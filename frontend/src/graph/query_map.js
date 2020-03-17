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
    this.x += v.x
    this.y += v.y
    return this
  }

  sub(v) {
    this.x -= v.x
    this.y -= v.y
    return this
  }

  multiply(scalar) {
    this.x *= scalar
    this.y *= scalar
    return this
  }

  dot_product(v) {
    this.x *= v.x
    this.y *= v.y
    return this
  }

  norm() {
    return Math.sqrt(this.x * this.x + this.y * this.y)
  }

  normalize() {
    let norm = this.norm()
    if (norm > 0) {
      this.x /= norm
      this.y /= norm
    }
    return this
  }

  distance_to(v) {
    return Math.sqrt(Math.pow(this.x - v.x, 2) + Math.pow(this.y - v.y, 2))
  }

  clamp(min, max) {
    this.x = Math.min(Math.max(this.x, min), max)
    this.y = Math.min(Math.max(this.y, min), max)
    return this
  }
}

class Node {
  constructor(x, y, radius) {
    this.pos = new Vector(x, y)
    this.velocity = new Vector(0, 0)
    this.force = new Vector(0, 0)
    this.radius = radius
  }
}

const REPULSION = 10
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

  // calculate_repulsive_forces(node, nodes) {
  //   for key, n of nodes
  //     continue if n.id == node.id
  //     this.add_repulsive_force(node, n.pos, REPULSION)
  // }

  // calculate_elastic_forces(node) {
  //   for key, n of node.edges
  //     this.add_attractive_force(node, n.target.pos, ATTRACTION)
  //     this.add_attractive_force(n.target, node.pos, ATTRACTION)
  // }

  static calculate_friction_force(node) {
    node.force = node.force.multiply(1 - FRICTION)
  }

  static calculate_constraint_forces(node, canvas_width, canvas_height) {
    let dist = 2
    let up = new Vector(node.pos.x, canvas_height + dist)
    let down = new Vector(node.pos.x, -dist)
    let left = new Vector(-dist, node.pos.y)
    let right = new Vector(canvas_width + dist, node.pos.y)

    // this.add_repulsive_force(node, up, REPULSION)
    this.add_repulsive_force(node, down, REPULSION)
    // this.add_repulsive_force(node, left, REPULSION)
    // this.add_repulsive_force(node, right, REPULSION)
  }

  static update_forces(nodes, width, height) {
    nodes.forEach(node => {
      this.calculate_constraint_forces(node, width, height)
      // this.calculate_repulsive_forces(node, nodes)
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
      // console.log(node.velocity.x)
      // console.log(node.velocity.y)
      node.pos = node.pos.add(node.velocity)
      node.pos = new Vector(100, node.pos.y)
      // console.log(node.pos.x)
      console.log(node.pos.y)
      node.force.make_null()
    });
  }
}

class QueryMap {
  constructor() {
    this.nodes = [
      new Node(125, 125, 20),
      new Node(245, 125, 20),
      new Node(385, 125, 20),
      new Node(500, 125, 20),
    ]
  }

  update() {
    Physics.update_forces(this.nodes, 800, 500)
    Physics.update_motion(this.nodes)
    Physics.limit_to_bounds(this.nodes, 800, 500)
    // this.nodes.forEach(node => {
    //   console.log(node.pos.x);
    //   console.log(node.pos.y);
    // });
  }
}

let QueryMapSingleton = new QueryMap()

export default QueryMapSingleton;
