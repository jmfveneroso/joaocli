import React, {Component} from 'react';
import {Link, Switch, Route, Redirect} from 'react-router-dom';
import {Container} from 'reactstrap';

function LogEntry(props) {
  return (
    <div class="log-entry">
      <div class="title">{props.entry.title}</div>
      <div class="content">{props.entry.content}</div>
    </div>
  );
}

class Main extends Component {
  constructor(props) {
    super(props);
    this.state = {entries: []};
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
    return (
      <div className="app">
        <div className="app-body">
          <main className="main">
            <Container fluid>
              {entries.map(entry => {
                return <LogEntry entry={entry} />;
              })}
            </Container>
          </main>
        </div>
      </div>
    );
  }
}

export default Main;
