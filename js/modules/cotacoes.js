window.CotacoesModule = class CotacoesModule {
  constructor() {
    this.orcamentos = [];
    this.panel = document.getElementById('cotacoesPanel');
    this._init();
  }
  _init() {
    bus.on('cotacao:create', d => this._create(d));
    bus.on('cotacao:convert', d => this._convert(d.id));
    bus.on('cotacao:remove', d => this._remove(d.id));
    bus.on('cotacao:list', () => this._render());
  }
  _create(data) {
    const id = 'COT-' + String(this.orcamentos.length + 1).padStart(4, '0');
    const cot = {
      id, atendimento: 'AT-' + String(state.get('atendimentoId')).padStart(6, '0'),
      cliente: state.get('customer').name, itens: [...state.get('cart')],
      total: cartModule.getTotal().total, status: 'pendente',
      data: new Date().toLocaleDateString('pt-BR'),
      validade: new Date(Date.now() + 15 * 86400000).toLocaleDateString('pt-BR')
    };
    this.orcamentos.push(cot);
    notifs.ok(id + ' — Cotação gerada!');
    bus.emit('timeline:add', { action: 'Cotação criada', detail: id });
    this._render();
    bus.emit('session:new');
  }
  _convert(id) {
    const cot = this.orcamentos.find(o => o.id === id);
    if (!cot) return;
    cot.status = 'convertido';
    state.update({ cart: [...cot.itens] });
    this._render();
    notifs.info('Cotação ' + id + ' convertida para venda');
    bus.emit('section:switch', 'atendimento');
    bus.emit('cart:render');
  }
  _remove(id) {
    this.orcamentos = this.orcamentos.filter(o => o.id !== id);
    this._render();
  }
  _render() {
    const el = document.getElementById('cotacoesBody');
    if (!el) return;
    if (!this.orcamentos.length) { el.innerHTML = '<div class="empty">Nenhuma cotação</div>'; return; }
    el.innerHTML = this.orcamentos.map((o, i) =>
      `<div class="list-item">
        <div class="li-head"><strong>${o.id}</strong> <span class="st ${o.status === 'convertido' ? 'ok' : ''}">${o.status}</span></div>
        <div class="li-body">${o.cliente} — R$ ${o.total.toFixed(2)}</div>
        <div class="li-foot">${o.data} | Validade: ${o.validade}</div>
        <div class="li-actions">
          ${o.status !== 'convertido' ? `<button onclick="cotacoes._convert('${o.id}')">Converter</button>` : ''}
          <button onclick="cotacoes._remove('${o.id}')">Remover</button>
        </div>
      </div>`
    ).join('');
    this._updateBadge();
  }
  _updateBadge() {
    const el = document.getElementById('cotacoesBadge');
    if (el) el.textContent = this.orcamentos.filter(o => o.status === 'pendente').length || '';
  }
};

window.cotacoes = null;
