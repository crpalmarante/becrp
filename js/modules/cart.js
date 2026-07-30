window.CartModule = class CartModule {
  constructor() {
    this.totalEl = document.getElementById('cartTotal');
    this.bodyEl = document.getElementById('cartBody');
    this.emptyEl = document.getElementById('cartEmpty');
    this.breakdownEl = document.getElementById('totalBreakdown');
    this.btnFinish = document.getElementById('btnFinish');
    this._init();
  }
  _init() {
    bus.on('cart:add', d => this.add(d));
    bus.on('cart:remove', d => this.remove(d.idx));
    bus.on('cart:qty', d => this.updateQty(d.idx, d.qty));
    bus.on('cart:discount', d => this.applyDiscount(d.idx, d.type, d.val));
    bus.on('cart:clear', () => this.clear());
    bus.on('state:cart:changed', () => this.render());
    actions.register('cart:add', { label: 'Adicionar Produto', context: 'cart', handler: () => document.getElementById('prodSearch')?.focus() });
    actions.register('cart:clear', { label: 'Limpar Carrinho', context: 'cart', handler: () => this.clear() });
    actions.register('cart:undo', { label: 'Desfazer', context: 'cart', shortcut: 'Ctrl+Z', handler: () => state.undo() });
  }
  add(p) {
    const cart = state.get('cart');
    const exist = cart.findIndex(c => c.code === p.code);
    if (exist >= 0) {
      cart[exist].qty += p.qty || 1;
      state.update({ cart: [...cart] });
    } else {
      const item = { code: p.code, name: p.name, price: p.price, qty: p.qty || 1, discType: null, discValue: 0, catPath: p.catPath || [] };
      state.update({ cart: [...cart, item] });
    }
    bus.emit('cart:item-added', { product: p });
    bus.emit('timeline:add', { action: 'Produto adicionado', detail: p.name });
  }
  remove(idx) {
    const cart = state.get('cart');
    if (idx < 0 || idx >= cart.length) return;
    const removed = cart[idx];
    cart.splice(idx, 1);
    state.update({ cart: [...cart], selIdx: Math.min(idx, cart.length - 1) });
    bus.emit('timeline:add', { action: 'Produto removido', detail: removed.name });
  }
  updateQty(idx, qty) {
    const cart = state.get('cart');
    if (idx < 0 || idx >= cart.length) return;
    if (qty <= 0) return this.remove(idx);
    cart[idx].qty = qty;
    state.update({ cart: [...cart] });
  }
  applyDiscount(idx, type, val) {
    const cart = state.get('cart');
    if (idx < 0 || idx >= cart.length) return;
    cart[idx].discType = type;
    cart[idx].discValue = val;
    state.update({ cart: [...cart] });
    bus.emit('timeline:add', { action: `Desconto ${type==='pct'?val+'%':'R$'+val}`, detail: cart[idx].name });
  }
  clear() {
    const count = state.get('cart').length;
    if (!count) return;
    state.update({ cart: [], selIdx: -1 });
    bus.emit('timeline:add', { action: 'Carrinho limpo', detail: count + ' itens' });
  }
  getTotal() {
    const cart = state.get('cart');
    const frete = state.get('frete');
    let sub = 0;
    for (const c of cart) {
      let t = c.price * c.qty;
      if (c.discType === 'pct') t -= t * (c.discValue / 100);
      if (c.discType === 'val') t -= c.discValue;
      sub += Math.max(0, t);
    }
    return { subtotal: sub, frete: frete.val || 0, total: sub + (frete.val || 0) };
  }
  render() {
    const cart = state.get('cart');
    if (this.emptyEl) this.emptyEl.style.display = cart.length ? 'none' : 'block';
    if (this.bodyEl) {
      if (!cart.length) { this.bodyEl.innerHTML = ''; }
      else {
        this.bodyEl.innerHTML = cart.map((c, i) => {
          const t = this._itemTotal(c);
          return `<div class="cart-item ${i === state.get('selIdx') ? 'sel' : ''}" onclick="state.update({selIdx:${i}});bus.emit('cart:select',{idx:${i}})">
            <div class="ci-info">
              <span class="ci-name">${c.name}</span>
              <span class="ci-price">R$ ${c.price.toFixed(2)} <span class="ci-qty">x${c.qty}</span></span>
              ${c.discValue ? `<span class="ci-disc">${c.discType === 'pct' ? c.discValue+'%' : 'R$'+c.discValue}</span>` : ''}
            </div>
            <div class="ci-total">R$ ${t.toFixed(2)}</div>
            <div class="ci-actions">
              <button onclick="event.stopPropagation();bus.emit('numpad:enter',{mode:'quantity',opts:{label:'${c.name}',callback:v=>{cartModule.updateQty(${i},parseInt(v)||1)}}})">Q</button>
              <button onclick="event.stopPropagation();bus.emit('numpad:enter',{mode:'discount_pct',opts:{label:'${c.name}',callback:v=>{cartModule.applyDiscount(${i},'pct',parseInt(v))}}})">%</button>
              <button class="rm" onclick="event.stopPropagation();bus.emit('cart:remove',{idx:${i}})">✕</button>
            </div>
          </div>`;
        }).join('');
      }
    }
    this._updateTotal();
  }
  _itemTotal(c) {
    let t = c.price * c.qty;
    if (c.discType === 'pct') t -= t * (c.discValue / 100);
    if (c.discType === 'val') t -= c.discValue;
    return Math.max(0, t);
  }
  _updateTotal() {
    const { subtotal, frete, total } = this.getTotal();
    if (this.totalEl) this.totalEl.textContent = 'R$ ' + total.toFixed(2);
    if (this.breakdownEl) {
      this.breakdownEl.innerHTML = `Sub: R$ ${subtotal.toFixed(2)}${frete ? ' | Frete: R$ '+frete.toFixed(2) : ''}`;
    }
    if (this.btnFinish) this.btnFinish.disabled = !state.get('cart').length;
  }
  getItems() { return state.get('cart'); }
  getItemTotal(c) { return this._itemTotal(c); }
};

window.cartModule = null;
