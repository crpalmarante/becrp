/**
 * Hub Configurações — Gerais (default) + módulos na sidebar.
 * Plano: sprints/RFC-ORGANIZATION-ESTABLISHMENT.md · sprints/TODO.md
 */
(function () {
  "use strict";

  const STORAGE_KEY = "becrp_config_gerais";

  const MODULES = [
    { id: "pos", label: "POS", icon: "icon-cart", panel: "pos" },
    { id: "fiscal", label: "Fiscal", icon: "icon-file-text", panel: "fiscal" },
    { id: "contabilidade", label: "Contabilidade", icon: "icon-dollar", panel: "contabilidade" },
    { id: "folha", label: "Folha", icon: "icon-users", panel: "folha" },
  ];

  const DEFAULTS = {
    org: {
      nome: "BECRP",
      razao: "",
      email: "",
      telefone: "",
      modulos: { pos: true, fiscal: true, contabilidade: true, folha: true },
    },
    preferencias: {
      pais: "BR",
      idioma: "pt-BR",
      fuso: "America/Sao_Paulo",
      moeda: "BRL",
      tema: "dark",
      data: "dd/mm/aaaa",
    },
    seguranca: {
      timeout: 30,
      senhaMin: 8,
      tentativas: 5,
      trocaSenha: false,
      reauth: true,
    },
  };

  const TITLES = {
    gerais: "Gerais",
    pos: "POS",
    fiscal: "Fiscal",
    contabilidade: "Contabilidade",
    folha: "Folha",
  };

  function loadState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return structuredClone(DEFAULTS);
      return deepMerge(structuredClone(DEFAULTS), JSON.parse(raw));
    } catch {
      return structuredClone(DEFAULTS);
    }
  }

  function saveState(state) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function deepMerge(base, patch) {
    if (!patch || typeof patch !== "object") return base;
    for (const k of Object.keys(patch)) {
      if (
        patch[k] &&
        typeof patch[k] === "object" &&
        !Array.isArray(patch[k]) &&
        base[k] &&
        typeof base[k] === "object"
      ) {
        deepMerge(base[k], patch[k]);
      } else {
        base[k] = patch[k];
      }
    }
    return base;
  }

  function toast(msg) {
    const el = document.getElementById("cfg-toast");
    if (!el) return;
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.remove("show"), 2200);
  }

  function showPanel(id) {
    document.querySelectorAll(".cfg-panel").forEach((p) => {
      p.classList.toggle("active", p.dataset.panel === id);
    });
    document.querySelectorAll(".cfg-mod-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.panel === id);
    });
    const title = TITLES[id] || id;
    const crumb = document.getElementById("cfg-crumb");
    const h = document.getElementById("cfg-title");
    if (crumb) crumb.textContent = title;
    if (h) h.textContent = title;
    const url = new URL(location.href);
    url.searchParams.set("mod", id);
    history.replaceState(null, "", url);
    if (id === "pos") loadTerminais();
    if (id === "fiscal") loadFiscalPanel();
  }

  function renderModuleNav(state) {
    const nav = document.getElementById("cfg-mod-nav");
    if (!nav) return;
    nav.querySelectorAll("[data-dyn-mod]").forEach((n) => n.remove());

    const mods = state.org.modulos || {};
    MODULES.forEach((m) => {
      if (!mods[m.id]) return;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "cfg-mod-btn";
      btn.dataset.panel = m.panel;
      btn.dataset.dynMod = "1";
      btn.innerHTML =
        `<svg class="icon"><use href="../assets/images/icons.svg#${m.icon}"/></svg> ${m.label}`;
      btn.addEventListener("click", () => showPanel(m.panel));
      nav.appendChild(btn);
    });
  }

  function renderModuleToggles(state) {
    const box = document.getElementById("org-modulos");
    if (!box) return;
    box.innerHTML = "";
    MODULES.forEach((m) => {
      const on = !!(state.org.modulos && state.org.modulos[m.id]);
      const label = document.createElement("label");
      label.className = "form-switch";
      label.innerHTML =
        `<input type="checkbox" data-mod="${m.id}" ${on ? "checked" : ""}>` +
        `<span>${m.label}</span>`;
      box.appendChild(label);
    });
  }

  function fillForm(state) {
    const o = state.org;
    const p = state.preferencias;
    const s = state.seguranca;
    setVal("org-nome", o.nome);
    setVal("org-razao", o.razao);
    setVal("org-email", o.email);
    setVal("org-telefone", o.telefone);
    setVal("pref-pais", p.pais);
    setVal("pref-idioma", p.idioma);
    setVal("pref-fuso", p.fuso);
    setVal("pref-moeda", p.moeda);
    setVal("pref-tema", p.tema);
    setVal("pref-data", p.data);
    setVal("sec-timeout", s.timeout);
    setVal("sec-senha-min", s.senhaMin);
    setVal("sec-tentativas", s.tentativas);
    const troca = document.getElementById("sec-troca-senha");
    const reauth = document.getElementById("sec-reauth");
    if (troca) troca.checked = !!s.trocaSenha;
    if (reauth) reauth.checked = !!s.reauth;
    renderModuleToggles(state);
    const tema = p.tema || "dark";
    document.documentElement.setAttribute("data-theme", tema);
  }

  function setVal(id, v) {
    const el = document.getElementById(id);
    if (el) el.value = v == null ? "" : v;
  }

  function readForm() {
    const modulos = {};
    document.querySelectorAll("#org-modulos [data-mod]").forEach((cb) => {
      modulos[cb.dataset.mod] = cb.checked;
    });
    return {
      org: {
        nome: val("org-nome"),
        razao: val("org-razao"),
        email: val("org-email"),
        telefone: val("org-telefone"),
        modulos,
      },
      preferencias: {
        pais: val("pref-pais"),
        idioma: val("pref-idioma"),
        fuso: val("pref-fuso"),
        moeda: val("pref-moeda"),
        tema: val("pref-tema"),
        data: val("pref-data"),
      },
      seguranca: {
        timeout: num("sec-timeout", 30),
        senhaMin: num("sec-senha-min", 8),
        tentativas: num("sec-tentativas", 5),
        trocaSenha: !!document.getElementById("sec-troca-senha")?.checked,
        reauth: !!document.getElementById("sec-reauth")?.checked,
      },
    };
  }

  function val(id) {
    return (document.getElementById(id)?.value || "").trim();
  }

  function num(id, fallback) {
    const n = Number(document.getElementById(id)?.value);
    return Number.isFinite(n) ? n : fallback;
  }

  const TERM_LS = "becrp_pos_terminais";
  let cacheEstabs = [];
  let cacheUsers = [];
  let cacheTerminais = [];

  function authHeaders(json) {
    const token =
      localStorage.getItem("auth_token") ||
      localStorage.getItem("token") ||
      localStorage.getItem("becrp_token");
    const h = {};
    if (token) h["X-Auth-Token"] = token;
    if (json) h["Content-Type"] = "application/json";
    return h;
  }

  async function apiGet(url) {
    const r = await fetch(url, { headers: authHeaders() });
    if (!r.ok) throw new Error(String(r.status));
    return r.json();
  }

  async function apiPost(url, body) {
    const r = await fetch(url, {
      method: "POST",
      headers: authHeaders(true),
      body: JSON.stringify(body || {}),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.message || "Erro " + r.status);
    return data;
  }

  async function loadUsersList() {
    try {
      const data = await apiGet("/api/admin/users");
      cacheUsers = data.users || [];
      return cacheUsers;
    } catch {
      try {
        const r = await fetch("../data/users.json");
        if (r.ok) {
          const map = await r.json();
          cacheUsers = Object.keys(map).map((id) => ({
            id,
            nome: map[id].nome,
            usuario: map[id].usuario,
            role: map[id].role,
            ativo: map[id].ativo !== false,
          }));
          return cacheUsers;
        }
      } catch {
        /* ignore */
      }
    }
    cacheUsers = [];
    return cacheUsers;
  }

  async function loadEstabsList() {
    try {
      const data = await apiGet("/api/admin/empresas");
      cacheEstabs = data.empresas || [];
      return cacheEstabs;
    } catch {
      try {
        const r = await fetch("../data/empresas.json");
        if (r.ok) {
          const map = await r.json();
          cacheEstabs = Object.keys(map).map((id) => ({ id, ...map[id] }));
          return cacheEstabs;
        }
      } catch {
        /* ignore */
      }
    }
    cacheEstabs = [];
    return cacheEstabs;
  }

  function estabName(id) {
    const e = cacheEstabs.find((x) => x.id === id);
    return e ? e.nome : id || "—";
  }

  async function loadUsuariosResumo() {
    const countEl = document.getElementById("users-count");
    const labelEl = document.getElementById("users-count-label");
    await loadUsersList();
    const n = cacheUsers.filter((u) => u.ativo !== false).length;
    if (countEl) countEl.textContent = String(n || 0);
    if (labelEl) {
      labelEl.textContent = n === 1 ? "usuário ativo" : "usuários ativos";
    }
  }

  async function loadEstabelecimentos() {
    const cards = document.getElementById("estabs-cards");
    const countEl = document.getElementById("estabs-count");
    if (!cards) return;
    await loadEstabsList();
    const lista = cacheEstabs;
    if (countEl) countEl.textContent = String(lista.length);
    if (!lista.length) {
      cards.innerHTML =
        '<p class="form-help">Nenhum estabelecimento. Use Gerir estabelecimentos.</p>';
      return;
    }
    cards.innerHTML = lista
      .map((e) => {
        const nome = e.nome || e.id || "—";
        const initials =
          String(nome)
            .split(/\s+/)
            .slice(0, 2)
            .map((w) => w[0] || "")
            .join("")
            .toUpperCase() || "?";
        const linha2 = [e.cidade, e.uf].filter(Boolean).join(" / ") || "—";
        const ativo = e.ativo !== false;
        return (
          `<article class="cfg-company-card">` +
          `<div class="cfg-company-avatar" aria-hidden="true">${esc(initials)}</div>` +
          `<div class="cfg-company-body">` +
          `<p class="cfg-company-name">${esc(nome)}` +
          (ativo ? "" : ' <span class="cfg-badge off">Inativo</span>') +
          `</p>` +
          `<p class="cfg-company-meta">${esc(linha2)}<br>CNPJ ${esc(e.cnpj || "—")}` +
          (e.ie ? `<br>IE ${esc(e.ie)}` : "") +
          `</p>` +
          `</div></article>`
        );
      })
      .join("");
  }

  function loadTerminaisLocal() {
    try {
      const raw = localStorage.getItem(TERM_LS);
      if (!raw) return null;
      const data = JSON.parse(raw);
      return Array.isArray(data) ? data : null;
    } catch {
      return null;
    }
  }

  function saveTerminaisLocal(list) {
    localStorage.setItem(TERM_LS, JSON.stringify(list));
  }

  async function loadTerminais() {
    const tbody = document.getElementById("terminais-tbody");
    if (!tbody) return;
    await loadEstabsList();
    await loadUsersList();
    let lista = [];
    try {
      const data = await apiGet("/api/admin/pos/terminais");
      lista = data.terminais || [];
    } catch {
      lista = loadTerminaisLocal();
      if (!lista) {
        try {
          const r = await fetch("../data/pos_terminais.json");
          if (r.ok) {
            const data = await r.json();
            lista = data.terminais || [];
          }
        } catch {
          lista = [];
        }
      }
    }
    cacheTerminais = lista;
    renderTerminaisTable();
  }

  function renderTerminaisTable() {
    const tbody = document.getElementById("terminais-tbody");
    if (!tbody) return;
    if (!cacheTerminais.length) {
      tbody.innerHTML =
        '<tr><td colspan="7">Nenhum terminal. Clique em + Novo terminal.</td></tr>';
      return;
    }
    tbody.innerHTML = cacheTerminais
      .map((t) => {
        const ativo = t.ativo !== false;
        return (
          `<tr>` +
          `<td>${esc(t.codigo || "—")}</td>` +
          `<td>${t.tipo === "caixa" ? "Caixa" : "PDV"}</td>` +
          `<td>${esc(t.nome || "—")}</td>` +
          `<td>${esc(estabName(t.estabelecimento_id))}</td>` +
          `<td>${esc(t.usuario_nome || t.usuario_id || "—")}</td>` +
          `<td><span class="cfg-badge ${ativo ? "on" : "off"}">${ativo ? "Ativo" : "Inativo"}</span></td>` +
          `<td><div class="cfg-actions-inline">` +
          `<button type="button" class="btn btn-secondary" data-term-edit="${esc(t.id)}">Editar</button>` +
          `<button type="button" class="btn btn-secondary" data-term-toggle="${esc(t.id)}">${ativo ? "Desativar" : "Ativar"}</button>` +
          `</div></td>` +
          `</tr>`
        );
      })
      .join("");

    tbody.querySelectorAll("[data-term-edit]").forEach((btn) => {
      btn.addEventListener("click", () => openTerminalModal(btn.dataset.termEdit));
    });
    tbody.querySelectorAll("[data-term-toggle]").forEach((btn) => {
      btn.addEventListener("click", () => toggleTerminal(btn.dataset.termToggle));
    });
  }

  function fillSelect(el, options, emptyLabel) {
    if (!el) return;
    el.innerHTML =
      (emptyLabel ? `<option value="">${emptyLabel}</option>` : "") +
      options
        .map((o) => `<option value="${esc(o.value)}">${esc(o.label)}</option>`)
        .join("");
  }

  function syncTipoFields() {
    const tipo = document.getElementById("term-tipo")?.value;
    const balWrap = document.getElementById("term-balanca-wrap");
    const nfceWrap = document.getElementById("term-nfce-wrap");
    const help = document.getElementById("term-usuario-help");
    if (balWrap) balWrap.style.display = tipo === "pdv" ? "" : "none";
    if (nfceWrap) nfceWrap.style.display = tipo === "caixa" ? "" : "none";
    if (help) {
      help.textContent =
        tipo === "pdv"
          ? "PDV: um vendedor por terminal (relação 1:1)."
          : "Caixa: gerente ou caixa — visão de todos os PDVs/Caixas do estabelecimento.";
    }
    const users = cacheUsers.filter((u) => {
      if (u.ativo === false) return false;
      const role = (u.role || "").toLowerCase();
      if (tipo === "pdv") return role === "vendedor" || role === "operador" || role === "admin";
      return role === "caixa" || role === "gerente" || role === "admin";
    });
    fillSelect(
      document.getElementById("term-usuario"),
      users.map((u) => ({
        value: u.id,
        label: `${u.nome || u.usuario} (${u.role || "—"})`,
      })),
      "Selecione…"
    );
  }

  async function openTerminalModal(editId) {
    await loadEstabsList();
    await loadUsersList();
    fillSelect(
      document.getElementById("term-estab"),
      cacheEstabs
        .filter((e) => e.ativo !== false)
        .map((e) => ({ value: e.id, label: e.nome || e.id })),
      "Selecione…"
    );
    const modal = document.getElementById("terminal-modal");
    const title = document.getElementById("terminal-modal-title");
    const form = document.getElementById("form-terminal");
    form?.reset();
    document.getElementById("term-id").value = editId || "";
    document.getElementById("term-treino").checked = true;
    document.getElementById("term-ativo").checked = true;
    document.getElementById("term-timeout").value = "30";
    document.getElementById("term-balanca").value = "mock";
    document.getElementById("term-nfce").checked = false;
    document.getElementById("term-codigo").disabled = !!editId;

    if (editId) {
      const t = cacheTerminais.find((x) => x.id === editId);
      if (!t) return;
      if (title) title.textContent = "Editar terminal";
      document.getElementById("term-tipo").value = t.tipo || "pdv";
      syncTipoFields();
      document.getElementById("term-estab").value = t.estabelecimento_id || "";
      document.getElementById("term-codigo").value = t.codigo || "";
      document.getElementById("term-nome").value = t.nome || "";
      document.getElementById("term-usuario").value = t.usuario_id || "";
      document.getElementById("term-impressora").value = t.impressora || "";
      document.getElementById("term-balanca").value = t.balanca || "mock";
      document.getElementById("term-timeout").value = String(t.timeout_min || 30);
      document.getElementById("term-treino").checked = t.treino !== false;
      document.getElementById("term-nfce").checked = !!t.emite_nfce;
      document.getElementById("term-ativo").checked = t.ativo !== false;
    } else {
      if (title) title.textContent = "Novo terminal";
      document.getElementById("term-tipo").value = "pdv";
      syncTipoFields();
    }
    if (modal) modal.hidden = false;
  }

  function closeTerminalModal() {
    const modal = document.getElementById("terminal-modal");
    if (modal) modal.hidden = true;
  }

  async function saveTerminal(ev) {
    ev.preventDefault();
    const id = document.getElementById("term-id").value;
    const payload = {
      tipo: document.getElementById("term-tipo").value,
      estabelecimento_id: document.getElementById("term-estab").value,
      codigo: document.getElementById("term-codigo").value.trim().toUpperCase(),
      nome: document.getElementById("term-nome").value.trim(),
      usuario_id: document.getElementById("term-usuario").value,
      impressora: document.getElementById("term-impressora").value.trim(),
      balanca: document.getElementById("term-balanca").value,
      timeout_min: num("term-timeout", 30),
      treino: !!document.getElementById("term-treino")?.checked,
      emite_nfce: !!document.getElementById("term-nfce")?.checked,
      ativo: !!document.getElementById("term-ativo")?.checked,
    };
    if (!payload.codigo || !payload.nome || !payload.estabelecimento_id || !payload.usuario_id) {
      toast("Preencha os campos obrigatórios");
      return;
    }
    const user = cacheUsers.find((u) => u.id === payload.usuario_id);
    payload.usuario_nome = user ? user.nome || user.usuario : "";

    try {
      if (id) {
        await apiPost("/api/admin/pos/terminais/" + id, { action: "update", ...payload });
      } else {
        await apiPost("/api/admin/pos/terminais", payload);
      }
      toast(id ? "Terminal atualizado" : "Terminal criado");
      closeTerminalModal();
      await loadTerminais();
      return;
    } catch (err) {
      /* fallback local se API negada */
      if (String(err.message).includes("403") || String(err.message).includes("401")) {
        /* continue local */
      } else if (!String(err.message).match(/^[45]/)) {
        /* API returned business error */
        const msg = err.message || "Erro ao salvar";
        if (!msg.includes("Acesso") && !msg.includes("autentic")) {
          toast(msg);
          return;
        }
      }
    }

    // Demo local (sem admin logado)
    let list = loadTerminaisLocal() || cacheTerminais.slice();
    if (payload.tipo === "pdv") {
      const conflict = list.find(
        (t) =>
          t.tipo === "pdv" &&
          t.ativo !== false &&
          t.usuario_id === payload.usuario_id &&
          t.id !== id
      );
      if (conflict) {
        toast("Vendedor já vinculado ao " + conflict.codigo + " (1:1)");
        return;
      }
    }
    if (id) {
      list = list.map((t) => (t.id === id ? { ...t, ...payload, id } : t));
    } else {
      if (list.some((t) => (t.codigo || "").toUpperCase() === payload.codigo)) {
        toast("Código já existe");
        return;
      }
      list.push({
        ...payload,
        id: "local-" + Date.now().toString(36),
        criado_em: new Date().toISOString(),
      });
    }
    saveTerminaisLocal(list);
    cacheTerminais = list;
    toast(id ? "Terminal atualizado (local)" : "Terminal criado (local)");
    closeTerminalModal();
    renderTerminaisTable();
  }

  async function toggleTerminal(id) {
    try {
      await apiPost("/api/admin/pos/terminais/" + id, { action: "toggle" });
      toast("Status atualizado");
      await loadTerminais();
      return;
    } catch {
      /* local */
    }
    let list = loadTerminaisLocal() || cacheTerminais.slice();
    list = list.map((t) =>
      t.id === id ? { ...t, ativo: t.ativo === false ? true : false } : t
    );
    saveTerminaisLocal(list);
    cacheTerminais = list;
    renderTerminaisTable();
    toast("Status atualizado (local)");
  }

  let cacheFiscalLista = [];

  async function loadFiscalPanel() {
    const sel = document.getElementById("fiscal-estab");
    const hint = document.getElementById("fiscal-hint");
    if (!sel) return;
    try {
      const data = await apiGet("/api/admin/fiscal/estabelecimentos");
      cacheFiscalLista = data.estabelecimentos || [];
    } catch {
      cacheFiscalLista = [];
      if (hint) hint.textContent = "Faça login como admin para editar o fiscal por loja.";
    }
    const cur = sel.value;
    fillSelect(
      sel,
      cacheFiscalLista.map((e) => ({
        value: e.id,
        label: `${e.nome || e.id}${e.fiscal && !e.fiscal.csc ? " · sem CSC" : ""}`,
      })),
      cacheFiscalLista.length ? null : "Nenhum estabelecimento"
    );
    if (cur && cacheFiscalLista.some((e) => e.id === cur)) sel.value = cur;
    else if (cacheFiscalLista.length) sel.value = cacheFiscalLista[0].id;
    await fillFiscalForm(sel.value);
  }

  async function fillFiscalForm(eid) {
    const hint = document.getElementById("fiscal-hint");
    if (!eid) return;
    let empresa = {};
    try {
      const data = await apiGet("/api/admin/fiscal/estabelecimentos/" + encodeURIComponent(eid));
      empresa = data.empresa || {};
    } catch {
      const row = cacheFiscalLista.find((e) => e.id === eid);
      empresa = (row && row.fiscal) || {};
    }
    setVal("fisc-csc-id", empresa.csc_id || "1");
    setVal("fisc-csc", empresa.csc || "");
    setVal("fisc-serie", empresa.serie_nfce || 1);
    setVal("fisc-numero", empresa.numero_nfce || 0);
    setVal("fisc-ambiente", String(empresa.ambiente != null ? empresa.ambiente : 2));
    setVal("fisc-cert", empresa.certificado || "");
    setVal("fisc-cert-senha", empresa.cert_senha || "");
    setVal("fisc-crt", String(empresa.crt != null ? empresa.crt : 1));
    setVal("fisc-ie", empresa.inscricao_est || "");
    setVal("fisc-uf", empresa.uf != null ? empresa.uf : "");
    setVal("fisc-mun-cod", empresa.cod_municipio || "");
    if (hint) {
      const csc = String(empresa.csc || "");
      const ok = csc && !/ALTERAR/i.test(csc);
      hint.textContent = ok
        ? `Emitente: ${empresa.nome_fantasia || empresa.nome || eid} · CSC ok`
        : `Emitente: ${empresa.nome_fantasia || empresa.nome || eid} · configure o CSC real antes de produção`;
    }
  }

  async function saveFiscal(ev) {
    ev.preventDefault();
    const eid = document.getElementById("fiscal-estab")?.value;
    if (!eid) {
      toast("Selecione o estabelecimento");
      return;
    }
    const payload = {
      csc_id: val("fisc-csc-id") || "1",
      csc: val("fisc-csc"),
      serie_nfce: num("fisc-serie", 1),
      numero_nfce: num("fisc-numero", 0),
      ambiente: num("fisc-ambiente", 2),
      certificado: val("fisc-cert"),
      crt: num("fisc-crt", 1),
      inscricao_est: val("fisc-ie"),
      uf: val("fisc-uf"),
      cod_municipio: val("fisc-mun-cod"),
    };
    const senha = val("fisc-cert-senha");
    if (senha) payload.cert_senha = senha;
    try {
      await apiPost("/api/admin/fiscal/estabelecimentos/" + encodeURIComponent(eid), payload);
      toast("Fiscal da loja salvo");
      await loadFiscalPanel();
    } catch (err) {
      toast(err.message || "Erro ao salvar fiscal");
    }
  }

  function esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function bind() {
    let state = loadState();
    fillForm(state);
    renderModuleNav(state);
    loadUsuariosResumo();
    loadEstabelecimentos();

    document.querySelectorAll('.cfg-mod-btn[data-panel="gerais"]').forEach((b) => {
      b.addEventListener("click", () => showPanel("gerais"));
    });

    const form = document.getElementById("form-gerais");
    form?.addEventListener("submit", (ev) => {
      ev.preventDefault();
      state = readForm();
      if (!state.org.nome) {
        toast("Informe o nome fantasia");
        return;
      }
      saveState(state);
      renderModuleNav(state);
      document.documentElement.setAttribute("data-theme", state.preferencias.tema || "dark");
      toast("Gerais salvos");
      const active = document.querySelector(".cfg-mod-btn.active")?.dataset.panel;
      if (active && active !== "gerais" && !state.org.modulos[active]) {
        showPanel("gerais");
      }
    });

    document.getElementById("org-modulos")?.addEventListener("change", () => {
      const draft = readForm();
      renderModuleNav(draft);
    });

    document.getElementById("btn-reset-gerais")?.addEventListener("click", () => {
      localStorage.removeItem(STORAGE_KEY);
      state = loadState();
      fillForm(state);
      renderModuleNav(state);
      toast("Padrões restaurados");
    });

    document.getElementById("btn-novo-terminal")?.addEventListener("click", () =>
      openTerminalModal(null)
    );
    document.getElementById("terminal-modal-close")?.addEventListener("click", closeTerminalModal);
    document.getElementById("terminal-modal-cancel")?.addEventListener("click", closeTerminalModal);
    document.getElementById("term-tipo")?.addEventListener("change", syncTipoFields);
    document.getElementById("form-terminal")?.addEventListener("submit", saveTerminal);
    document.getElementById("fiscal-estab")?.addEventListener("change", (e) =>
      fillFiscalForm(e.target.value)
    );
    document.getElementById("form-fiscal")?.addEventListener("submit", saveFiscal);

    const params = new URLSearchParams(location.search);
    const mod = params.get("mod") || "gerais";
    if (mod !== "gerais") {
      const mods = state.org.modulos || {};
      if (mods[mod] || mod === "gerais") showPanel(mod);
      else showPanel("gerais");
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
