import React, {Component} from 'react';
import {Link, Switch, Route, Redirect} from 'react-router-dom';
import {Container, Row} from 'reactstrap';

class Graph extends Component {
  constructor(props) {
    super(props);
    this.state = {};
  }

  componentDidMount() {
  }

  render() {
    return (
      <svg width="800" height="500">
        <circle cx="50" cy="50" r="25" fill="red" />
      </svg>
    );
  }
}

export default Graph;
