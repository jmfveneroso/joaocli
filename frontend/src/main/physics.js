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

  random(range) {
    return this.add(new Vector(Math.random(), Math.random()).multiply(range))
  }

  toString() {
    return 'x: ' + this.x + ' y: ' + this.y
  }
}

class Physics {
  static add_repulsive_force(node, v) {
    let distance_squared = Math.pow(node.pos.x - v.x, 2) + Math.pow(node.pos.y - v.y, 2)
    let repel_vector = node.pos.sub(v).normalize().multiply(Physics.REPULSION / (distance_squared + 0.00001))
    node.velocity = node.velocity.add(repel_vector)
  }

  static add_attractive_force(node, v) {
    let scalar = Physics.ATTRACTION * node.pos.distance_to(v)
    let attraction_vector = v.sub(node.pos).normalize().multiply(scalar)
    node.velocity = node.velocity.add(attraction_vector)
  }
}

Physics.REPULSION = 1000
Physics.ATTRACTION = 0.0001

export {
  Vector,
  Physics
}

