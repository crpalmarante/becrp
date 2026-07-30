window.PedidosModule = class PedidosModule {
  constructor() {
    this.pedidos = [];
    this.panel = document.getElementById('pedidosPanel');
    this._init();
  }
  _init() {
    bus.on('pedido:create', d => this._create(d));
    bus.on('pedido:remove', d => this._remove(d.id));
    bus.on('pedido:separate', d => this._separate(d.idx));
    bus.on('pedido:list', () => this._render());
    actions.register('pedido:create', { label: 'Criar Pedido', context: 'cart', handler: () => this._openCreate() });
  }
  _openCreate() {
    const cart = state.get('cart');
    if (!cart.length) { notifs.warn('Carrinho vazio'); return; }
    bus.emit('overlay:open', { id: 'pedidoOverlay' });
  }
  _create(data) {
    const id = 'PED-' + String(this.pedidos.length + 1).padStart(4, '0');
    const pedido = {
      id, atendimento: 'AT-' + String(state.get('atendimentoId')).padStart(6, '0'),
      cliente: state.get('customer').name, itens: [...state.get('cart')],
      total: cartModule.getTotal().total, status: 'pendente',
      data: new Date().toLocaleDateString('pt-BR'),
      entrega: data.entrega || null, separado: false
    };
    this.pedidos.push(pedido);
    notifs.ok(id + ' — Pedido gerado! R$ ' + pedido.total.toFixed(2));
    bus.emit('timeline:add', { action: 'Pedido criado', detail: id });
    if (data.requireMontagem) {
      bus.emit('montagem:create-from-pedido', { pedidoId: id, entrega: data.entrega });
    }
    this._render();
    bus.emit('session:new');
  }
  _remove(id) {
    this.pedidos = this.pedidos.filter(p => p.id !== id);
    this._render();
  }
  _separate(idx) {
    if (idx >= 0 && idx < this.pedidos.length) {
      this.pedidos[idx].separado = true;
      this._render();
      notifs.ok('Pedido enviado para separação');
    }
  }
  _render() {
    const el = document.getElementById('pedidosBody');
    if (!el) return;
    if (!this.pedidos.length) { el.innerHTML = '<div class="empty">Nenhum pedido</div>'; return; }
    el.innerHTML = this.pedidos.map((p, i) =>
      `<div class="list-item">
        <div class="li-head"><strong>${p.id}</strong> <span class="st ${p.separado ? 'ok' : 'warn'}">${p.separado ? 'Separado' : 'Pendente'}</span></div>
        <div class="li-body">${p.cliente} — R$ ${p.total.toFixed(2)}</div>
        <div class="li-foot">${p.data}${p.entrega ? ' | '+p.entrega.tipo : ''}</div>
        <div class="li-actions">
          ${!p.separado ? `<button onclick="pedidos._separate(${i})">Separar</button>` : ''}
          <button onclick="pedidos._remove('${p.id}')">Remover</button>
        </div>
      </div>`
    ).join('');
    this._updateBadge();
  }
  _updateBadge() {
    const el = document.getElementById('pedidosBadge');
    if (el) el.textContent = this.pedidos.filter(p => p.status === 'pendente' && !p.separado).length || '';
  }
};

window.pedidos = null;
