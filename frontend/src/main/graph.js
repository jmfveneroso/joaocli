import API from './api.js';
import {Vector, Physics} from './physics.js';

class TagNode {
  constructor(tag, pos) {
    // General attributes.
    this.pos = pos
    this.velocity = new Vector(0, 0)
    this.score = 0
    this.selected = false

    // Tag attributes.
    this.parent = null
    this.id = tag.id
    this.name = tag.name
    this.total_entries = tag.total_entries
    this.children = []
    this.entries = []
    this.modified_at = new Date(Date.parse(tag.modified_at))
  }

  addChild(tag_node) {
    this.children.push(tag_node)
    tag_node.parent = this
  }

  addEntry(entry_node) {
    this.entries.push(entry_node)
    entry_node.category = this
  }

  incrementEntryCount(entry_node) {
    let parent = this
    while (parent) {
      parent.total_entries++
      parent = parent.parent
    }
  }

  recalculateModifiedTime() {
    this.modified_at = new Date()
    this.modified_at.setTime(0)
    for (let i = 0; i < this.entries.length; i++) {
      if (this.entries[i].modified_at > this.modified_at) {
        this.modified_at = this.entries[i].modified_at
      }
    }

    for (let i = 0; i < this.children.length; i++) {
      if (this.children[i].modified_at > this.modified_at) {
        this.modified_at = this.children[i].modified_at
      }
    }

    if (this.parent) {
      this.parent.recalculateModifiedTime()
    }
  }

  removeChild(tag_id) {
    for (let i = 0; i < this.children.length; i++) {
      if (this.children[i].id === tag_id) {
        this.children.splice(i, 1)
	return
      }
    }
  }

  removeEntry(entry_id) {
    for (let i = 0; i < this.entries.length; i++) {
      if (this.entries[i].id === entry_id) {
        this.entries.splice(i, 1)
        break
      }
    }

    let parent = this
    while (parent) {
      parent.total_entries--
      parent = parent.parent
    }
  }

  getChildrenInternal(tag) {
    let children = tag.children
    for (let i = 0; i < tag.children.length; i++) {
      children = children.concat(this.getChildrenInternal(tag.children[i]))
    }
    return children
  }

  getChildren(tag) {
    return [this].concat(this.getChildrenInternal(this))
  }

  getEntriesInternal(tag) {
    let entries = [].concat(tag.entries)
    for (let i = 0; i < tag.children.length; i++) {
      entries = entries.concat(this.getEntriesInternal(tag.children[i]))
    }
    return entries
  }

  getEntries() {
    let entries = this.getEntriesInternal(this)
    entries.sort((a, b) => {
      if (a.modified_at < b.modified_at) return 1;
      else if (a.modified_at > b.modified_at) return -1;
      return 0;
    })  
    return entries
  }

  isSelected() {
    return this.selected
  }
}

class EntryNode {
  constructor(entry, pos) {
    // General attributes.
    this.pos = pos
    this.velocity = new Vector(0, 0)
    this.score = 0

    // Entry attributes.
    this.id = entry.id
    this.title = entry.title
    this.content = entry.content
    this.category = null
    this.created_at = new Date(Date.parse(entry.created_at))
    this.modified_at = new Date(Date.parse(entry.modified_at))
  }
}

class Graph {
  constructor(nodes) {
    this.main_tag = null
    this.other_tag = null
    this.tags = {}
    this.entries = {}

    this.dragging_tag = false
    this.replacing = false
    this.moving_entry = false
    this.old_parent = null
    this.selected_node = null
    this.temperature = 1000
  }

  load(center) {
    return API.getAll().then((result) => {
      this.loadTags(result.tags, center)
      this.loadEntries(result.entries)
    })
  }

  loadTags(tags, center) {
    for (let i = 0; i < tags.length; i++) {
      let pos = center.sub(new Vector(2000, 2000)).random(4000)
      let tag_node = new TagNode(tags[i], pos)
      this.tags[tags[i].id] = tag_node
    }
    this.main_tag = this.tags[0]
    this.other_tag = this.tags[1]

    // Load children.
    for (let i = 0; i < tags.length; i++) {
      let tag_node = this.tags[tags[i].id]
      for (let j = 0; j < tags[i].children.length; j++) {
        let child_id = parseInt(tags[i].children[j])
        let child_node = this.tags[child_id]
        tag_node.addChild(child_node)
      }
    }
  }

  loadEntries(entries) {
    for (let i = 0; i < entries.length; i++) {
      let entry_node = new EntryNode(entries[i], new Vector(0, 0))
      this.entries[entries[i].id] = entry_node
      let tag = this.tags[entries[i].category]
      tag.addEntry(entry_node)
    }
  }

