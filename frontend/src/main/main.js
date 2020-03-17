import React, {Component} from 'react';
import {Link, Switch, Route, Redirect} from 'react-router-dom';
import {Container, Row} from 'reactstrap';
import CodeMirror from 'react-codemirror';
import 'codemirror/lib/codemirror.css';
import Graph from '../graph/graph.js';

function LogEntry(props) {
  function emitChange(){
    console.log('just who');
  }

  return (
    <div className="log-entry">
      <Link to={`/log-entry/${props.entry.id}`} className="title">
        <span>{props.entry.id} -</span> {props.entry.title}
      </Link>
      <div className="timestamp">
        <span className="modified-at">
          M: {props.entry.modified_at}
        </span>
        &nbsp;
        <span className="created-at">
          C: {props.entry.created_at}
        </span>
      </div>
      <div className="tags">
          {props.entry.tags}
      </div>
      <div className="content">
        {props.entry.content.split('\n').map((line, i) => {
          return (
            <p key={i}>{line}</p>
          );
        })}
      </div>
    </div>
  );
}

class Main extends Component {
  constructor(props) {
    super(props);
    this.state = {
      entries: [],
    };
  }

  componentDidMount() {
    fetch("/logs")
      .then(res => res.json())
      .then(
        (result) => {
          this.setState({entries: result.entries});
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
    let entries = this.state.entries
    let options = {
      lineNumbers: true,
    }

    return (
      <div className="app">
        <div className="app-body">
          <main className="main">
            <div className="main-container">
              <input type="text" />
              <Graph />
            </div>
            <div className="log-entries">
              {entries.map(entry => {
                return <LogEntry entry={entry} key={entry.id} />;
              })}
            </div>
          </main>
        </div>
      </div>
    );
  }
}

export default Main;