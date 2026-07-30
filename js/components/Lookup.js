/*=========================================================
  Lookup Component — RFC-LOOKUP-AUTOCOMPLETE-ENGINE
  + Context Preservation (criar/editar sem sair da tela)
=========================================================*/
class Lookup {
  constructor(input, options = {}) {
    this._input = typeof input === "string" ? document.querySelector(input) : input;
    this._provider = options.provider;
    this._minChars = options.minChars ?? 1;
    this._debounceMs = options.debounce ?? 300;
    this._placeholder = options.placeholder || "Digite código ou descrição...";
    this._onSelect = options.onSelect || null;
    this._onClear = options.onClear || null;
    this._onCreate = options.onCreate || null;
    this._onEdit = options.onEdit || null;
    this._valueKey = options.valueKey || "codigo";
    this._showCode = options.showCode !== false;
    this._createLabel = options.createLabel || "Criar novo";
    this._emptyLabel = options.emptyLabel || "Nenhum resultado";
    this._actions = {
      search: options.actions?.search !== false,
      create: !!(options.actions?.create || options.onCreate),
      edit: !!(options.actions?.edit || options.onEdit),
    };
    this._dropdown = null;
    this._items = [];
    this._selectedIndex = -1;
    this._value = null;
    this._timer = null;
    this._wrap = null;
    this._field = null;
    this._hint = null;
    this._lastQuery = "";
    this._init();
  }

  _init() {
    if (!this._input) return;
    this._input.setAttribute("autocomplete", "off");
    this._input.placeholder = this._input.placeholder || this._placeholder;

    this._wrap = document.createElement("div");
    this._wrap.className = "lookup-wrap";
    this._input.parentNode.insertBefore(this._wrap, this._input);

    this._field = document.createElement("div");
    this._field.className = "lookup-field";
    this._wrap.appendChild(this._field);
    this._field.appendChild(this._input);

    if (this._actions.search || this._actions.create || this._actions.edit) {
      const bar = document.createElement("div");
      bar.className = "lookup-actions";
      if (this._actions.search) {
        bar.appendChild(this._actionBtn("🔍", "Pesquisar", () => {
          const q = this._input.value.trim();
          if (q.length >= this._minChars) this._search(q);
          else this._input.focus();
        }));
      }
      if (this._actions.create) {
        bar.appendChild(this._actionBtn("➕", "Criar novo", () => this._openCreate()));
      }
      if (this._actions.edit) {
        bar.appendChild(this._actionBtn("✎", "Editar selecionado", () => this._openEdit()));
      }
      this._field.appendChild(bar);
      this._field.classList.add("has-actions");
    }

    this._hint = document.createElement("div");
    this._hint.className = "lookup-hint";
    this._wrap.appendChild(this._hint);

    this._input.addEventListener("input", () => this._onInput());
    this._input.addEventListener("keydown", (e) => this._onKey(e));
    this._input.addEventListener("blur", () => setTimeout(() => this._hide(), 180));
    this._input.addEventListener("focus", () => {
      if (this._items.length) this._show();
    });
  }

