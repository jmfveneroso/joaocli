import React, {Component} from 'react';
import GraphSingleton from './graph.js';
import CodeMirror from 'react-codemirror';
import jQuery from 'jquery';
import 'codemirror/lib/codemirror.css';

class Entry extends Component {
  constructor(props) {
    super(props)
    this.entry = props.entry
    this.code_debounce = null
    this.title_debounce = null
    this.state = {
      enable_editor: false,
      content: props.entry.content,
      title: props.entry.title
    }
  }

  updateCode(new_content) {
    clearTimeout(this.code_debounce)
    this.setState({
      content: new_content
    })

    let self = this
    this.code_debounce = setTimeout(function() {
      GraphSingleton.updateEntryContent(self.entry.id, new_content)
    }, 300)
  }

  updateTitle(event) {
    this.setState({
      title: event.currentTarget.value
    });

    let self = this
    clearTimeout(this.title_debounce)
    this.title_debounce = setTimeout(function() {
      GraphSingleton.updateEntryTitle(self.entry.id, self.state.title)
    }, 300)
  }

  deleteEntry(event) {
    let self = this
    GraphSingleton.deleteEntry(self.entry.id).then(function (data) {
      self.props._handleDelete(self.entry.id)
    })
  }

  moveEntry(event) {
    GraphSingleton.moving_entry = this.entry
  }

  enableEditor() {
    this.setState({ enable_editor: true })
  }

  disableEditor() {
    this.setState({ enable_editor: false })
  }

  render() {
    let self = this
    let entry = this.entry
    let title = this.state.title
    let modified_at = entry.modified_at.toString()

    let content = this.state.content
    if (this.state.enable_editor) {
      let options = { lineNumbers: true };
      return (
        <div className="log-entry">
          <span className="title">{entry.id} -</span> 
          <input type="text" value={title} onChange={e => self.updateTitle(e)} /> 
          <div>
            <span className="enable-editor" onClick={e => self.disableEditor(e)}>VIEW</span> 
          </div>
          <div className="timestamp">
            <span className="modified-at">{modified_at}</span>
          </div>
          <div className="tags">{entry.category.name}</div>
          <CodeMirror value={content} 
            onChange={this.updateCode.bind(this)} 
            options={options} />
        </div>
      )
    } else {
      return (
        <div className="log-entry">
          <span className="title">{entry.id} -</span>
          <span>{title}</span>
          <div>
            <span className="enable-editor" onClick={e => self.enableEditor(e)}>EDIT</span> &nbsp;
            <span className="enable-editor" onClick={e => self.deleteEntry(e)}>DELETE</span> &nbsp;
            <span className="enable-editor" onClick={e => self.moveEntry(e)}>MOVE</span> 
          </div>
          <div className="timestamp">
            <span className="modified-at">{modified_at}</span>
          </div>
          <div className="tags">{entry.category.name}</div>
          <div className="content">
            {content.split('\n').map((line, i) => {
              return (
                <p key={i}>{line}</p>
              )
            })}
          </div>
        </div>
      )
    }
  }
}

export default Entry;
