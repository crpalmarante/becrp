window.PaymentModule = class PaymentModule {
  constructor() {
    this.overlay = document.getElementById('payOverlay');
    this.totalEl = document.getElementById('payTotal');
    this.amountEl = document.getElementById('payAmount');
    this.changeEl = document.getElementById('payChange');
    this.changeRow = document.getElementById('payChangeRow');
    this._pendingCb = null;
    this._method = 'dinheiro';
    this._init();
  }
  _init() {
    bus.on('payment:open', d => this.open(d));
    bus.on('payment:close', () => this.close());
    actions.register('payment:open', { label: 'Receber', context: 'cart', shortcut: 'F9', handler: () => this.open() });
    actions.register('payment:dinheiro', { label: 'Dinheiro', context: 'payment', group: 'pay-method', handler: () => this._setMethod('dinheiro') });
    actions.register('payment:credito', { label: 'Crédito', context: 'payment', group: 'pay-method', handler: () => this._setMethod('credito') });
    actions.register('payment:debito', { label: 'Débito', context: 'payment', group: 'pay-method', handler: () => this._setMethod('debito') });
    actions.register('payment:pix', { label: 'PIX', context: 'payment', group: 'pay-method', handler: () => this._setMethod('pix') });
    if (this.amountEl) {
      this.amountEl.addEventListener('input', () => this._calcChange());
      this.amountEl.addEventListener('keydown', e => { if (e.key === 'Enter') this.confirm(); });
    }
  }
  open(opts) {
    const cart = state.get('cart');
    if (!cart.length && !opts?.total) { notifs.warn('Carrinho vazio'); return; }
    this._pendingCb = opts?.callback || null;
    const total = opts?.total || cartModule.getTotal().total;
    if (this.totalEl) this.totalEl.textContent = 'R$ ' + total.toFixed(2);
    if (this.amountEl) { this.amountEl.value = total.toFixed(2).replace('.', ','); this.amountEl.readOnly = false; }
    if (this.changeRow) this.changeRow.style.display = 'none';
    this._method = 'dinheiro';
    this.overlay?.classList.add('show');
    setTimeout(() => this.amountEl?.focus(), 100);
    this._renderMethods();
  }
  close() {
    this.overlay?.classList.remove('show');
    this._pendingCb = null;
  }
  _setMethod(m) {
    this._method = m;
    this._renderMethods();
    if (m !== 'dinheiro' && this.amountEl) {
      this.amountEl.readOnly = true;
      this.amountEl.value = this.totalEl?.textContent.replace('R$ ', '').replace(',', '.') || '0';
    } else if (this.amountEl) {
      this.amountEl.readOnly = false;
      this.amountEl.focus();
    }
    this._calcChange();
  }
  _calcChange() {
    const t = parseFloat((this.totalEl?.textContent || '0').replace('R$ ', '').replace(',', '.'));
    const p = parseFloat((this.amountEl?.value || '0').replace(',', '.').replace('.', ''));
    if (isNaN(p) || p <= t) { if (this.changeRow) this.changeRow.style.display = 'none'; return; }
    if (this.changeEl) this.changeEl.textContent = 'R$ ' + (p - t).toFixed(2);
    if (this.changeRow) this.changeRow.style.display = 'flex';
  }
  confirm() {
    const t = parseFloat((this.totalEl?.textContent || '0').replace('R$ ', '').replace(',', '.'));
    const p = parseFloat((this.amountEl?.value || '0').replace(',', '.').replace('.', ''));
    if (isNaN(p) || p < t) { notifs.err('Valor insuficiente'); return; }
    const troco = p - t;
    if (this._pendingCb) {
      this._pendingCb({ total: t, recebido: p, troco, method: this._method });
    }
    this.close();
    notifs.ok(`Venda finalizada! R$ ${t.toFixed(2)}${troco > 0 ? ' | Troco: R$ '+troco.toFixed(2) : ''} | ${this._method.toUpperCase()}`);
    bus.emit('payment:confirmed', { total: t, method: this._method, troco });
    bus.emit('timeline:add', { action: 'Pagamento confirmado', detail: `R$ ${t.toFixed(2)} ${this._method}` });
    bus.emit('session:new');
  }
  _renderMethods() {
    const el = document.getElementById('payMethods');
    if (!el) return;
    const methods = [
      { id: 'dinheiro', label: '💵 Dinheiro' },
      { id: 'credito', label: '💳 Crédito' },
      { id: 'debito', label: '💳 Débito' },
      { id: 'pix', label: '📱 PIX' },
    ];
    el.innerHTML = methods.map(m =>
      `<button class="${m.id === this._method ? 'sel' : ''}" onclick="pay._setMethod('${m.id}')">${m.label}</button>`
    ).join('');
  }
};

window.pay = null;
