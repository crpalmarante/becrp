window.NumpadModule = class NumpadModule {
  constructor() {
    this.mode = 'default';
    this.buffer = '';
    this.callback = null;
    this.contextLabel = '';
    this.quickBtns = [];
    this.el = document.getElementById('numpadPanel');
    this._init();
  }
  _init() {
    if (!this.el) return;
    this.el.addEventListener('click', e => {
      const btn = e.target.closest('[data-np]');
      if (!btn) return;
      const action = btn.dataset.np;
      if (action === 'ok') this.ok();
      else if (action === 'bs') this.backspace();
      else if (action === 'clr') this.clear();
      else if (action === 'esc') this.esc();
      else if (action === 'mode') this.switchMode(btn.dataset.npMode);
      else this.input(action);
    });
    document.addEventListener('keydown', e => {
      if (this.mode === 'default') return;
      if (e.key >= '0' && e.key <= '9') { this.input(e.key); e.preventDefault(); }
      if (e.key === '.') { this.input('.'); e.preventDefault(); }
      if (e.key === ',') { this.input(','); e.preventDefault(); }
      if (e.key === 'Backspace') { this.backspace(); e.preventDefault(); }
      if (e.key === 'Enter') { this.ok(); e.preventDefault(); }
      if (e.key === 'Escape') { this.esc(); e.preventDefault(); }
    });
    bus.on('numpad:enter', d => this.enterMode(d.mode, d.opts));
    bus.on('numpad:exit', () => this.exitMode());
  }
  input(v) {
    if (this.mode === 'default') return;
    const ops = '+-×÷*/';
    if (ops.includes(v) && this.mode === 'default') {
      this.buffer += v;
    } else if (v === '=' || v === 'enter') {
      this.ok();
    } else {
      this.buffer += v;
    }
    this.render();
    bus.emit('numpad:input', { buffer: this.buffer, mode: this.mode });
  }
  backspace() {
    this.buffer = this.buffer.slice(0, -1);
    this.render();
  }
  clear() {
    this.buffer = '';
    this.render();
  }
  esc() {
    if (this.callback) this.callback(null);
    this.exitMode();
  }
  ok() {
    if (!this.buffer) return;
    let val = this.buffer;
    try {
      if (/[+\-×÷*/]/.test(val)) {
        val = val.replace(/×/g, '*').replace(/÷/g, '/');
        val = String(eval(val));
      }
      val = val.replace(',', '.');
      if (this.callback) this.callback(val);
    } catch (e) {
      notifs.err('Expressão inválida');
    }
    this.exitMode();
  }
  enterMode(mode, opts) {
    this.mode = mode;
    this.buffer = opts?.initial || '';
    this.callback = opts?.callback || null;
    this.contextLabel = opts?.label || '';
    this.quickBtns = opts?.quickBtns || [];
    this.render();
    this.el?.classList.add('active');
  }
  exitMode() {
    this.mode = 'default';
    this.buffer = '';
    this.callback = null;
    this.contextLabel = '';
    this.quickBtns = [];
    this.render();
    this.el?.classList.remove('active');
  }
  switchMode(mode) {
    bus.emit('numpad:enter', { mode, opts: {} });
  }
  render() {
    if (!this.el) return;
    const display = this.el.querySelector('.np-display');
    if (display) display.textContent = this.buffer || '0';
    const label = this.el.querySelector('.np-label');
    if (label) label.textContent = this.contextLabel;
    const info = this.el.querySelector('.np-mode');
    if (info) info.textContent = this.mode !== 'default' ? this.mode.toUpperCase() : '';
  }
  applyQuick(pct) {
    if (!this.callback) return;
    this.callback(String(pct));
    this.exitMode();
  }
};
