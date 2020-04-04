import React, {Component} from 'react';
import {Link, Switch, Route, Redirect} from 'react-router-dom';
import {Container, Row} from 'reactstrap';
import {GraphSingleton, Vector, Physics} from './graph.js';
import CodeMirror from 'react-codemirror';
import jQuery from 'jquery';
import 'codemirror/lib/codemirror.css';

let holding_mouse = false
let SENSIBILITY = 4
let WHEEL_SENSITIVITY = 0.01
let MIN_ZOOM = 0.25
let MAX_ZOOM = 16

function daysBetween(date1, date2) {
  let diff_in_time = date2.getTime() - date1.getTime()
  return diff_in_time / (1000 * 3600 * 24)
}

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

class TagEditor extends Component {
  constructor(props) {
    super(props)
    this.graph = GraphSingleton
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
      let json = {
        name: 'new',  
        parent: self.graph.selected_node.id, 
      }

      let token = getCookie('csrftoken')
      fetch('/tag/', {
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
        console.log(data)
        let new_node = self.graph.createTagNode({
          'id': data.id,
          'name': 'new-' + data.id.toString(),
          'children': [],
          'entries': [],
          'total_entries': 0,
          'created_at': new Date(),
          'modified_at': new Date(),
        }, self.graph.selected_node.pos)
        new_node.active = true
        self.graph.selected_node.children.push(data.id)
      })
    }

    function deleteTag() {
      let tag_id = self.graph.selected_node.id
      let json = {
        id: tag_id
      }

      let token = getCookie('csrftoken')
      fetch('/tag/', {
        method: 'delete',
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
        self.graph.deleteTag(tag_id)
      })
    }

    function enableEditor () {
      self.setState({ editor_enabled: true })
    }

    function disableEditor() {
      self.setState({ editor_enabled: false })
    }

    function updateTitle(event) {
      let newTitle = event.currentTarget.value
      tag.name = newTitle
      console.log(tag)
      console.log(tag.name)
      self.setState({ tag_name: newTitle })

      clearTimeout(self.debouncer)
      self.debouncer = setTimeout(function() {
        let json = {
          id: tag.id,
          name: tag.name,
        }

        let token = getCookie('csrftoken')
        fetch('/tag/', {
          method: 'put',
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
          console.log(data)
        })
        
        console.log(newTitle)
      }, 300)
    }

    if (this.state.editor_enabled) {
      return (
        <div className="tag-info">
          <span>({tag.id})</span> - &nbsp;
          <input type="text" value={this.state.tag_name} onChange={e => updateTitle(e)} /> - &nbsp;
          <span>{tag.modified_at.toString() }</span>
          <div>
            <span className="btn" onClick={addTag}>ADD TAG</span> &nbsp;
            <span className="btn" onClick={deleteTag}>DELETE</span> &nbsp;
            <span className="btn" onClick={disableEditor}>VIEW</span> 
          </div>
        </div>
      )
    } else {
      return (
        <div className="tag-info">
          <span>({tag.id})</span> - &nbsp;
          <span>{this.state.tag_name}</span> - &nbsp;
          <span>{tag.modified_at.toString() }</span>
          <div>
            <span className="btn" onClick={addTag}>ADD TAG</span> &nbsp;
            <span className="btn" onClick={deleteTag}>DELETE</span> &nbsp;
            <span className="btn" onClick={enableEditor}>EDIT</span> 
          </div>
        </div>
      )
    }
  }
}

class LogEntry extends Component {
  constructor(props) {
    super(props)
    this.props = props
    this.debounce = null
    this.titleDebounce = null
    this.state = {
      enable_editor: false,
      content: props.entry.content,
      title: props.entry.title
    }
  }

  updateCode(newCode) {
    let self = this
    clearTimeout(this.debounce)
    this.debounce = setTimeout(function() {
      let json = {
        id: self.props.entry.id,
        title: self.state.title,
        content: newCode
      }

      let token = getCookie('csrftoken')
      fetch('/entry/' + self.props.entry.id + '/', {
        method: 'put',
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
        self.props.entry.title = self.state.title
        self.props.entry.content = newCode
        self.setState({
          content: newCode
        })
      })
    }, 300)
  }

  updateTitle(event) {
    let newTitle = event.currentTarget.value
    this.setState({
      title: newTitle
    });

    let self = this
    clearTimeout(this.titleDebounce)
    this.titleDebounce = setTimeout(function() {
      self.updateCode(self.state.content)
    }, 300)
  }

  deleteEntry(event) {
    let self = this
    let json = {
      id: self.props.entry.id
    }

    let token = getCookie('csrftoken')
    fetch('/entry/' + self.props.entry.id + '/', {
      method: 'delete',
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
      self.props._handleDelete(self.props.entry.id)
    })
  }

