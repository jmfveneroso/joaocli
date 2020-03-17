import React, {Component} from 'react';
import {Link, Switch, Route, Redirect} from 'react-router-dom';
import {Container, Row} from 'reactstrap';
import QueryMapSingleton from './query_map.js';

class NodeComponent extends Component {
  constructor(props) {
    super(props);
    this.state = { x: props.node.pos.x, y: props.node.pos.y, radius: props.radius };
  }

  update() {
    this.setState({ 
      x: props.node.pos.x, y: props.node.pos.y, radius: props.radius 
    });
    console.log('vc me abandounou')
  }

  render() {
    console.log('amor ' + this.state.x)
    let x = this.state.x
    let y = this.state.y
    let radius = this.state.radius
    return (
      <g>
        <circle cx={x} cy={y} r={radius} stroke="red" fill="transparent" />
        <text x={x-13} y={y+3} fill="black">Node {x}</text>
      </g>
    );
  }
}

class Graph extends Component {
  constructor(props) {
    super(props);
    this.query_map = QueryMapSingleton
    this.state = { counter: 0 };
  }

  componentDidMount() {
    this.timer = setInterval(() => {
      this.query_map.update()
      this.forceUpdate()
    }, 10);
  }

  createArr() {
    let counter = this.state.counter;
    let arr = []
    arr = this.query_map.nodes.map(function (node) {
      console.log('the rhythm: ' + counter);
      return React.createElement(NodeComponent, {
        key: counter++, node: node, radius: node.radius
      });
    });
    return arr
  }

  render() {
    let nodes = this.createArr()
    console.log('the rhythm of the night');

    return (
      <svg width="800" height="500">
        {nodes}
      </svg>
    );
  }
}

export default Graph;
