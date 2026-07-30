window.Notifications = class Notifications {
  constructor() {
    this._container = null;
    this._center = null;
    this._timer = null;
    this._notifs = [];
    this._init();
    bus.on('notify', d => this.show(d.msg, d.type, d.timeout));
  }
  _init() {
    this._container = document.getElementById('toastContainer');
    if (!this._container) {
      this._container = document.createElement('div');
      this._container.id = 'toastContainer';
      document.body.appendChild(this._container);
    }
    this._center = document.getElementById('notifCenter');
    if (!this._center) {
      this._center = document.createElement('div');
      this._center.id = 'notifCenter';
      this._center.innerHTML = '<div class="nc-header"><span>Notificações</span><button onclick="notifs.toggleCenter()">✕</button></div><div class="nc-body"></div>';
      this._center.style.display = 'none';
      document.body.appendChild(this._center);
    }
  }
  show(msg, type, timeout) {
    const el = document.createElement('div');
    el.className = 'toast' + (type ? ' toast-' + type : '');
    el.textContent = msg;
    this._container.appendChild(el);
    requestAnimationFrame(() => el.classList.add('show'));
    const t = timeout || (type === 'err' ? 5000 : 3000);
    setTimeout(() => { el.classList.remove('show'); setTimeout(() => el.remove(), 300); }, t);
    this._notifs.push({ msg, type, ts: Date.now() });
    this._renderCenter();
    if (this._notifs.length > 100) this._notifs.shift();
    bus.emit('notification:shown', { msg, type });
  }
  info(msg) { this.show(msg, 'info'); }
  ok(msg) { this.show(msg, 'ok'); }
  warn(msg) { this.show(msg, 'warn', 5000); }
  err(msg) { this.show(msg, 'err', 6000); }
  toggleCenter() {
    const d = this._center.style.display;
    this._center.style.display = d === 'flex' ? 'none' : 'flex';
    if (this._center.style.display === 'flex') this._renderCenter();
  }
  _renderCenter() {
    const body = this._center.querySelector('.nc-body');
    if (!body) return;
    const recent = this._notifs.slice(-50).reverse();
    body.innerHTML = recent.map(n =>
      `<div class="nc-item${n.type ? ' nc-'+n.type : ''}">${n.msg}<span class="nc-ts">${new Date(n.ts).toLocaleTimeString()}</span></div>`
    ).join('');
  }
  get badge() { return this._notifs.filter(n => Date.now() - n.ts < 60000).length; }
};

window.notifs = new Notifications();
