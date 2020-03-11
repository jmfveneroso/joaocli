import React, {Component} from 'react';
import {Link, Switch, Route, Redirect, useParams} from 'react-router-dom';
import {Container, Row} from 'reactstrap';
import CodeMirror from 'react-codemirror';
import jQuery from 'jquery';
import 'codemirror/lib/codemirror.css';

function getCookie(name) {
  var cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
      var cookie = jQuery.trim(cookies[i]);
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

class LogEntry extends Component {
  constructor(props) {
    super(props);
    this.state = {
      id: this.props.match.params.id,
      entry: null,
    };
  }

  componentDidMount() {
    fetch("/entry/" + this.state.id)
      .then(res => res.json())
      .then(
        (result) => {
          this.setState({
            id: this.state.id,
            loaded: true,
            entry: result.entry,
          });
        },
        (error) => {
          this.setState({
            isLoaded: true,
            error
          });
        }
      )
  }

  updateCode(newCode) {
    let json = {
      id: this.state.id,
      content: newCode
    }

    let token = getCookie('csrftoken')
    fetch('/entry/' + this.state.id + '/', {
      method: 'post',
      mode: 'same-origin',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-CSRFToken': token,
      },
      credentials: 'include',
      body: JSON.stringify(json),
    }).then(function(response) {
      return response.json();
    }).then(function(data) {
      console.log(data);
    })
  }

  render() {
    if (!this.state.loaded) return <div/>

    let entry = this.state.entry

    let options = {
      lineNumbers: true,
    };

    return (
      <div className="log-entry">
        <Link to={`/log-entry/${entry.id}`} className="title">
          <span>{entry.id} -</span> {entry.title}
        </Link>
        <div className="timestamp">
          <span className="modified-at">
            M: {entry.modified_at}
          </span>
          &nbsp;
          <span className="created-at">
            C: {entry.created_at}
          </span>
        </div>
        <div className="tags">
            {entry.tags}
        </div>
        <div className="content">
          <CodeMirror value={entry.content}
                      onChange={this.updateCode.bind(this)} options={options} />
        </div>
        <Link to={`/`} className="title">Back</Link>
      </div>
    );
  }
}

export default LogEntry;
