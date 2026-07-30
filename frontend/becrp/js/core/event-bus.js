window.EventBus = class EventBus {
  constructor() {
    this._handlers = {};
    this._history = [];
    this._maxHistory = 1000;
    this._historyEnabled = true;
  }
  on(event, handler, ctx) {
    (this._handlers[event] = this._handlers[event] || []).push({ handler, ctx });
    return () => this.off(event, handler);
  }
  off(event, handler) {
    const h = this._handlers[event];
    if (!h) return;
    this._handlers[event] = h.filter(e => e.handler !== handler);
  }
  emit(event, data) {
    if (this._historyEnabled) {
      this._history.push({ event, data, ts: Date.now() });
      if (this._history.length > this._maxHistory)
        this._history.splice(0, this._history.length - this._maxHistory);
    }
    const h = this._handlers[event];
    if (!h) return;
    for (const e of h) {
      try { e.handler.call(e.ctx || null, data, event); }
      catch (err) { console.error(`EventBus[${event}]:`, err); }
    }
  }
  once(event, handler, ctx) {
    const unsub = this.on(event, (...args) => { unsub(); handler.apply(ctx, args); }, ctx);
  }
  clear(event) {
    if (event) delete this._handlers[event];
    else this._handlers = {};
  }
  getHistory(filter) {
    if (!filter) return [...this._history];
    return this._history.filter(h => !filter || h.event === filter);
  }
  enableHistory(v) { this._historyEnabled = v; }
};

window.bus = new EventBus();
