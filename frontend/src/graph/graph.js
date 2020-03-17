import React, {Component} from 'react';
import {Link, Switch, Route, Redirect} from 'react-router-dom';
import {Container, Row} from 'reactstrap';
import {QueryMap, Vector} from './query_map.js';

class Canvas extends Component {
  constructor(props) {
    super(props);
    this.query_map = new QueryMap()
    this.state = { counter: 0 }
    this.canvas_ref = React.createRef()
  }

  drawCircle(ctx, pos, radius) {
    ctx.save()
    ctx.beginPath()
    ctx.arc(pos.x, pos.y, radius, 0, 2 * Math.PI)
    ctx.fillStyle = '#ee9999'
    ctx.fill()
    ctx.fillStyle = '#000000'
    ctx.lineWidth = 1
    ctx.strokeStyle = '#ff0000'
    ctx.stroke()
    ctx.restore()
  }

  drawRectangle(ctx, p, size) {
    ctx.save()
    ctx.beginPath()
    ctx.rect(p.x, p.y, size.x, size.y);
    ctx.fillStyle = '#ee9999'
    ctx.fill()
    ctx.fillStyle = '#000000'
    ctx.lineWidth = 1
    ctx.strokeStyle = '#ff0000'
    ctx.stroke()
    ctx.restore()
  }

  drawText(ctx, text, pos) {
    ctx.font = '8px monospace'
    ctx.textAlign = 'center'
    ctx.fillText(text, pos.x, pos.y + 4)
  }

  updateCanvas() {
    const canvas = this.canvas_ref.current;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h)
    this.query_map.nodes.forEach(node => {
      let top_lft = node.pos.sub(new Vector(25, 10))
      let size = new Vector(50, 20)
      this.drawRectangle(ctx, top_lft, size)
      // this.drawCircle(ctx, node.pos, 20)
      this.drawText(ctx, node.name, node.pos)
    });
  }

  componentDidMount() {
    this.timer = setInterval(() => {
      this.query_map.update()
      this.updateCanvas()
    }, 10);

    fetch("/logs")
      .then(res => res.json())
      .then(
        (result) => {
          for (let i = 0; i < 20; i++) {
            this.query_map.createNode(result.entries[i].title)
          }
        },
        (error) => {
          this.setState({
            isLoaded: true,
            error
          });
        }
      )
  }

  render() {
    return (
      <div>
        <canvas width="800" height="500" ref={this.canvas_ref} />
      </div>
    );
  }
}

export default Canvas;
