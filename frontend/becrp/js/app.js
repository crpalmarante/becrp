window.App = class App {
  constructor() {
    this.sections = { atendimento: true, pedidos: false, cotacoes: false, montagens: false };
    this.rightTab = 'timeline';
    this._initActions();
    this._initKeyboard();
    this._initFrete();
    this._initModules();
    this._loadInitialData();
    this._renderShortcuts();
  }

  _initModules() {
    window.numpad = new NumpadModule();
    window.cust = new CustomerModule();
    window.prods = new ProductsModule();
    window.cartModule = new CartModule();
    window.sessions = new SessionsModule();
    window.pay = new PaymentModule();
    window.pedidos = new PedidosModule();
    window.cotacoes = new CotacoesModule();
    window.montagens = new MontagensModule();
    window.timeline = new TimelineModule();

    bus.on('cart:select', d => this._updateActionPanel(d));
    bus.on('state:cart:changed', () => cartModule.render());
    bus.on('section:switch', s => this._switchSection(s));
    bus.on('state:frete:changed', () => this._renderFrete());
    bus.on('payment:confirmed', () => {
      bus.emit('cotacao:list');
      bus.emit('pedido:list');
    });
  }

  _initActions() {
    actions.register('app:logout', {
      label: 'Sair', context: 'global', shortcut: '',
      handler: () => this.logout()
    });
    actions.register('app:finalizar', {
      label: 'Finalizar Atendimento', context: 'cart', shortcut: 'F12',
      handler: () => this.finalizar()
    });
    actions.register('app:undo', {
      label: 'Desfazer', context: 'global', shortcut: 'Ctrl+Z',
      handler: () => { if (state.undo()) notifs.info('Desfeito'); }
    });
    actions.register('app:redo', {
      label: 'Refazer', context: 'global', shortcut: 'Ctrl+Shift+Z',
      handler: () => { if (state.redo()) notifs.info('Refeito'); }
    });
    actions.register('app:search', {
      label: 'Busca Universal', context: 'global', shortcut: 'Ctrl+K',
      handler: () => {
        const el = document.getElementById('prodSearch');
        if (el) { el.focus(); el.select(); }
      }
    });
    actions.register('app:notifications', {
      label: 'Central de Notificações', context: 'global', shortcut: 'Ctrl+N',
      handler: () => notifs.toggleCenter()
    });
    actions.register('app:shortcuts', {
      label: 'Atalhos do Teclado', context: 'global', shortcut: '?',
      handler: () => this.toggleShortcuts()
    });
  }

  _initKeyboard() {
    document.addEventListener('keydown', e => {
      if (e.ctrlKey && e.key === 'z') { e.preventDefault(); actions.execute('app:undo'); return; }
      if (e.ctrlKey && e.shiftKey && e.key === 'Z') { e.preventDefault(); actions.execute('app:redo'); return; }
      if (e.ctrlKey && e.key === 'k') { e.preventDefault(); actions.execute('app:search'); return; }
      if (e.ctrlKey && e.key === 'n') { e.preventDefault(); actions.execute('app:notifications'); return; }
      if (e.key === 'F2') { e.preventDefault(); cust._toggle(); return; }
      if (e.key === 'F5') { e.preventDefault(); this._switchSection('montagens'); return; }
      if (e.key === 'F9') { e.preventDefault(); actions.execute('payment:open'); return; }
      if (e.key === 'F10') { e.preventDefault(); actions.execute('session:suspend'); return; }
      if (e.key === 'F11') { e.preventDefault(); actions.execute('session:recover'); return; }
      if (e.key === 'F12') { e.preventDefault(); actions.execute('app:finalizar'); return; }
      if (e.key === 'Escape') {
        if (document.querySelector('.overlay.show')) {
          document.querySelectorAll('.overlay.show').forEach(o => o.classList.remove('show'));
          return;
        }
      }
      if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
        actions.execute('app:shortcuts');
      }
    });
  }

  _initFrete() {
    const FRETE_OPTS = [
      { label: 'Balcão', dest: 'balcao', val: 0 },
      { label: 'Bairro', dest: 'bairro', val: 5 },
      { label: 'Centro', dest: 'centro', val: 8 },
      { label: 'Cidade', dest: 'cidade', val: 12 },
      { label: 'Região', dest: 'regiao', val: 20 },
      { label: 'Fora Estado', dest: 'fora_estado', val: 35 },
    ];
    window.FRETE_OPTS = FRETE_OPTS;
    state.update({ frete: FRETE_OPTS[0] });
  }

  _renderFrete() {
    const el = document.getElementById('freteBar');
    if (!el) return;
    const frete = state.get('frete');
    el.innerHTML = '<span class="fr-label">🚚 Destino</span>' +
      FRETE_OPTS.map(f =>
        `<button class="${f.dest === frete.dest ? 'sel' : ''}" onclick="state.update({frete:FRETE_OPTS.find(x=>x.dest==='${f.dest}')})">${f.label}${f.val > 0 ? ' R$'+f.val : ''}</button>`
      ).join('');
  }

  _switchSection(section) {
    this.sections = Object.keys(this.sections).reduce((a, k) => { a[k] = k === section; return a; }, {});
    document.querySelectorAll('.section').forEach(el => {
      el.classList.toggle('active', el.id === 'section' + section.charAt(0).toUpperCase() + section.slice(1));
    });
  }

  switchRightTab(tab) {
    this.rightTab = tab;
    document.querySelectorAll('.panel-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
    document.querySelectorAll('.panel-body').forEach(b => b.classList.toggle('active', b.id === tab + 'Panel' || b.id === 'custPanel' && tab === 'customer'));
  }

  _updateActionPanel(d) {
    const el = document.getElementById('actionPanel');
    if (!el) return;
    const cart = state.get('cart');
    const idx = d?.idx ?? state.get('selIdx');
    if (idx < 0 || idx >= cart.length) {
      el.innerHTML = '';
      return;
    }
    const item = cart[idx];
    el.innerHTML = `
      <button onclick="bus.emit('numpad:enter',{mode:'quantity',opts:{label:'${item.name}',callback:v=>{cartModule.updateQty(${idx},parseInt(v)||1)}}})">Qtd</button>
      <button onclick="bus.emit('numpad:enter',{mode:'discount_pct',opts:{label:'${item.name}',callback:v=>{cartModule.applyDiscount(${idx},'pct',parseInt(v))}}})">% Desc</button>
      <button onclick="bus.emit('numpad:enter',{mode:'discount_val',opts:{label:'${item.name}',callback:v=>{cartModule.applyDiscount(${idx},'val',parseFloat(v))}}})">R$ Desc</button>
      <button class="prim" onclick="bus.emit('cart:remove',{idx:${idx}})">✕ Remover</button>
    `;
  }

  finalizar() {
    const cart = state.get('cart');
    if (!cart.length) { notifs.warn('Carrinho vazio'); return; }
    const op = state.get('operation') || 'sale';
    if (op === 'sale') { actions.execute('payment:open'); }
    else if (op === 'order') { bus.emit('pedido:create'); }
    else if (op === 'quotation') { bus.emit('cotacao:create', {}); }
  }

  toggleShortcuts() {
    document.getElementById('shortcutsOverlay').classList.toggle('show');
  }

  _renderShortcuts() {
    const el = document.getElementById('shortcutsPanel');
    if (!el) return;
    const all = actions.list({ visibleOnly: true }).filter(a => a.shortcut);
    el.innerHTML = all.map(a =>
      `<kbd><span class="key">${a.shortcut}</span> ${a.label}</kbd>`
    ).join('');
  }

  async logout() {
    const token = localStorage.getItem('becrp_token');
    if (token) {
      try {
        await fetch('http://'+location.hostname+':8000/api/auth/logout', {
          method: 'POST',
          headers: { 'X-Auth-Token': token }
        });
      } catch (e) {}
    }
    localStorage.removeItem('becrp_token');
    localStorage.removeItem('becrp_user');
    window.location.href = 'login.html';
  }

  _loadInitialData() {
    const userData = JSON.parse(localStorage.getItem('becrp_user') || '{}');
    const el = document.getElementById('userDisplay');
    if (el && userData.nome) el.textContent = '👋 ' + userData.nome;
    bus.emit('session:new');
    setTimeout(() => {
      notifs.info('✦ BECRP pronto — ' + (userData.nome || 'POS'));
    }, 500);
  }
};

window.app = new App();
