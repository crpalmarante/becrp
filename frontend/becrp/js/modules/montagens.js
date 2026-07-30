window.MontagensModule = class MontagensModule {
  constructor() {
    this.montagens = [];
    this.API = 'http://' + location.hostname + ':8013/api';
    this.panel = document.getElementById('montagensPanel');
    this._init();
  }
  _init() {
    bus.on('montagem:create-from-pedido', d => this._createFromPedido(d));
    bus.on('montagem:list', () => this._load());
    bus.on('montagem:update-status', d => this._updateStatus(d.id, d.status));
    bus.on('section:switch', section => { if (section === 'montagens') this._load(); });
    actions.register('montagem:list', { label: 'Ordens de Montagem', context: 'session', handler: () => bus.emit('section:switch', 'montagens') });
  }
  async _load() {
    try {
      const el = document.getElementById('montFilter');
      const statusFilter = el?.value || '';
      const r = await fetch(this.API + '/montagens' + (statusFilter ? '?status=' + encodeURIComponent(statusFilter) : ''));
      const d = await r.json();
      this.montagens = d.data || [];
    } catch (e) { this.montagens = []; }
    this._render();
  }
  async _createFromPedido(data) {
    const cart = state.get('cart');
    const payload = {
      pedido_id: data.pedidoId,
      cliente: state.get('customer').name,
      telefone: '',
      endereco: data.entrega?.endereco || '',
      data_entrega: data.entrega?.data || '',
      montador: '', auxiliar: '', observacoes: '',
      produtos: cart.map(p => ({ cod: p.code, nome: p.name, qtd: p.qty, local: '', observacao: '' }))
    };
    try {
      const r = await fetch(this.API + '/montagens', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const d = await r.json();
      if (d.status === 'ok') notifs.ok('🔧 Ordem de Montagem #' + d.id + ' criada');
      await this._load();
    } catch (e) { console.error(e); }
  }
  async _updateStatus(id, status) {
    try {
      await fetch(this.API + '/montagens/' + id + '/status', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      });
      notifs.ok('Status atualizado: ' + status);
      await this._load();
    } catch (e) { notifs.err('Erro ao atualizar status'); }
  }
  async _delete(id) {
    try {
      await fetch(this.API + '/montagens/' + id, { method: 'DELETE' });
      notifs.ok('Ordem de montagem excluída');
      await this._load();
    } catch (e) { notifs.err('Erro ao excluir'); }
  }
  _render() {
    const el = document.getElementById('montagensBody');
    if (!el) return;
    if (!this.montagens.length) { el.innerHTML = '<div class="empty">Nenhuma ordem de montagem</div>'; return; }
    const statusClass = { 'Novo': '', 'Agendado': 'warn', 'Equipe Designada': 'warn', 'Em Deslocamento': 'acc', 'Em Montagem': 'acc', 'Aguardando Peça': 'danger', 'Concluído': 'ok' };
    el.innerHTML = this.montagens.map(m =>
      `<div class="list-item">
        <div class="li-head"><strong>${m.id}</strong> <span class="st ${statusClass[m.status] || ''}">${m.status}</span></div>
        <div class="li-body">${m.cliente}</div>
        <div class="li-foot">Entrega: ${m.data_entrega || '—'}${m.montador ? ' | Montador: '+m.montador : ''}</div>
        <div class="li-actions">
          <button onclick="montagens._updateStatus('${m.id}','${MontagensModule._nextStatus(m.status)}')">➡️ ${MontagensModule._nextStatus(m.status)}</button>
          ${m.status !== 'Concluído' ? `<button onclick="montagens._updateStatus('${m.id}','Concluído')">✅ Concluir</button>` : ''}
          <button onclick="montagens._delete('${m.id}')">🗑️</button>
        </div>
      </div>`
    ).join('');
    this._updateBadge();
  }
  static _nextStatus(s) {
    const sts = ['Novo', 'Agendado', 'Equipe Designada', 'Em Deslocamento', 'Em Montagem', 'Aguardando Peça', 'Concluído'];
    const i = sts.indexOf(s);
    return i >= 0 && i < sts.length - 1 ? sts[i + 1] : s;
  }
  _updateBadge() {
    const el = document.getElementById('montagensBadge');
    if (el) el.textContent = this.montagens.filter(m => m.status !== 'Concluído').length || '';
  }
};

window.montagens = null;
