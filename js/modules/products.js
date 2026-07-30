window.ProductsModule = class ProductsModule {
  constructor() {
    this.products = [];
    this.filtered = [];
    this.categories = {};
    this.favorites = JSON.parse(localStorage.getItem('pos_favorites') || '[]');
    this.searchEl = document.getElementById('prodSearch');
    this.gridEl = document.getElementById('prodGrid');
    this.catEl = document.getElementById('catPanel');
    this.panel = document.getElementById('leftPanel');
    this.catPath = [];
    this.selectedCat = '';
    this.view = 'grid';
    this._init();
  }
  async _init() {
    await this._load();
    this._renderCategories();
    this._renderGrid();
    if (this.searchEl) {
      this.searchEl.addEventListener('input', () => this._onSearch());
      this.searchEl.addEventListener('keydown', e => {
        if (e.key === 'ArrowDown') { e.preventDefault(); this._navGrid(1); }
        if (e.key === 'ArrowUp') { e.preventDefault(); this._navGrid(-1); }
        if (e.key === 'Enter') {
          e.preventDefault();
          if (this.filtered.length) this._selectProduct(0);
        }
      });
    }
    bus.on('product:search', q => { if (this.searchEl) { this.searchEl.value = q; this._onSearch(); } });
    bus.on('product:add-favorite', id => this._toggleFav(id));
    actions.register('product:add', { label: 'Adicionar ao Atendimento', context: 'product', when: () => true, handler: ctx => this._addSingle(ctx.product) });
    actions.register('product:fav', { label: 'Favoritar', context: 'product', handler: ctx => this._toggleFav(ctx.product.code) });
  }
  async _load() {
    try {
      const r = await fetch('http://' + location.hostname + ':8012/api/produtos');
      const d = await r.json();
      this.products = d.data || [];
    } catch (e) {
      this.products = this._defaultProducts();
    }
    this.filtered = [...this.products];
    this._buildCategories();
  }
  _defaultProducts() {
    return [
      { code: '7891000315518', name: 'Coca-Cola 2L', price: 12.50, catPath: ['Bebidas', 'Refrigerantes', 'Cola'] },
      { code: '7891000315718', name: 'Geladeira Brastemp 380L', price: 3899.00, catPath: ['Eletro', 'Refrigeração', 'Geladeira'] },
      { code: '7891000315732', name: 'Fogão Brastemp 5 Bocas', price: 2199.00, catPath: ['Eletro', 'Cozinha', 'Fogão'] },
      { code: '7891000315749', name: 'Micro-ondas Panasonic 32L', price: 899.00, catPath: ['Eletro', 'Cozinha', 'Micro-ondas'] },
      { code: 'FAKE-SOFA-001', name: 'Sofá Itália 3 Lugares', price: 3490.00, catPath: ['Móveis', 'Sala', 'Sofás'] },
      { code: 'FAKE-SOFA-002', name: 'Sofá Veneza 2 Lugares', price: 2890.00, catPath: ['Móveis', 'Sala', 'Sofás'] },
      { code: 'FAKE-BED-001', name: 'Cama Box Casal', price: 1890.00, catPath: ['Móveis', 'Quarto', 'Camas'] },
      { code: 'FAKE-BED-002', name: 'Guarda-Roupa Casal 6 Portas', price: 4290.00, catPath: ['Móveis', 'Quarto', 'Guarda-Roupas'] },
      { code: 'FAKE-TABLE-001', name: 'Mesa Jantar 6 Lugares', price: 1590.00, catPath: ['Móveis', 'Cozinha', 'Mesas'] },
      { code: 'FAKE-RACK-001', name: 'Rack TV 2m', price: 890.00, catPath: ['Móveis', 'Sala', 'Racks'] },
      { code: 'FAKE-PAINEL-001', name: 'Painel TV 3m', price: 1290.00, catPath: ['Móveis', 'Sala', 'Painéis'] },
      { code: 'FAKE-MATTRESS-001', name: 'Colchão King Size', price: 2490.00, catPath: ['Móveis', 'Quarto', 'Colchões'] },
    ];
  }
  _buildCategories() {
    this.categories = {};
    for (const p of this.products) {
      if (!p.catPath) continue;
      let node = this.categories;
      for (const seg of p.catPath) {
        if (!node[seg]) node[seg] = {};
        node = node[seg];
      }
    }
  }
  _renderCategories() {
    if (!this.catEl) return;
    let node = this.categories;
    let path = this.catPath;
    for (const seg of path) {
      node = node[seg] || {};
    }
    const keys = Object.keys(node);
    if (path.length) {
      this.catEl.innerHTML =
        `<div class="cat-back" onclick="prods._catUp()">‹ Voltar</div>` +
        keys.map(k => `<div class="cat-item" onclick="prods._catDrill('${k}')">${k}</div>`).join('') +
        `<div class="cat-all" onclick="prods._catSelect('${path[path.length-1]}')">→ Todos ${path[path.length-1]}</div>`;
    } else {
      this.catEl.innerHTML = keys.map(k => `<div class="cat-item" onclick="prods._catDrill('${k}')">${k}</div>`).join('');
    }
  }
  _catDrill(cat) {
    this.catPath.push(cat);
    this._renderCategories();
    this._onSearch();
  }
  _catUp() {
    this.catPath.pop();
    this._renderCategories();
    this._onSearch();
  }
  _catSelect(cat) {
    this.selectedCat = cat;
    this._onSearch();
  }
  _onSearch() {
    const q = (this.searchEl?.value || '').toLowerCase();
    const catPath = this.catPath;
    this.filtered = this.products.filter(p => {
      if (catPath.length) {
        for (let i = 0; i < catPath.length; i++) {
          if (!p.catPath || p.catPath[i] !== catPath[i]) return false;
        }
      }
      if (this.selectedCat && (!p.catPath || !p.catPath.includes(this.selectedCat))) return false;
      if (q && !p.name.toLowerCase().includes(q) && !p.code.toLowerCase().includes(q)) return false;
      return true;
    });
    this._renderGrid();
  }
  _renderGrid() {
    if (!this.gridEl) return;
    if (!this.filtered.length) {
      this.gridEl.innerHTML = '<div class="empty">Nenhum produto encontrado</div>';
      return;
    }
    this.gridEl.innerHTML = this.filtered.map((p, i) => {
      const isFav = this.favorites.includes(p.code);
      return `<div class="prod-card" onclick="prods._addSingle(${i})" data-idx="${i}">
        <div class="prod-img">${p.name.charAt(0)}</div>
        <div class="prod-name">${p.name}</div>
        <div class="prod-price">R$ ${p.price.toFixed(2)}</div>
        <div class="prod-fav ${isFav ? 'on' : ''}" onclick="event.stopPropagation();prods._toggleFav('${p.code}')">${isFav ? '★' : '☆'}</div>
      </div>`;
    }).join('');
  }
  _navGrid(dir) {
    const sel = this.gridEl?.querySelector('.prod-card.sel');
    let idx = sel ? parseInt(sel.dataset.idx) : -1;
    idx = Math.max(0, Math.min(this.filtered.length - 1, idx + dir));
    this.gridEl?.querySelectorAll('.prod-card').forEach(el => el.classList.remove('sel'));
    this.gridEl?.querySelector(`[data-idx="${idx}"]`)?.classList.add('sel');
    this.gridEl?.querySelector(`[data-idx="${idx}"]`)?.scrollIntoView({ block: 'nearest' });
  }
  _selectProduct(idx) {
    if (idx >= 0 && idx < this.filtered.length) this._addSingle(idx);
  }
  _addSingle(idx) {
    const p = this.filtered[idx];
    if (!p) return;
    bus.emit('cart:add', { code: p.code, name: p.name, price: p.price, catPath: p.catPath });
  }
  _toggleFav(code) {
    const i = this.favorites.indexOf(code);
    if (i >= 0) this.favorites.splice(i, 1);
    else this.favorites.push(code);
    localStorage.setItem('pos_favorites', JSON.stringify(this.favorites));
    this._renderGrid();
  }
  getFavorites() {
    return this.products.filter(p => this.favorites.includes(p.code));
  }
};

window.prods = null;
