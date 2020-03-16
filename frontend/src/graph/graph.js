import React, {Component} from 'react';
import {Link, Switch, Route, Redirect} from 'react-router-dom';
import {Container, Row} from 'reactstrap';
import QueryMap from './query_map.js';

class NodeComponent extends Component {
  constructor(props) {
    super(props);
    this.state = { x: props.x, y: props.y, radius: props.radius };
  }

  render() {
    let x = this.state.x
    let y = this.state.y
    let radius = this.state.radius
    return (
      <g>
        <circle cx={x} cy={y} r={radius} stroke="red" fill="transparent" />
        <text x={x-10} y={y+5} fill="black">Node</text>
      </g>
    );
  }
}

class Graph extends Component {
  constructor(props) {
    super(props);
    this.query_map = new QueryMap()
    this.state = {};
  }

  componentDidMount() {
  }

  render() {
    const nodes = this.query_map.nodes.map(function (node) {
      return React.createElement(NodeComponent, {
        key: 0, x: node.x, y: node.y, radius: node.radius
      });
    });

    return (
      <svg width="800" height="500" ref={this.svg}>
        {nodes}
      </svg>
    );
  }
}

export default Graph;
