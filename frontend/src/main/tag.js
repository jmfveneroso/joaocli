import React, {Component} from 'react';
import API from './api.js';
import GraphSingleton from './graph.js';

class Tag extends Component {
  constructor(props) {
    super(props)
    this.state = {
      editor_enabled: false,
      tag_name: '',
    }
    this.debouncer = null
  }

  render() {
    let self = this
    let tag = this.props.tag
    this.state.tag_name = tag.name
    
    function addTag() {
      GraphSingleton.createTag(GraphSingleton.selected_node)
    }

    function deleteTag() {
      GraphSingleton.deleteTag(GraphSingleton.selected_node)
    }

    function enableEditor () {
      self.setState({ editor_enabled: true })
    }

    function disableEditor() {
      self.setState({ editor_enabled: false })
    }

    function updateTitle(event) {
      let new_title = event.currentTarget.value
      self.setState({ tag_name: new_title })
      tag.name = new_title
      if (tag.name.length > 0 && !tag.name.includes(' ')) {
        clearTimeout(self.debouncer)
        self.debouncer = setTimeout(function() {
          GraphSingleton.editTagTitle(tag.id, new_title)
        }, 500)
      }
    }

    function addEntry() {
      return GraphSingleton.createEntry().then((entry_node) => {
        self.props._handleAddEntry(entry_node)
      })
    }


    if (this.state.editor_enabled) {
      return (
        <div className="tag-info">
          <div className="tag-header">
            <input className="tag-edit-name" type="text" value={this.state.tag_name} onChange={e => updateTitle(e)} />
          </div>
          <div className="tag-buttons">
            <span className="btn" onClick={disableEditor}>VIEW</span>
            <span className="btn" onClick={addEntry}>+ ENTRY</span>
            <span className="btn" onClick={addTag}>+ TAG</span>
            <span className="btn" onClick={deleteTag}>DELETE</span>
          </div>
        </div>
      )
    } else {
      return (
        <div className="tag-info">
          <div className="tag-header">
            <span className="tag-name">{this.state.tag_name}</span> &nbsp;
            <span className="tag-date">{tag.modified_at.toLocaleString() }</span>
          </div>
          <div className="tag-buttons">
            <span className="btn" onClick={enableEditor}>EDIT</span>
            <span className="btn" onClick={addEntry}>+ ENTRY</span>
            <span className="btn" onClick={addTag}>+ TAG</span>
            <span className="btn" onClick={deleteTag}>DELETE</span>
          </div>
        </div>
      )
    }
  }
}

export default Tag;
