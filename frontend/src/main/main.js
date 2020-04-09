import React, {Component} from 'react';
import {Link, Switch, Route, Redirect} from 'react-router-dom';
import {Container, Row} from 'reactstrap';
import GraphSingleton from './graph.js';
import RankerSingleton from './ranker.js';
import {Vector, Physics} from './physics.js';
import API from './api.js';
import {UiStateSingleton, States} from './uistate.js';
import Entry from './entry.js';
import Tag from './tag.js';

let holding_mouse = false
const SENSIBILITY = 4
const WHEEL_SENSITIVITY = 0.01
const MIN_ZOOM = 0.25
const MAX_ZOOM = 16
const DOUBLE_CLICK_DELAY = 300
const CANVAS_WIDTH = 600
const CANVAS_HEIGHT = 600
const SPACE_WIDTH = MAX_ZOOM * CANVAS_WIDTH
const SPACE_HEIGHT = MAX_ZOOM * CANVAS_HEIGHT

class Main extends Component {
  constructor(props) {
    super(props);
    this.canvas_ref = React.createRef()
    this.zoom = 4
    this.top_lft = new Vector(
      (SPACE_WIDTH - CANVAS_WIDTH*this.zoom)/2, 
      (SPACE_HEIGHT - CANVAS_HEIGHT*this.zoom)/2
    )

    this.hold_mouse_timer = null
    this.mouseX = 0
    this.mouseY = 0
    this.newMouseX = 0
    this.newMouseY = 0

    this.clicked = false
    this.query_debounce = null

    this.state = {
      query: '',
      entry: null,
      entries: [],
      tag: {name: '', modified_at: ''},
    };
  }

  getCanvasPos(pos) {
    return pos.sub(this.top_lft).div(this.zoom)
  }

  updateTopLft(new_top_lft) {
    this.top_lft = new_top_lft
    if (this.top_lft.x < 0) this.top_lft.x = 0
    if (this.top_lft.y < 0) this.top_lft.y = 0
    if (this.top_lft.x + CANVAS_WIDTH * this.zoom > SPACE_WIDTH) 
      this.top_lft.x = SPACE_WIDTH - CANVAS_WIDTH * this.zoom
    if (this.top_lft.y + CANVAS_HEIGHT * this.zoom > SPACE_HEIGHT) 
      this.top_lft.y = SPACE_HEIGHT - CANVAS_HEIGHT * this.zoom
  }

  updateQuery(event) {
    let new_query = event.currentTarget.value
    this.setState({
      query: new_query
    });

    let self = this
    clearTimeout(this.query_debounce)
    this.query_debounce = setTimeout(function() {
      let entries = GraphSingleton.selected_node.getEntries()
      if (new_query.length >= 2) {
        RankerSingleton.scoreEntries(new_query, entries)
        entries = entries.filter(e => e.score > 0)
        entries.sort((a, b) => {
          if (a.score > b.score) {
            return -1
          } else if (a.score < b.score) {
            return 1
          } else if (a.modified_at < b.modified_at) {
            return -1;
          } else if (a.modified_at > b.modified_at) {
            return 1;
          }
          return 0;
        })  
      }
      self.setState({ entries: entries })
    }, 300)
  }

  getMousePos() {
    return new Vector(this.mouse_x, this.mouse_y).sub(new Vector(20, 20))
  }

  maybeGetClickedTag(mouse_pos) {
    let tags = GraphSingleton.getTags()
    for (let i = 0; i < tags.length; i++) {
      let pos = this.getCanvasPos(tags[i].pos)
      let distance = pos.distance_to(this.getMousePos())
      let size = this.getTagSize(tags[i]) / this.zoom
      if (distance < size) return tags[i]
    }
    return null
  }

  onTagClick(tag) {
    if (GraphSingleton.moving_entry) {
      GraphSingleton.changeEntryParent(GraphSingleton.moving_entry, tag)
      GraphSingleton.selected_node = null
    }

    GraphSingleton.selectTag(tag.id)
    this.setState({
      entries: tag.getEntries(),
      tag: tag,
      query: '',
    })
  }

  onTagDoubleClick(tag) {
    tag.parent.removeChild(tag.id)
    GraphSingleton.replacing = true
  }

  endReplacing(event) {
    GraphSingleton.replacing = false
    let parent = GraphSingleton.getClosestNode(GraphSingleton.selected_node)
    let distance = parent.pos.distance_to(GraphSingleton.selected_node.pos)
    if (distance < 300) {
      GraphSingleton.moveSelectionToParent(parent)
    }
  }

  handleMouse(event) {
    let self = this
    this.new_mouse_x = event.clientX;
    this.new_mouse_y = event.clientY;
    if (event.type === "mousedown") {
      if (GraphSingleton.replacing) this.endReplacing()
      holding_mouse = true
      this.mouse_x = this.new_mouse_x
      this.mouse_y = this.new_mouse_y

      let clicked_tag = this.maybeGetClickedTag()
      if (clicked_tag !== null) {
        GraphSingleton.dragging_tag = true
        if (this.clicked) {
	  this.onTagDoubleClick(clicked_tag)
        } else {
          this.onTagClick(clicked_tag)
	}

        // Detect double click.
        this.clicked = true
        setTimeout(() => {self.clicked = false}, DOUBLE_CLICK_DELAY)
      }

      GraphSingleton.moving_entry = null
    } else if (event.type === "mouseup") {
      holding_mouse = false
      GraphSingleton.dragging_tag = false
    }
  }