  getTags() {
    return Object.values(this.tags)
  }

  clearSelection() {
    for (let id in this.tags) this.tags[id].selected = false
    this.selected_node = null
  }

  selectTag(tag_id) {
    this.clearSelection()
    this.tags[tag_id].selected = true
    this.selected_node = this.tags[tag_id]
  }

  update() {
    if (this.temperature <= 0) return
    for (let id in this.tags) {
      this.tags[id].velocity = new Vector(0, 0)
    }

    for (let id in this.tags) {
      let tag = this.tags[id]

      // Calculate repulsion.
      for (let id2 in this.tags) {
        let tag2 = this.tags[id2]
        if (tag2.isSelected() && this.replacing) continue
        if (tag.id == tag2.id) continue
        if (!this.replacing || !tag.isSelected()) 
          Physics.add_repulsive_force(tag, tag2.pos)
      }

      // Calculate attraction.
      for (let i = 0; i < tag.children.length; i++) {
        let child = tag.children[i]
        if (!this.replacing || !child.isSelected())  
          Physics.add_attractive_force(tag, child.pos)
        Physics.add_attractive_force(child, tag.pos)
      }
    }

    for (let id in this.tags) {
      let tag = this.tags[id]
      if (tag.id === 0) continue
      tag.pos = tag.pos.add(tag.velocity.multiply(this.temperature))
    }
    this.temperature -= 0.01
  }

  deleteEntry(id) {
    let self = this
    return API.deleteEntry(id).then(function (data) {
      let tag = self.entries[id].category
      tag.removeEntry(id)
      tag.recalculateModifiedTime()
      delete self.entries[id]
    })
  }

  updateEntryTitle(id, title) {
    let entry = this.entries[id]
    entry.title = title
    entry.modified_at = new Date(Date.now())
    entry.category.recalculateModifiedTime()
    return API.updateEntryContent(id, title, entry.content)
  }

  updateEntryContent(id, new_content) {
    let entry = this.entries[id]
    entry.content = new_content
    entry.modified_at = new Date(Date.now())
    entry.category.recalculateModifiedTime()
    return API.updateEntryContent(id, entry.title, new_content)
  }

  changeEntryParent(entry, new_parent) {
    let tag = entry.category
    tag.removeEntry(entry.id)
    new_parent.addEntry(entry)
    return API.updateEntryTag(entry.id, new_parent.name)
  }

  createEntry() {
    let self = this
    return API.createEntry(this.selected_node.id, 'New entry').then((entry) => {
      let entry_node = new EntryNode(entry, new Vector(0, 0))
      self.entries[entry.id] = entry_node
      self.selected_node.addEntry(entry_node)
      self.selected_node.incrementEntryCount()
      self.selected_node.recalculateModifiedTime()
      return entry_node
    })
  }

  createTag(parent) {
    let self = this
    API.createTag('new', parent.id).then(function(data) {
      let tag_node = new TagNode(data, parent.pos.random(200))
      self.tags[tag_node.id] = tag_node
      self.selected_node.addChild(tag_node)
    })
  }

  deleteTag(tag) {
    let self = this
    API.deleteTag(tag.id).then(function(data) {
      tag.parent.removeChild(tag.id)
      let children = tag.getChildren()
      for (let i = 0; i < children.length; i++) {
        delete self.tags[children[i].id]
      }
      let entries = tag.getEntries()
      for (let i = 0; i < entries.length; i++) {
        delete self.entries[entries[i].id]
      }
    })
  }

  getClosestNode(source) {
    let min_distance = 999999999
    let closest_node = null
    for (let id in this.tags) {
      id = parseInt(id)
      if (id === source.id || id === 1) continue
      if (source.children.includes(id)) continue

      const node = this.tags[id]
      let distance = node.pos.distance_to(source.pos)
      if (distance < min_distance) {
        min_distance = distance
	closest_node = node
      }
    }
    return closest_node
  }

  moveSelectionToParent(parent) {
    let old_parent = this.old_parent
    let tag = this.selected_node
    return API.editTag(tag.id, tag.name, parent.id).then(function(data) {
      tag.parent.removeChild(tag)
      parent.addChild(tag)
    })
  }

  editTagTitle(tag_id, new_title) {
    let tag = this.tags[tag_id]
    API.editTag(tag.id, new_title, null).then((data) => {
      console.log(data)
    })
  }

  getEntryById(id) {
    return this.entries[id]
  }

  getTagById(id) {
    return this.tags[id]
  }

  getEntries() {
    return this.main_tag.getEntries()
  }
}

let GraphSingleton = new Graph()
export default GraphSingleton;
