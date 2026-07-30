window.CustomerModule = class CustomerModule {
  constructor() {
    this.customers = [
      { name: 'Consumidor Final', doc: '' },
      { name: 'João Silva', doc: '123.456.789-00', phone: '(47) 99999-9999' },
      { name: 'Maria Santos', doc: '987.654.321-00', phone: '(47) 98888-8888' },
      { name: 'Pedro Oliveira', doc: '111.222.333-44', phone: '(47) 97777-7777' },
    ];
    this.el = document.getElementById('custPanel');
    this.searchEl = document.getElementById('custSearch');
    this._init();
    bus.on('customer:open', () => this._toggle());
    bus.on('customer:set', d => this._set(d));
  }
  _init() {
    if (!this.el) return;
    if (this.searchEl) {
      this.searchEl.addEventListener('input', () => this._render());
      this.searchEl.addEventListener('keydown', e => {
        if (e.key === 'Escape') this._toggle();
      });
    }
    this._render();
  }
  _toggle() {
    if (!this.el) return;
    const show = this.el.classList.toggle('show');
    if (show) setTimeout(() => this.searchEl?.focus(), 100);
  }
  _set(d) {
    state.update({ customer: { name: d.name, doc: d.doc || '' } });
    bus.emit('customer:changed', d);
    this._render();
    this.el?.classList.remove('show');
  }
  _render() {
    const q = (this.searchEl?.value || '').toLowerCase();
    const filtered = this.customers.filter(c =>
      !q || c.name.toLowerCase().includes(q) || c.doc.includes(q) || (c.phone || '').includes(q)
    );
    const current = state.get('customer');
    const list = document.getElementById('custList');
    if (!list) return;
    list.innerHTML = filtered.map(c =>
      `<div class="cust-item ${c.name === current.name ? 'sel' : ''}" onclick="cust.set({name:'${c.name.replace(/'/g, "\\'")}',doc:'${c.doc}'})">
        <strong>${c.name}</strong>${c.doc ? '<br><span class="dim">'+c.doc+'</span>' : ''}</div>`
    ).join('');
    const header = document.getElementById('custHeaderName');
    if (header) header.textContent = current.name;
    const badge = document.getElementById('custBadge');
    if (badge) { badge.textContent = current.name !== 'Consumidor Final' ? current.name.charAt(0) : '?'; }
  }
  set(d) { this._set(d); }
  quickCreate(name) {
    if (!name || name === 'Consumidor Final') return;
    this.customers.push({ name, doc: '', phone: '' });
    this._set({ name, doc: '' });
    notifs.info('Cliente criado: ' + name);
  }
};

window.cust = null;
