const States = Object.freeze({
  DEFAULT:               Symbol("default"),
  CHANGE_TAG_PARENT:     Symbol("change_tag_parent"),
  CHANGE_ENTRY_CATEGORY: Symbol("change_entry_category"),
  MOVE_TAG:              Symbol("move_tag"),
});

class UiState {
  constructor() {
    this.state = States.DEFAULT
    this.selected_node = null
  }

  getState() {
    return this.state
  }
}

let UiStateSingleton = new UiState()
export { 
  UiStateSingleton,
  States
}
