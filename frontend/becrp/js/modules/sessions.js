window.SessionsModule = class SessionsModule {
  constructor() {
    this.el = document.getElementById('sessionBar');
    this._init();
  }
  _init() {
    state.update({ sessions: [], activeSession: -1 });
    this._new();
    bus.on('session:new', () => this._new());
    bus.on('session:switch', d => this._switch(d.idx));
    bus.on('session:suspend', () => this._suspend());
    bus.on('session:close', d => this._close(d.idx));
    bus.on('session:recover', () => this._recoverLast());
    bus.on('session:list', () => this._render());
    actions.register('session:new', { label: 'Novo Atendimento', context: 'session', shortcut: 'Ctrl+N', handler: () => this._new() });
    actions.register('session:suspend', { label: 'Suspender', context: 'session', shortcut: 'F10', handler: () => this._suspend() });
    actions.register('session:recover', { label: 'Recuperar', context: 'session', shortcut: 'F11', handler: () => this._recoverLast() });
  }
  _new() {
    const id = state.get('atendimentoId') + 1;
    state.update({ atendimentoId: id });
    const s = { id: 'AT-' + String(id).padStart(6, '0'), customer: state.get('customer'), cart: [], status: 'active', createdAt: Date.now() };
    const sessions = state.get('sessions');
    sessions.push(s);
    state.update({ sessions: [...sessions], activeSession: sessions.length - 1, cart: [], selIdx: -1, customer: { name: 'Consumidor Final', doc: '' } });
    this._render();
    bus.emit('timeline:add', { action: 'Atendimento iniciado', detail: s.id });
    this._updateHeader(s);
  }
  _switch(idx) {
    const sessions = state.get('sessions');
    if (idx < 0 || idx >= sessions.length || idx === state.get('activeSession')) return;
    this._saveCurrent();
    const s = sessions[idx];
    state.update({ activeSession: idx, cart: [...(s.cart || [])], customer: { ...(s.customer || { name: 'Consumidor Final', doc: '' }) } });
    this._render();
    this._updateHeader(s);
    bus.emit('cart:render');
  }
  _suspend() {
    this._saveCurrent();
    const sessions = state.get('sessions');
    const idx = state.get('activeSession');
    if (idx >= 0 && idx < sessions.length) sessions[idx].status = 'suspended';
    state.update({ sessions: [...sessions] });
    this._new();
    notifs.info('Atendimento suspenso');
    bus.emit('timeline:add', { action: 'Atendimento suspenso' });
  }
  _recoverLast() {
    const sessions = state.get('sessions');
    const suspended = sessions.findIndex(s => s.status === 'suspended');
    if (suspended < 0) { notifs.warn('Nenhum atendimento suspenso'); return; }
    sessions[suspended].status = 'active';
    state.update({ sessions: [...sessions] });
    this._switch(suspended);
    notifs.ok('Atendimento recuperado');
  }
  _close(idx) {
    let sessions = state.get('sessions');
    if (idx < 0 || idx >= sessions.length) return;
    sessions.splice(idx, 1);
    const active = state.get('activeSession');
    let newActive = active;
    if (active === idx) {
      newActive = sessions.length > 0 ? Math.min(idx, sessions.length - 1) : -1;
    } else if (active > idx) {
      newActive = active - 1;
    }
    if (newActive < 0) {
      state.update({ sessions: [...sessions], activeSession: -1 });
      this._new();
    } else {
      state.update({ sessions: [...sessions], activeSession: newActive });
      this._switch(newActive);
    }
    this._render();
  }
  _saveCurrent() {
    const sessions = state.get('sessions');
    const idx = state.get('activeSession');
    if (idx < 0 || idx >= sessions.length) return;
    sessions[idx] = {
      ...sessions[idx],
      cart: [...state.get('cart')],
      customer: { ...state.get('customer') },
    };
    state.update({ sessions: [...sessions] });
  }
  _render() {
    if (!this.el) return;
    const sessions = state.get('sessions');
    const active = state.get('activeSession');
    this.el.innerHTML = sessions.map((s, i) => {
      const isActive = i === active;
      const count = i === active ? state.get('cart').length : (s.cart?.length || 0);
      const stCls = isActive ? 'active' : s.status === 'suspended' ? 'suspended' : '';
      return `<div class="ss-item ${stCls}" onclick="sessions._switch(${i})" title="${s.id}">
        <span class="ss-id">${s.id.replace('AT-','')}</span>
        ${count > 0 ? `<span class="ss-badge">${count}</span>` : ''}
        ${isActive ? '<span class="ss-arrow">▶</span>' : ''}
      </div>`;
    }).join('') +
    `<div class="ss-item ss-new" onclick="sessions._new()" title="Novo Atendimento">+</div>`;
  }
  _updateHeader(s) {
    const el = document.getElementById('sessionHeader');
    if (!el) return;
    el.innerHTML = `<span class="sh-id">${s.id}</span><span class="sh-cust">${state.get('customer').name}</span>`;
  }
};

window.sessions = null;