  moveEntry(event) {
    GraphSingleton.selected_node = this.props.entry
    GraphSingleton.moving_entry = this.props.entry
  }

  render() {
    let self = this
    function enableEditor() {
      self.setState({
        enable_editor: true
      })
    }

    function disableEditor() {
      self.setState({
        enable_editor: false
      })
    }

    let props = this.props
    if (props.entry === null) {
      return (
        <div>Nothing</div>
      )
    }

    let options = {
      lineNumbers: true,
    };

    let content = this.state.content
    let title = this.state.title
    if (this.state.enable_editor) {
      return (
        <div className="log-entry">
          <span className="title">{props.entry.id} -</span> 
          <input type="text" value={title} onChange={e => self.updateTitle(e)} /> 
          <div>
            <span className="enable-editor" onClick={disableEditor}>VIEW</span> 
          </div>
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
          <CodeMirror value={content} 
            onChange={this.updateCode.bind(this)} 
            options={options} />
        </div>
      )
    } else {
      return (
        <div className="log-entry">
          <span className="title">{props.entry.id} -</span>
          <span>{title}</span>
          <div>
            <span className="enable-editor" onClick={enableEditor}>EDIT</span> &nbsp;
            <span className="enable-editor" onClick={e => self.deleteEntry(e)}>DELETE</span> &nbsp;
            <span className="enable-editor" onClick={e => self.moveEntry(e)}>MOVE</span> 
          </div>
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

class Canvas extends Component {
  constructor(props) {
    super(props);
    this.top_lft = new Vector(2400, 2400)
    this.graph = GraphSingleton
    this.entriesById = {}
    this.canvas_ref = React.createRef()

    this.physicsTimer = null

    this.holdMouseTimer = null
    this.mouseX = 0
    this.mouseY = 0
    this.newMouseX = 0
    this.newMouseY = 0
    this.zoom = 4

    this.clicked = false
    this.clickTimer = null
    this.queryDebounce = null
    this.next_tag_id = -1

    this.state = {
      query: '',
      entry: null,
      entries: [],
      tag: {name: '', modified_at: ''},
      holding_node: false,
    };
  }

  updateQuery(event) {
    let newQuery = event.currentTarget.value
    this.setState({
      query: newQuery
    });

    let self = this
    clearTimeout(this.queryDebounce)
    this.queryDebounce = setTimeout(function() {
      Physics.temperature = 500
      self.counter = 500
      self.graph.rankNodes(newQuery)
    }, 300)
  }

  getTagSize(node) {
    return 20 + 80 * node.total_entries / 500
  }

  updateTopLft(new_top_lft) {
    this.top_lft = new_top_lft

    if (this.top_lft.x < 0) this.top_lft.x = 0
    if (this.top_lft.y < 0) this.top_lft.y = 0
    if (this.top_lft.x + 800 * this.zoom > 8000) this.top_lft.x = 8000 - 800 * this.zoom
    if (this.top_lft.y + 800 * this.zoom > 8000) this.top_lft.y = 8000 - 800 * this.zoom
  }

  changeEntryTag(entry, tag) {
    let json = {
      id: entry.id,
      tags: [tag.name]
    }

    if (entry.tags.length) {
      for (let i = 0; i < entry.tags.length; i++) {
        let t = GraphSingleton.getTagByName(entry.tags[i])
        console.log(t.name)
        t.removeEntry(entry.id)
      }
    } else {
      let t = GraphSingleton.getTagByName('other')
      t.removeEntry(entry.id)
    }
    tag.entries.unshift(entry.id)

    let token = getCookie('csrftoken')
    fetch('/entry/' + entry.id + '/', {
      method: 'put',
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
      console.log(data)
    })
  }

  handleMouse(event) {
    this.newMouseX = event.clientX;
    this.newMouseY = event.clientY;
    if (event.type === "mousedown") {
      if (this.graph.replacing) {
        this.graph.replacing = false

        let mousePos = new Vector(this.newMouseX, this.newMouseY).sub(new Vector(20, 20)).multiply(this.zoom).add(this.top_lft)
        let node = this.graph.getClosestNode(this.graph.selected_node)

        let distance = node.pos.distance_to(this.graph.selected_node.pos)
        if (distance > 300) {
          this.graph.old_parent.addChild(this.graph.selected_node)
        } else {
          let self = this
          let token = getCookie('csrftoken')
          let json = {
            id: this.graph.selected_node.id,
            name: this.graph.selected_node.name,
            parent: node.id
          }

          fetch('/tag/', {
            method: 'put',
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
            console.log(data)
            node.addChild(self.graph.selected_node)
          })
        }
      }

      holding_mouse = true
      this.mouseX = this.newMouseX
      this.mouseY = this.newMouseY

      this.state.holding_node = false
      let mousePos = new Vector(this.mouseX, this.mouseY).sub(new Vector(20, 20))
      for (let i = 0; i < this.graph.nodes.length; i++) {
        let node = this.graph.nodes[i]
        if (!node.active) continue

        let pos = node.pos.sub(this.top_lft).div(this.zoom)
        let distance = pos.distance_to(mousePos)

        let size = 10 / this.zoom
        if (node.type === 'tag') {
          size = this.getTagSize(node) / this.zoom
        }

        if (distance < size) {
          if (this.graph.moving_entry) {
            this.changeEntryTag(this.graph.moving_entry, node)
            this.graph.moving_entry = null
            return
          }

          this.state.holding_node = true
          this.graph.selected_node = node
 
          let entries = [node.entry]
          if (this.graph.selected_node.type === 'tag') {
            let self = this
            let entry_ids = node.entries
            entries = entry_ids.map(id => {
              return self.entriesById[id]
            })
          }
          this.setState({
            entries: entries,
            tag: node,
          })

          if (this.clicked) {
            let tag_id = this.graph.selected_node.id
            let parent = this.graph.getTagParent(tag_id)
            parent.removeChild(tag_id)
            this.graph.replacing = true
            this.graph.old_parent = parent
          }

          let self = this
          this.clicked = true
          this.clickTimer = setTimeout(function() {
            self.clicked = false
          }, 300)
          break
        }
      }

      let self = this
      this.timer = setInterval(function(){
	if (!holding_mouse && !self.graph.replacing) {
          clearInterval(self.timer)
	  return
	}

        if (self.graph.selected_node !== null && self.state.holding_node) {
          let node = self.graph.selected_node
          if (node !== undefined) {
            let mousePos = new Vector(self.newMouseX, self.newMouseY).sub(new Vector(20, 20))
            node.pos = self.top_lft.add(mousePos.multiply(self.zoom))
            Physics.temperature = 500
            self.counter = 500
          }
        } else {
          let dragDirection = new Vector(self.newMouseX - self.mouseX, self.newMouseY - self.mouseY)
          dragDirection = dragDirection.multiply(SENSIBILITY)
          self.updateTopLft(self.top_lft.add(dragDirection.multiply(self.zoom)))
          self.mouseX = self.newMouseX
          self.mouseY = self.newMouseY
        }
      }, 10);

      this.graph.moving_entry = null
    } else if (event.type === "mouseup") {
      clearInterval(this.holdMouseTimer)
    }
  }

  drawCircle(ctx, pos, radius, color, lineWidth) {
    lineWidth = lineWidth || 1

    ctx.save()
    ctx.beginPath()
    ctx.arc(pos.x, pos.y, radius, 0, 2 * Math.PI)
    ctx.fillStyle = color
    ctx.fill()
    ctx.lineWidth = lineWidth
    ctx.strokeStyle = '#000000'
    ctx.stroke()
    ctx.restore()
  }

  drawRectangle(ctx, pos, size) {
    ctx.save()
    ctx.beginPath()
    ctx.rect(pos.x, pos.y, size.x, size.y);
    ctx.fillStyle = '#ee9999'
    ctx.fill()
    ctx.fillStyle = '#000000'
    ctx.lineWidth = 1
    ctx.strokeStyle = '#ff0000'
    ctx.stroke()
    ctx.restore()
  }

  drawText(ctx, text, pos) {
    ctx.font = '10px monospace'
    ctx.textAlign = 'center'
    ctx.fillText(text, pos.x, pos.y + 4)
  }

  drawLine(ctx, p1, p2, color, width) {
    ctx.beginPath();
    ctx.lineWidth = width
    ctx.strokeStyle = color
    ctx.moveTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);
    ctx.stroke();
  }

  drawEdges(ctx) {
    // this.graph.nodes.forEach(node => {
    //   if (!node.active) return;
    //   
    //   node.entries.forEach(id => {
    //     let destNode = this.graph.getNodeById(id)
    //     if (destNode === undefined) return
    //     if (!destNode.active) return;

    //     // this.drawLine(ctx, node.pos.sub(this.top_lft).div(this.zoom), 
    //     //   destNode.pos.sub(this.top_lft).div(this.zoom), '#999999', 1)
    //   })
    // });

    this.graph.nodes.forEach(node => {
      if (!node.active) return;

      node.children.forEach(id => {
        let destNode = this.graph.getTagById(id)
        if (destNode === undefined) return
        if (!destNode.active) return;

        this.drawLine(ctx, node.pos.sub(this.top_lft).div(this.zoom), 
                      destNode.pos.sub(this.top_lft).div(this.zoom), 
                      '#999999', 2)
      })
    });
  }

  drawNodes(ctx) {
    this.graph.nodes.forEach(node => {
      if (!node.active) return;

      let pos = node.pos.sub(this.top_lft).div(this.zoom)
      if (node.type === 'entry') {
        let size = 10 / this.zoom
        this.drawCircle(ctx, pos, size, '#ee9999', 1)

        // let top_lft = pos.sub(new Vector(size/2, size/2))
        // this.drawRectangle(ctx, top_lft, new Vector(size, size))

        if (this.zoom < 2) {
          let textPos = pos.sub(new Vector(0, size + 10))
          this.drawText(ctx, node.name, textPos)
        }
      } else if (node.type === 'tag') {
        let size = this.getTagSize(node) / this.zoom

        let lineWidth = 1
        if (this.graph.selected_node !== null) {
          if (this.graph.selected_node.id === node.id) {
            lineWidth = 3
          }
        }

        let days_old = 0
        if (node.modified_at instanceof Date) {
          days_old = -daysBetween(new Date(), node.modified_at)
        }

        days_old = (days_old > 14) ? 14 : days_old
        let lightness = 50 + (days_old * 45 / 14)

        this.drawCircle(ctx, pos, size, 'hsl(142, 100%, ' + lightness.toString() + '%)', lineWidth)
        this.drawText(ctx, node.total_entries.toString(), pos)

        let textPos = pos.sub(new Vector(0, size + 10))
        this.drawText(ctx, node.name, textPos)
      }
    });
  }

  updateCanvas() {
    const canvas = this.canvas_ref.current;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h)
    this.drawEdges(ctx)
    this.drawNodes(ctx)
  }

  registerOnWheel() {
    let self = this
    this.canvas_ref.current.addEventListener('wheel', (e) => {
      event.preventDefault()

      let oldZoom = self.zoom
      self.zoom += WHEEL_SENSITIVITY * event.deltaY

      if (self.zoom < MIN_ZOOM) self.zoom = MIN_ZOOM
      if (self.zoom > MAX_ZOOM) self.zoom = MAX_ZOOM

      self.updateTopLft(self.top_lft.add(new Vector(600, 400).multiply(oldZoom - self.zoom)))
    }, { passive: false })
  }

  componentDidMount() {
    this.registerOnWheel()

    let self = this
    this.counter = 500
    this.physicsTimer = setInterval(() => {
      if (self.counter == 0) {
        return
      }

      self.counter--
      this.graph.update()
    }, 50);

    setInterval(() => {
      this.updateCanvas()
    }, 50);

    fetch("/all")
      .then(res => res.json())
      .then(
        (result) => {
          for (let i = 0; i < result.entries.length; i++) {
            let entry = result.entries[i]
            this.graph.createEntryNode(entry)
            this.entriesById[entry.id] = entry
          }
          
          for (let i = 0; i < result.tags.length; i++) {
            this.graph.createTagNode(result.tags[i])
            this.next_tag_id = Math.max(this.next_tag_id, result.tags[i].id+1)
          }

          this.graph.createIrModel()
          this.graph.setMainTags(result.main_tags)
          this.graph.rankNodes("")
        },
        (error) => {
          this.setState({
            isLoaded: true,
            error
          });
        }
      )
  }

  deleteEntry(id){
    this.setState(prevState => ({
      entries: prevState.entries.filter(e => e.id != id )
    }))
  }

  render() {
    let self = this
    let token = getCookie('csrftoken')
    function addEntry(event) {
      let tag = self.graph.selected_node
      let json = {
        parent_id: tag.id,
        title: 'New entry'
      }

      fetch('/entry/', {
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
      }).then(function(entry) {
        self.graph.createEntryNode(entry)
        self.entriesById[entry.id] = entry
        tag.entries.unshift(entry.id)

        let entries = self.state.entries
        entries.unshift(entry)
        self.setState({
          entries: entries
        })
      })
    }

    return (
      <div>
        <div className="main-container">
          <canvas width="800" height="800" ref={this.canvas_ref} 
	    onMouseMove={e => this.handleMouse(e)} 
	    onMouseDown={e => this.handleMouse(e)} 
	    onMouseUp={e => this.handleMouse(e)} />
          </div>
          <div className="log-entries">
            <div>
              <input className="query-box" type="text" value={this.state.query} onChange={e => this.updateQuery(e)} />
            </div>
            <span className="btn" onClick={addEntry}>ADD ENTRY</span> &nbsp;
            <TagEditor tag={this.state.tag} />
            <div>
              {this.state.entries.map(entry => {
                return <LogEntry entry={entry} key={entry.id} _handleDelete={this.deleteEntry.bind(this)} />;
              })}
            </div>
          </div>
      </div>
    )
  }
}

window.addEventListener('mouseup', (event) => {
  holding_mouse = false
})

export default Canvas;
