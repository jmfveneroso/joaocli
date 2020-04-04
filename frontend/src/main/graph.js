class Vector {
  constructor(x, y) {
    this.x = x
    this.y = y
  }

  make_null() {
    this.x = this.y = 0
    return this
  }

  add(v) {
    return new Vector(this.x + v.x, this.y + v.y)
  }

  sub(v) {
    return new Vector(this.x - v.x, this.y - v.y)
  }

  multiply(scalar) {
    return new Vector(this.x * scalar, this.y * scalar)
  }

  div(scalar) {
    return new Vector(this.x / scalar, this.y / scalar)
  }

  dot_product(v) {
    return new Vector(this.x * v.x, this.y * v.y)
  }

  norm() {
    return Math.sqrt(this.x * this.x + this.y * this.y)
  }

  normalize() {
    let norm = this.norm()
    if (norm > 0) {
      return new Vector(this.x / norm, this.y / norm)
    }
    return new Vector(this.x, this.y)
  }

  distance_to(v) {
    return Math.sqrt(Math.pow(this.x - v.x, 2) + Math.pow(this.y - v.y, 2))
  }

  clamp(min, max) {
    return new Vector(Math.min(Math.max(this.x, min), max), Math.min(Math.max(this.y, min), max))
  }

  toString() {
    return 'x: ' + this.x + ' y: ' + this.y
  }
}

class Node {
  constructor(type, id, name, x, y, content, mass, entry, total_entries, modified_at) {
    this.id = id
    this.type = type
    this.pos = new Vector(x, y)
    this.velocity = new Vector(0, 0)
    this.force = new Vector(0, 0)
    this.name = name
    this.children = []
    this.entries = []
    this.content = content
    this.score = 0
    this.mass = mass
    this.entry = entry 
    this.total_entries = total_entries
    this.active = false
    this.modified_at = new Date(Date.parse(modified_at))
  }

  removeChild(tag_id) {
    for (let i = 0; i < this.children.length; i++) {
      if (this.children[i] === tag_id) {
        this.children.splice(i, 1)
	return
      }
    }
  }

  removeEntry(entry_id) {
    for (let i = 0; i < this.entries.length; i++) {
      if (this.entries[i] === entry_id) {
        this.entries.splice(i, 1)
	return
      }
    }
  }

  addChild(node) {
    this.children.push(node.id)
  }
}

class Physics {
  static add_repulsive_force(node, v, force) {
    let distance_squared = Math.pow(node.pos.x - v.x, 2) + Math.pow(node.pos.y - v.y, 2)
    let repel_vector = node.pos.sub(v).normalize().multiply(force / (distance_squared + 0.00001))
    node.velocity = node.velocity.add(repel_vector)
  }

  static add_attractive_force(node, v, force) {
    let scalar = force * node.pos.distance_to(v)
    let attraction_vector = v.sub(node.pos).normalize().multiply(scalar)
    node.velocity = node.velocity.add(attraction_vector)
  }

  static calculate_repulsive_forces(node, nodes) {
    if (!node.active) return

    nodes.forEach(n => {
      if (n.id != node.id && n.active) {
        let magnitude = Physics.REPULSION
        if (n.type === 'tag') {
	  magnitude *= 10
	}
        this.add_repulsive_force(node, n.pos, magnitude)
      }
    })
  }

  static calculate_elastic_forces(source, target, factor) {
    if (!source.active || !target.active) return;

    this.add_attractive_force(source, target.pos, Physics.ATTRACTION * factor)
    this.add_attractive_force(target, source.pos, Physics.ATTRACTION * factor)
  }

  static calculate_friction_force(node) {
    let friction_vector = node.velocity.multiply(-Physics.FRICTION)
    node.velocity = node.velocity.add(friction_vector)
  }

