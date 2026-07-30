/*=========================================================
  EntityQuickModal + EntityLookup.bind
  Context Preservation — criar/editar sem sair da tela
=========================================================*/
(function (global) {
  let modalEl = null;
  let state = {
    editingId: null,
    onSave: null,
    titleNew: "Novo",
    titleEdit: "Editar",
  };

  function ensureDom() {
    if (modalEl) return modalEl;
    modalEl = document.createElement("div");
    modalEl.id = "entity-quick-modal";
    modalEl.className = "lookup-cest-dialog";
    modalEl.hidden = true;
    modalEl.innerHTML = `
      <div class="lookup-cest-panel" role="dialog" aria-modal="true" aria-labelledby="eqm-title">
        <h3 id="eqm-title">Novo</h3>
        <p id="eqm-help">O formulário permanece aberto — após salvar, o campo já fica preenchido.</p>
        <div class="field" style="margin-bottom:10px">
          <label for="eqm-nome">Nome</label>
          <input class="form-input" id="eqm-nome" placeholder="Nome">
        </div>
        <div class="field" style="margin-bottom:10px" id="eqm-desc-wrap">
          <label for="eqm-descricao">Descrição</label>
          <textarea class="form-input" id="eqm-descricao" rows="3" placeholder="Opcional"></textarea>
        </div>
        <div class="form-error" id="eqm-error"></div>
        <div class="lookup-cest-actions">
          <button type="button" class="so-btn ghost" id="eqm-cancel">Cancelar</button>
          <button type="button" class="so-btn primary" id="eqm-save">Salvar</button>
        </div>
      </div>`;
    document.body.appendChild(modalEl);
    document.getElementById("eqm-cancel").addEventListener("click", close);
    document.getElementById("eqm-save").addEventListener("click", save);
    modalEl.addEventListener("click", (e) => {
      if (e.target === modalEl) close();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && modalEl && !modalEl.hidden) close();
    });
    return modalEl;
  }

  function close() {
    if (!modalEl) return;
    modalEl.hidden = true;
    const err = document.getElementById("eqm-error");
    if (err) err.classList.remove("visible");
    state.editingId = null;
    state.onSave = null;
  }

  function open(opts) {
    ensureDom();
    state.editingId = opts.item && opts.item.id != null ? opts.item.id : null;
    state.onSave = opts.onSave || null;
    state.titleNew = opts.titleNew || ("Nova " + (opts.entityLabel || "entidade"));
    state.titleEdit = opts.titleEdit || ("Editar " + (opts.entityLabel || "entidade"));
    document.getElementById("eqm-title").textContent = state.editingId
      ? state.titleEdit
      : state.titleNew;
    document.getElementById("eqm-help").textContent =
      opts.help ||
      "O formulário permanece aberto — após salvar, o campo já fica preenchido.";
    document.getElementById("eqm-nome").value =
      (opts.item && (opts.item.nome || opts.item.label)) || opts.presetNome || "";
    document.getElementById("eqm-descricao").value =
      (opts.item && opts.item.descricao) || "";
    document.getElementById("eqm-desc-wrap").hidden = !!opts.hideDescricao;
    document.getElementById("eqm-error").classList.remove("visible");
    modalEl.hidden = false;
    setTimeout(() => document.getElementById("eqm-nome").focus(), 40);
  }

  async function save() {
    const err = document.getElementById("eqm-error");
    err.classList.remove("visible");
    const nome = document.getElementById("eqm-nome").value.trim();
    const descricao = document.getElementById("eqm-descricao").value.trim();
    if (!nome) {
      err.textContent = "Nome é obrigatório";
      err.classList.add("visible");
      return;
    }
    if (!state.onSave) {
      close();
      return;
    }
    try {
      const item = await state.onSave({
        id: state.editingId,
        nome,
        descricao,
        isEdit: !!state.editingId,
      });
      close();
      return item;
    } catch (e) {
      err.textContent = (e && e.message) || "Erro ao salvar";
      err.classList.add("visible");
    }
  }

  /**
   * Liga um input Lookup com create/edit em modal (context preservation).
   * @returns {Lookup}
   */
  function bind(selector, options) {
    const provider = options.provider;
    const entityLabel = options.entityLabel || "item";
    const lookup = new Lookup(selector, {
      provider,
      minChars: options.minChars ?? 1,
      debounce: options.debounce ?? 220,
      valueKey: options.valueKey || "nome",
      showCode: options.showCode === true,
      placeholder: options.placeholder || "Digite para pesquisar ou criar",
      emptyLabel: options.emptyLabel || ("Nenhum(a) " + entityLabel.toLowerCase() + " encontrado(a)"),
      createLabel: options.createLabel || ("Criar Nov" + (options.gender === "a" ? "a " : "o ") + entityLabel),
      actions: { search: true, create: true, edit: options.edit !== false },
      onSelect: options.onSelect || null,
      onClear: options.onClear || null,
      onCreate: (q) =>
        open({
          entityLabel,
          titleNew: options.titleNew,
          titleEdit: options.titleEdit,
          presetNome: q,
          hideDescricao: options.hideDescricao,
          onSave: async (payload) => {
            const data = await provider.create({
              nome: payload.nome,
              descricao: payload.descricao,
            });
            if (data.status !== "ok") throw new Error(data.message || "Erro ao criar");
            const item = {
              id: data.id,
              codigo: data.id,
              nome: payload.nome,
              descricao: payload.descricao || "",
              label: payload.nome,
            };
            lookup.setValue(item);
            if (options.onCreated) options.onCreated(item);
            return item;
          },
        }),
      onEdit: (item) =>
        open({
          entityLabel,
          titleNew: options.titleNew,
          titleEdit: options.titleEdit,
          item,
          hideDescricao: options.hideDescricao,
          onSave: async (payload) => {
            const data = await provider.update(payload.id, {
              nome: payload.nome,
              descricao: payload.descricao,
              ...(item || {}),
            });
            if (data.status !== "ok") throw new Error(data.message || "Erro ao atualizar");
            const next = {
              id: payload.id,
              codigo: payload.id,
              nome: payload.nome,
              descricao: payload.descricao || "",
              label: payload.nome,
            };
            lookup.setValue(next);
            if (options.onUpdated) options.onUpdated(next);
            return next;
          },
        }),
    });
    return lookup;
  }

  global.EntityQuickModal = { open, close, bind };
})(window);