  _actionBtn(icon, title, fn) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "lookup-action-btn";
    b.title = title;
    b.setAttribute("aria-label", title);
    b.textContent = icon;
    b.addEventListener("mousedown", (e) => {
      e.preventDefault();
      fn();
    });
    return b;
  }

  _onInput() {
    const val = this._input.value.trim();
    this._value = null;
    this._setHint("");
    if (this._timer) clearTimeout(this._timer);
    if (val.length < this._minChars) {
      this._items = [];
      this._hide();
      if (!val && this._onClear) this._onClear();
      return;
    }
    this._timer = setTimeout(() => this._search(val), this._debounceMs);
  }

  async _search(val) {
    if (!this._provider || !this._provider.search) return;
    this._lastQuery = val;
    try {
      this._setHint("Pesquisando...");
      const items = await this._provider.search(val);
      this._items = items || [];
      this._selectedIndex = -1;
      if (this._items.length) {
        this._setHint(`${this._items.length} resultado(s)`);
        this._show();
      } else {
        this._setHint(this._emptyLabel);
        this._showEmpty();
      }
    } catch (e) {
      this._items = [];
      this._setHint("Erro na pesquisa");
      this._hide();
    }
  }

  _itemHtml(item, i) {
    const code = item.codigo || item.id || "";
    const desc = item.descricao || item.nome || item.label || "";
    if (this._showCode && code && code !== desc) {
      return `<div class="lookup-item autocomplete-item" data-index="${i}">
        <span class="lookup-code">${this._esc(code)}</span>
        <span class="lookup-desc">${this._esc(desc)}</span>
      </div>`;
    }
    return `<div class="lookup-item autocomplete-item lookup-item-simple" data-index="${i}">
      <span class="lookup-desc">${this._esc(item.label || desc)}</span>
    </div>`;
  }

  _bindItems() {
    this._dropdown.querySelectorAll(".lookup-item").forEach((el) => {
      el.addEventListener("mousedown", (e) => {
        e.preventDefault();
        this._select(parseInt(el.dataset.index, 10));
      });
    });
  }

  _show() {
    this._hide(false);
    this._dropdown = document.createElement("div");
    this._dropdown.className = "lookup-dropdown autocomplete-dropdown show";
    this._dropdown.innerHTML = this._items.map((item, i) => this._itemHtml(item, i)).join("");
    this._field.appendChild(this._dropdown);
    this._bindItems();
  }

  _showEmpty() {
    this._hide(false);
    this._dropdown = document.createElement("div");
    this._dropdown.className = "lookup-dropdown autocomplete-dropdown show lookup-empty";
    const q = this._esc(this._lastQuery || this._input.value.trim());
    let html = `<div class="lookup-empty-msg">${this._esc(this._emptyLabel)}${q ? `: “${q}”` : ""}</div>`;
    if (this._onCreate) {
      html += `<button type="button" class="lookup-create-cta">${this._esc(this._createLabel)}</button>`;
    }
    this._dropdown.innerHTML = html;
    this._field.appendChild(this._dropdown);
    const btn = this._dropdown.querySelector(".lookup-create-cta");
    if (btn) {
      btn.addEventListener("mousedown", (e) => {
        e.preventDefault();
        this._openCreate();
      });
    }
  }

  _hide(clearHint) {
    if (this._dropdown) {
      this._dropdown.remove();
      this._dropdown = null;
      this._selectedIndex = -1;
    }
    if (clearHint) this._setHint("");
  }

  _onKey(e) {
    if (!this._dropdown) {
      if (e.key === "ArrowDown" && this._input.value.trim().length >= this._minChars) {
        this._search(this._input.value.trim());
      }
      return;
    }
    const items = this._dropdown.querySelectorAll(".lookup-item");
    if (!items.length) {
      if (e.key === "Enter" && this._onCreate && !this._items.length) {
        e.preventDefault();
        this._openCreate();
      } else if (e.key === "Escape") {
        this._hide();
      }
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      this._selectedIndex = Math.min(this._selectedIndex + 1, items.length - 1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      this._selectedIndex = Math.max(this._selectedIndex - 1, 0);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (this._selectedIndex >= 0) this._select(this._selectedIndex);
    } else if (e.key === "Escape") {
      this._hide();
    } else if (e.key === "Tab" && this._selectedIndex >= 0) {
      this._select(this._selectedIndex);
    }
    items.forEach((el, i) => el.classList.toggle("active", i === this._selectedIndex));
    if (items[this._selectedIndex]) items[this._selectedIndex].scrollIntoView({ block: "nearest" });
  }

  _openCreate() {
    this._hide(false);
    if (this._onCreate) this._onCreate(this._input.value.trim() || this._lastQuery);
  }

  _openEdit() {
    const item = this._value;
    if (!item) {
      this._setHint("Selecione um item para editar");
      return;
    }
    if (this._onEdit) this._onEdit(item);
  }

  _select(index) {
    const item = this._items[index];
    if (!item) return;
    this._value = item;
    this._input.value = item[this._valueKey] || item.codigo || item.nome || "";
    this._setHint(item.descricao || item.label || "");
    this._hide(false);
    if (this._onSelect) this._onSelect(item);
  }

  setValue(itemOrCode, hint) {
    if (!itemOrCode) {
      this.clear();
      return;
    }
    if (typeof itemOrCode === "object") {
      this._value = itemOrCode;
      this._input.value = itemOrCode[this._valueKey] || itemOrCode.codigo || itemOrCode.nome || "";
      this._setHint(itemOrCode.descricao || itemOrCode.label || hint || "");
    } else {
      this._input.value = itemOrCode;
      this._setHint(hint || "");
    }
  }

  getValue() {
    return this._value;
  }

  getCode() {
    return (this._value && (this._value[this._valueKey] || this._value.codigo || this._value.nome)) || this._input.value.trim();
  }

  clear() {
    this._value = null;
    this._input.value = "";
    this._setHint("");
    this._items = [];
    this._hide();
    if (this._onClear) this._onClear();
  }

  onSelect(fn) {
    this._onSelect = fn;
    return this;
  }

  _setHint(text) {
    if (this._hint) this._hint.textContent = text || "";
  }

  _esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
}

window.Lookup = Lookup;
