window.TimelineModule = class TimelineModule {
  constructor() {
    this.entries = [];
    this.el = document.getElementById('timelinePanel');
    this.max = 100;
    this._init();
  }
  _init() {
    bus.on('timeline:add', d => this.add(d));
    bus.on('timeline:clear', () => this.clear());
    bus.on('session:new', () => this.clear());
  }
  add(data) {
    this.entries.push({ action: data.action, detail: data.detail || '', ts: Date.now() });
    if (this.entries.length > this.max) this.entries.shift();
    this._render();
  }
  clear() {
    this.entries = [];
    this._render();
  }
  _render() {
    if (!this.el) return;
    if (!this.entries.length) {
      this.el.innerHTML = '<div class="empty" style="padding:8px;font-size:10px;color:var(--dim)">Nenhum evento</div>';
      return;
    }
    this.el.innerHTML = this.entries.map(e =>
      `<div class="tl-item">
        <span class="tl-time">${new Date(e.ts).toLocaleTimeString()}</span>
        <span class="tl-action">${e.action}</span>
        ${e.detail ? '<span class="tl-detail">' + e.detail + '</span>' : ''}
      </div>`
    ).reverse().join('');
    this.el.scrollTop = 0;
  }
};

window.timeline = null;
