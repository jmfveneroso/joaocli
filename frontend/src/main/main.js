import React, {Component} from 'react';
import {Link, Switch, Route, Redirect} from 'react-router-dom';
import {Container} from 'reactstrap';

function LogEntry(props) {
  return (
    <div className="log-entry">
      <div className="title">{props.entry.title}</div>
      <div className="content">
        {props.entry.content.split('\n').map(i => {
          return <p>{i}</p>
        })}
      </div>
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
    // <Container fluid>
    // </Container>
    return (
      <div className="app">
        <div className="app-body">
          <main className="main">
            <div className="wrapper">
              <div className="horizontal-scroll">
                {entries.map(entry => {
                  return <LogEntry entry={entry} />;
                })}
              </div>
            </div>
          </main>
        </div>
      </div>
    );
  }
}

export default Main;
