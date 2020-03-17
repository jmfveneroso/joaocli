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
  constructor(id, name, x, y) {
    this.id = id
    this.pos = new Vector(x, y)
    this.velocity = new Vector(0, 0)
    this.force = new Vector(0, 0)
    this.name = name
  }
}

const REPULSION = 200
const ATTRACTION = 0.0001
const FRICTION = 0.01

class Physics {
  static add_repulsive_force(node, v, force) {
    let distance_squared = Math.pow(node.pos.x - v.x, 2) + Math.pow(node.pos.y - v.y, 2)
    let repel_vector = node.pos.sub(v).normalize().multiply(force / (distance_squared + 0.00001))
    node.force = node.force.add(repel_vector)
  }

  // add_attractive_force(node, v, force) {
  //   scalar = force * node.pos.distance_to(v)
  //   attraction_vector = v.sub(node.pos).normalize().multiply(scalar)
  //   node.force = node.force.add attraction_vector
  // }

  static calculate_repulsive_forces(node, nodes) {
    nodes.forEach(n => {
      if (n.id != node.id) {
        this.add_repulsive_force(node, n.pos, REPULSION)
      }
    })
  }

  // calculate_elastic_forces(node) {
  //   for key, n of node.edges
  //     this.add_attractive_force(node, n.target.pos, ATTRACTION)
  //     this.add_attractive_force(n.target, node.pos, ATTRACTION)
  // }

  static calculate_friction_force(node) {
    let friction_vector = node.velocity.multiply(-FRICTION)
    node.force = node.force.add(friction_vector)
  }

  static calculate_constraint_forces(node, canvas_width, canvas_height) {
    let dist = 2
    let up    = new Vector(node.pos.x, canvas_height + dist)
    let down  = new Vector(node.pos.x, -dist)
    let left  = new Vector(-dist, node.pos.y)
    let right = new Vector(canvas_width + dist, node.pos.y)

    this.add_repulsive_force(node, up, REPULSION)
    this.add_repulsive_force(node, down, REPULSION)
    this.add_repulsive_force(node, left, REPULSION)
    this.add_repulsive_force(node, right, REPULSION)
  }

  static update_forces(nodes, width, height) {
    nodes.forEach(node => {
      this.calculate_constraint_forces(node, width, height)
      this.calculate_repulsive_forces(node, nodes)
      // this.calculate_elastic_forces node
      this.calculate_friction_force(node)
    });
  }

  static limit_to_bounds(nodes, width, height) {
    nodes.forEach(node => {
      node.pos = node.pos.clamp(1, width - 1)
    });
  }

  static update_motion(nodes) {
    nodes.forEach(node => {
      node.velocity = node.velocity.add(node.force)
      node.pos = node.pos.add(node.velocity)
      node.force.make_null()
    });
  }
}

class QueryMap {
  constructor(nodes) {
    this.id = 0
    this.nodes = []
  }

  createNode(name) {
    let x = Math.floor(Math.random() * 800)
    let y = Math.floor(Math.random() * 500)
    this.nodes.push(new Node(this.id++, name, x, y))
  }

  update() {
    Physics.update_forces(this.nodes, 800, 500)
    Physics.update_motion(this.nodes)
    Physics.limit_to_bounds(this.nodes, 800, 500)
  }
}

export {
  QueryMap,
  Vector
}