  static update_motion(nodes) {
    nodes.forEach(node => {
      if (node.name === 'main') {
        node.pos = new Vector(4000, 4000)
	return
      } 

      if (!node.active) return;
      node.pos = node.pos.add(node.velocity.multiply(Physics.temperature))
      node.force.make_null()
    });
    Physics.temperature -= 0.1
  }
}

Physics.temperature = 1000
Physics.REPULSION = 100
Physics.ATTRACTION = 0.0001
Physics.FRICTION = 0.01
Physics.CENTRAL_ATTRACTION = 0.00008
Physics.CENTRAL_REPULSION = 80000
Physics.RELEVANCE_ATTRACTION = 7000

class IrModel {
  constructor(nodes) {
    this.nodes = nodes
    this.createVocab()
  }

  createVocab(nodes) {
    this.vocab = {}
    for (let i = 0; i < this.nodes.length; i++) {
      let node = this.nodes[i]
      let tokens = (node.title + node.content).toLowerCase().split(' ')

      for (let j = 0; j < tokens.length; j++) {
        if (this.vocab[tokens[j]] === undefined) {
          this.vocab[tokens[j]] = 0
	}
        this.vocab[tokens[j]]++
      }
    }
  }

  calculateRelevance(query) {
    let queryTokens = query.split()
    for (let i = 0; i < this.nodes.length; i++) {
      let node = this.nodes[i]
      let tokens = (node.name + node.content).toLowerCase().split(' ')

       let score = 0
       let norm = 0
       for (let j = 0; j < tokens.length; j++) {
         let tkn = tokens[j]
         if (this.vocab[tkn] === undefined) {
	   continue
	 }

         if (queryTokens.includes(tkn)) {
           score += Math.pow(1.0 / this.vocab[tkn], 2)
         }
         norm += Math.pow(1.0 / this.vocab[tkn], 2)
         
       }

       if (norm > 0) {
         score /= Math.sqrt(norm)
       }
       this.nodes[i].score = score
    }
  }
}

class Graph {
  constructor(nodes) {
    this.replacing = false
    this.moving_entry = false
    this.old_parent = null
    this.selected_node = null
    this.nodes = []
    this.nodes_by_id = {}
    this.tags_by_id = {}
    this.tags_by_name = {}
    this.irModel = null 
    this.main_tags = []
  }

  getNodeById(id) {
    return this.nodes_by_id[id]
  }

  getTagById(id) {
    return this.tags_by_id[id]
  }

  getTagByName(name) {
    return this.tags_by_name[name]
  }
  
  createEntryNode(entry) {
    // let x = Math.floor(Math.random() * 3200)
    // let y = Math.floor(Math.random() * 2000)

    // let newNode = new Node('entry', entry.id, entry.title, x, y, entry.content, 1, entry, 1, entry.modified_at)
    // this.nodes.push(newNode)
    // this.nodes_by_id[entry.id] = newNode
  }

  createTagNode(tag, pos) {
    let x = Math.floor(2000 + Math.random() * 4000)
    let y = Math.floor(2000 + Math.random() * 4000)
    if (pos) {
      x = Math.floor(pos.x - 100 + Math.random() * 200)
      y = Math.floor(pos.y - 100 + Math.random() * 200)
    }

    let new_node = new Node('tag', tag.id, tag.name, x, y, '', 1, null, tag.total_entries, tag.modified_at)
    this.tags_by_id[tag.id] = new_node
    this.tags_by_name[tag.name] = new_node
    new_node.entries = tag.entries
    new_node.children = tag.children
    this.nodes.push(new_node)
    return new_node
  }

  createIrModel() {
    this.irModel = new IrModel(this.nodes)
  }

