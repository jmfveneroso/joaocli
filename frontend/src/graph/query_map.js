class Vector {
  constructor(x, y) {
    this.x = x
    this.y = y
  }

  makeNull() {
    this.x = this.y = 0
  }

  add(v) {
    this.x += v.x
    this.y += v.y
  }

  sub(v) {
    this.x -= v.x
    this.y -= v.y
  }

  multiply(scalar) {
    this.x *= scalar
    this.y *= scalar
  }

  dot_product(v) {
    this.x *= v.x
    this.y *= v.y
  }

  norm() {
    Math.sqrt(this.x * this.x + this.y * this.y)
  }

  normalize() {
    let norm = this.norm()
    if (norm > 0) {
      this.x /= norm
      this.y /= norm
    }
  }

  distance_to(v) {
    return Math.sqrt(Math.pow(this.x - v.x, 2) + Math.pow(this.y - v.y, 2))
  }
}

class Node {
  constructor(x, y, radius) {
    this.x = x
    this.y = y
    this.radius = radius
  }
}

class QueryMap {
  constructor() {
    this.nodes = [
      new Node(125, 125, 10),
      new Node(145, 125, 10),
      new Node(185, 125, 10),
      new Node(200, 125, 10),
    ]
  }
}

export default QueryMap;