  registerOnMouseDrag() {
    let self = this
    setInterval(function(){
      if (!holding_mouse && !GraphSingleton.replacing) return

      if (GraphSingleton.replacing || GraphSingleton.dragging_tag) {
        let mousePos = new Vector(self.new_mouse_x, self.new_mouse_y).sub(new Vector(20, 20))
        GraphSingleton.selected_node.pos = self.top_lft.add(mousePos.multiply(self.zoom))
        Physics.temperature = 500
      } else {
        let dragDirection = new Vector(self.new_mouse_x - self.mouse_x, self.new_mouse_y - self.mouse_y)
        dragDirection = dragDirection.multiply(SENSIBILITY)
        self.updateTopLft(self.top_lft.add(dragDirection.multiply(self.zoom)))
        self.mouse_x = self.new_mouse_x
        self.mouse_y = self.new_mouse_y
      }
    }, 10);
  }

  addEntry(entry){
    let entries = this.state.entries
    entries.unshift(entry)
    this.setState({
      entries: entries
    })
  }

  deleteEntry(id){
    this.setState(prevState => ({
      entries: prevState.entries.filter(e => e.id != id )
    }))
  }

  registerOnWheel() {
    let self = this
    this.canvas_ref.current.addEventListener('wheel', (e) => {
      event.preventDefault()

      let old_zoom = self.zoom
      self.zoom += WHEEL_SENSITIVITY * event.deltaY
      if (self.zoom < MIN_ZOOM) self.zoom = MIN_ZOOM
      if (self.zoom > MAX_ZOOM) self.zoom = MAX_ZOOM

      let stride = new Vector(400, 400).multiply(old_zoom - self.zoom)
      self.updateTopLft(self.top_lft.add(stride))
    }, { passive: false })
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
    ctx.closePath()
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
    ctx.closePath()
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

  getTagSize(tag) {
    return 20 + 80 * tag.total_entries / 500
  }

  getDaysOld(tag) {
    let days_old = 0
    if (tag.modified_at instanceof Date) {
      let diff_in_time = tag.modified_at.getTime() - (new Date()).getTime()
      days_old = diff_in_time / (1000 * 3600 * 24)
    }
    return days_old
  }

  drawEdges(ctx) {
    GraphSingleton.getTags().forEach(t => {
      t.children.forEach(c => {
        if (GraphSingleton.selected_node && c.id == GraphSingleton.selected_node.id && GraphSingleton.replacing)
          return
        this.drawLine(ctx, this.getCanvasPos(t.pos), this.getCanvasPos(c.pos),
                      '#999999', 2)
      })
    });
  }

  drawNodes(ctx) {
    GraphSingleton.getTags().forEach(tag => {
      let pos = this.getCanvasPos(tag.pos)
      let size = this.getTagSize(tag) / this.zoom

      // Width.
      let line_width = (tag.isSelected()) ? 3 : 1

      // Color.
      let days_old = this.getDaysOld(tag)
      days_old = (days_old > 14) ? 14 : days_old
      let lightness = 50 + (-days_old * 45 / 14)

      this.drawCircle(ctx, pos, size, 'hsl(142, 100%, ' + lightness.toString() + '%)', line_width)
      this.drawText(ctx, tag.total_entries.toString(), pos)

      let textPos = pos.sub(new Vector(0, size + 10))
      this.drawText(ctx, tag.name, textPos)
    });
  }

  componentDidMount() {
    let self = this
    let center = new Vector(SPACE_WIDTH/2, SPACE_HEIGHT/2)
    GraphSingleton.load(center).then(() => {
      self.registerOnWheel()

      self.physicsTimer = setInterval(() => {
        GraphSingleton.update()
        GraphSingleton.main_tag.pos = center
      }, 50);

      setInterval(() => {
        const canvas = self.canvas_ref.current;
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;

        ctx.clearRect(0, 0, w, h)
        self.drawEdges(ctx)
        self.drawNodes(ctx)
      }, 50);

      self.registerOnMouseDrag()
      RankerSingleton.createVocab(GraphSingleton.getEntries())
    })
  }

  render() {
    let self = this
    return (
      <div className="app">
        <div className="app-body">
          <div className="main">
            <div className="main-container">
              <canvas width={CANVAS_WIDTH} height={CANVAS_HEIGHT} ref={this.canvas_ref} 
                onMouseMove={e => this.handleMouse(e)} 
                onMouseDown={e => this.handleMouse(e)} 
                onMouseUp={e => this.handleMouse(e)} />
            </div>
            <div className="log-entries">
              <div>
                <input className="query-box" type="text" value={this.state.query} onChange={e => this.updateQuery(e)} />
              </div>
              <Tag tag={this.state.tag} _handleAddEntry={this.addEntry.bind(this)} />
              <div>
                {this.state.entries.map(entry => {
                  return <Entry entry={entry} key={entry.id} query={this.state.query} _handleDelete={this.deleteEntry.bind(this)} />;
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }
}

window.addEventListener('mouseup', (event) => {
  holding_mouse = false
})

export default Main;