  update() {
    let self = this
    this.nodes.forEach(node => {
      if (!node.active) return
      if (self.selected_node && self.replacing) {
        if (node.id == self.selected_node.id) {
          node.velocity = new Vector(0, 0)
	  return
	}
      }
      node.velocity = new Vector(0, 0)

      self.nodes.forEach(n => {
        if (self.selected_node && n.id == self.selected_node.id && self.replacing) return
        if (n.id != node.id && n.active) {
          let magnitude = ((n.type === 'tag') ? 10 : 1) * Physics.REPULSION
          Physics.add_repulsive_force(node, n.pos, magnitude)
        }
      })
    });

    this.nodes.forEach(node => {
      node.children.forEach(id => {
        let target = self.getTagById(id)
        if (target !== undefined) {
          Physics.calculate_elastic_forces(node, target, 1)
        }
      })

      // node.entries.forEach(id => {
      //   let target = self.getNodeById(id)
      //   if (target !== undefined) {
      //     Physics.calculate_elastic_forces(node, target, 1) 
      //   }
      // })
    });
    
    Physics.update_motion(this.nodes)
  }

  getAllEntryIds(node_id) {
    let node = this.getTagById(node_id)
    if (node === undefined)
      return []
    let entries = node.entries
    node.children.forEach(n => {
      entries = entries.concat(this.getAllEntryIds(n))
    })
    return entries
  }

  rankNodes(query) {
    this.irModel.calculateRelevance(query)

    this.nodes.sort((a, b) => {
      if (a.score > b.score) {
        return -1
      } else if (a.score < b.score) {
        return 1
      } else if (a.modified_at < b.modified_at) {
        return -1;
      } else if (a.modified_at > b.modified_at) {
        return 1;
      }
      return 0;
    })  

    for (let i = 0; i < this.nodes.length; i++) {
      this.nodes[i].active = this.nodes[i].type === 'tag'
    }
  }

  setRepulsion(repulsion) {
    Physics.REPULSION = repulsion
  }

  setAttraction(attraction) {
    Physics.ATTRACTION = attraction
  }

  setFriction(friction) {
    Physics.FRICTION = friction
  }

  setCentralRepulsion(central_repulsion) {
    Physics.CENTRAL_REPULSION = central_repulsion
  }

  setCentralAttraction(central_attraction) {
    Physics.CENTRAL_ATTRACTION = central_attraction
  }

  setRelevanceAttraction(relevance_attraction) {
    Physics.RELEVANCE_ATTRACTION = relevance_attraction
  }

  setMainTags(main_tags) {
    this.main_tags = main_tags
  }

  getTagParent(tag_id) {
    let tag = this.tags_by_id[tag_id]
    for (let i = 0; i < this.nodes.length; i++) {
      if (this.nodes[i].type === 'tag') {
        for (let j = 0; j < this.nodes[i].children.length; j++) {
          if (this.nodes[i].children[j] === tag_id) {
	    return this.nodes[i]
	  }
	}
      }
    }
    return null
  }

  deleteTag(tag_id) {
    for (let i = 0; i < this.nodes.length; i++) {
      if (this.nodes[i].type === 'tag') {
        let found = false
        for (let j = 0; j < this.nodes[i].children.length; j++) {
          if (this.nodes[i].children[j] === tag_id) {
            this.nodes[i].children.splice(j, 1)
            found = true
	    break
	  }
	}
	if (found) break
      }
    }
    for (let i = 0; i < this.nodes.length; i++) {
      if (this.nodes[i].type === 'tag' && this.nodes[i].id === tag_id) {
        this.nodes.splice(i, 1)
	break
      }
    }
    delete this.tags_by_id[tag_id]
  }

  getClosestNode(source) {
    let min_distance = 999999999
    let closest_node = null
    for (let i = 0; i < this.nodes.length; i++) {
      const node = this.nodes[i]
      if (!node.active) continue
      if (node.id === source.id) continue
      if (node.name === 'other') continue
      if (source.children.includes(node.id)) continue

      let distance = node.pos.distance_to(source.pos)
      if (distance < min_distance) {
        min_distance = distance
	closest_node = node
      }
    }
    return closest_node
  }
}

let GraphSingleton = new Graph()

export {
  GraphSingleton,
  Vector,
  Physics
}
