window.StateManager = class StateManager {
  constructor(initial) {
    this._state = { ...initial };
    this._undoStack = [];
    this._redoStack = [];
    this._maxUndo = 50;
    this._batch = null;
    this._snapshot();
  }
  get(key) {
    return key ? this._state[key] : { ...this._state };
  }
  set(key, val) {
    const prev = this._state[key];
    if (prev === val) return;
    const old = { ...this._state };
    this._state[key] = val;
    this._notify(key, val, prev);
    if (!this._batch) {
      this._snapshot(old);
      this._redoStack = [];
    }
  }
  update(patch) {
    const old = { ...this._state };
    let changed = false;
    for (const k of Object.keys(patch)) {
      if (this._state[k] !== patch[k]) {
        this._state[k] = patch[k];
        changed = true;
      }
    }
    if (!changed) return;
    for (const k of Object.keys(patch)) {
      this._notify(k, this._state[k], old[k]);
    }
    if (!this._batch) {
      this._snapshot(old);
      this._redoStack = [];
    }
  }
  beginBatch() {
    this._batch = [];
  }
  endBatch() {
    if (!this._batch) return;
    const old = this._batch;
    this._batch = null;
    this._snapshot(old);
    this._redoStack = [];
  }
  _snapshot(snap) {
    this._undoStack.push(snap || { ...this._state });
    if (this._undoStack.length > this._maxUndo)
      this._undoStack.shift();
  }
  _notify(key, val, prev) {
    if (this._batch) { this._batch.push({ key, val, prev }); return; }
    bus.emit('state:changed', { key, val, prev });
    bus.emit(`state:${key}:changed`, { val, prev });
  }
  undo() {
    if (this._undoStack.length < 2) return false;
    this._redoStack.push(this._undoStack.pop());
    const snap = this._undoStack[this._undoStack.length - 1];
    if (!snap) return false;
    const oldState = { ...this._state };
    this._state = { ...snap };
    for (const k of Object.keys(this._state)) {
      if (oldState[k] !== this._state[k])
        this._notify(k, this._state[k], oldState[k]);
    }
    bus.emit('state:undo', { state: this._state });
    return true;
  }
  redo() {
    if (!this._redoStack.length) return false;
    const snap = this._redoStack.pop();
    if (!snap) return false;
    const oldState = { ...this._state };
    this._state = { ...snap };
    this._snapshot();
    for (const k of Object.keys(this._state)) {
      if (oldState[k] !== this._state[k])
        this._notify(k, this._state[k], oldState[k]);
    }
    bus.emit('state:redo', { state: this._state });
    return true;
  }
  canUndo() { return this._undoStack.length > 1; }
  canRedo() { return this._redoStack.length > 0; }
  reset(initial) {
    this._state = { ...initial };
    this._undoStack = [];
    this._redoStack = [];
    this._snapshot();
    bus.emit('state:reset', { state: this._state });
  }
};

window.state = new StateManager({
  atendimentoId: 0,
  customer: { name: 'Consumidor Final', doc: '' },
  cart: [],
  selIdx: -1,
  operation: 'sale',
  frete: { label: 'Balcão', dest: 'balcao', val: 0 },
  activeSession: -1,
  sessions: [],
});
