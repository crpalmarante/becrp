(function () {
  let pedidos = [];

  const I = "../assets/images/icons.svg";

  /* Estrutura oficial do menu Vendas */
  const MENU = [
    { id: "dashboard", label: "Dashboard", icon: "icon-home", type: "view" },
    {
      id: "grp-pedidos", label: "Pedidos", icon: "icon-file-text", type: "group", open: true,
      items: [
        { id: "cotacoes", label: "Cotações", icon: "icon-file-text", type: "view", section: "Pedidos" },
        { id: "pedidos", label: "Pedidos de Venda", icon: "icon-dollar", type: "view", section: "Pedidos" },
        { id: "contratos", label: "Contratos", icon: "icon-file-text", type: "view", section: "Pedidos" },
        { id: "faturas", label: "Faturas de Venda", icon: "icon-file-text", type: "view", section: "Pedidos" },
        { id: "receber", label: "Contas a Receber", icon: "icon-dollar", type: "view", section: "Pedidos" },
        { id: "entregas", label: "Entregas", icon: "icon-truck", type: "view", section: "Pedidos" },
        { id: "nfe", label: "NF-e", icon: "icon-file-text", type: "view", section: "Pedidos" },
        { id: "clientes", label: "Clientes", icon: "icon-users", type: "link", href: "parceiros.html?role=CUSTOMER", section: "Pedidos" },
        { id: "produtos-atalho", label: "Produtos", icon: "icon-box", type: "link", href: "produtos.html", section: "Pedidos" },
      ]
    },
    {
      id: "grp-visualizacoes", label: "Visualizações", icon: "icon-grid", type: "group", open: false,
      items: [
        { id: "kanban", label: "Kanban", icon: "icon-file-text", type: "view", section: "Visualizações" },
        { id: "calendario", label: "Calendário", icon: "icon-calendar", type: "view", section: "Visualizações" },
        { id: "pivot", label: "Pivot", icon: "icon-grid", type: "view", section: "Visualizações" },
      ]
    },
    {
      id: "grp-produtos", label: "Produtos", icon: "icon-box", type: "group",
      items: [
        { id: "produtos", label: "Produtos", icon: "icon-box", type: "link", href: "produtos.html", section: "Produtos" },
        { id: "catalogo", label: "Catálogo de Produtos", icon: "icon-box", type: "view", section: "Produtos" },
        { id: "variantes", label: "Variantes", icon: "icon-filter", type: "soon", section: "Produtos" },
        { id: "lista-precos", label: "Lista de Preços", icon: "icon-dollar", type: "link", href: "listas-preco.html", section: "Produtos" },
        { id: "descontos", label: "Descontos", icon: "icon-percent", type: "soon", section: "Produtos",
          fallbackIcon: "icon-dollar" },
        { id: "uom", label: "Unidades de Medida", icon: "icon-box", type: "soon", section: "Produtos" },
        { id: "embalagens", label: "Embalagens", icon: "icon-box", type: "soon", section: "Produtos" },
        { id: "categorias", label: "Categorias de Produtos", icon: "icon-filter", type: "link", href: "categorias.html", section: "Produtos" },
        { id: "atributos", label: "Atributos", icon: "icon-settings", type: "soon", section: "Produtos" },
        { id: "etiquetas", label: "Etiquetas (Tags)", icon: "icon-file-text", type: "soon", section: "Produtos" },
      ]
    },
    {
      id: "grp-clientes", label: "Clientes", icon: "icon-users", type: "group",
      items: [
        { id: "clientes-pj", label: "Clientes", icon: "icon-users", type: "link", href: "parceiros.html?role=CUSTOMER", section: "Clientes" },
        { id: "parceiros", label: "Parceiros", icon: "icon-users", type: "link", href: "parceiros.html", section: "Clientes" },
        { id: "contatos", label: "Contatos (legado)", icon: "icon-users", type: "link", href: "contatos.html", section: "Clientes" },
        { id: "enderecos", label: "Endereços de entrega", icon: "icon-truck", type: "soon", section: "Clientes" },
        { id: "historico", label: "Histórico de compras", icon: "icon-clock", type: "soon", section: "Clientes" },
      ]
    },
    {
      id: "grp-relatorios", label: "Relatórios", icon: "icon-file-text", type: "group",
      items: [
        { id: "relatorio", label: "Análise de Vendas", icon: "icon-file-text", type: "view", section: "Relatórios" },
        { id: "rel-receita", label: "Receita", icon: "icon-dollar", type: "soon", section: "Relatórios" },
        { id: "rel-margem", label: "Margem", icon: "icon-dollar", type: "soon", section: "Relatórios" },
        { id: "rel-produtos", label: "Produtos vendidos", icon: "icon-box", type: "soon", section: "Relatórios" },
        { id: "rel-vendedores", label: "Vendedores", icon: "icon-users", type: "soon", section: "Relatórios" },
        { id: "rel-comissoes", label: "Comissões", icon: "icon-dollar", type: "soon", section: "Relatórios" },
        { id: "dashboard", label: "KPI Dashboard", icon: "icon-home", type: "view", section: "Relatórios" },
      ]
    },
    {
      id: "grp-config", label: "Configurações", icon: "icon-settings", type: "group",
      items: [
        { id: "cfg-equipes", label: "Equipes de Venda", icon: "icon-users", type: "soon", section: "Configurações" },
        { id: "cfg-faturamento", label: "Métodos de Faturamento", icon: "icon-dollar", type: "soon", section: "Configurações" },
        { id: "cfg-precos", label: "Lista de Preços", icon: "icon-dollar", type: "link", href: "listas-preco.html", section: "Configurações" },
        { id: "cfg-pagamento", label: "Termos de Pagamento", icon: "icon-file-text", type: "soon", section: "Configurações" },
        { id: "cfg-entrega", label: "Métodos de Entrega", icon: "icon-truck", type: "soon", section: "Configurações" },
        { id: "cfg-incoterms", label: "Incoterms", icon: "icon-globe", type: "soon", section: "Configurações",
          fallbackIcon: "icon-file-text" },
        { id: "cfg-assinaturas", label: "Assinaturas digitais", icon: "icon-lock", type: "soon", section: "Configurações" },
        { id: "cfg-portal", label: "Portal do Cliente", icon: "icon-users", type: "soon", section: "Configurações" },
        { id: "cfg-catalogo", label: "Catálogo de Produtos", icon: "icon-box", type: "soon", section: "Configurações" },
        { id: "cfg-aprovacao", label: "Aprovação de descontos", icon: "icon-lock", type: "soon", section: "Configurações" },
        { id: "cfg-multiempresa", label: "Multiempresa", icon: "icon-building", type: "link", href: "empresas.html", section: "Configurações" },
      ]
    },
  ];

  const money = (n) =>
    (Number(n) || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  const STATUS_LABEL = {
    pendente: "Pendente",
    aprovado: "Aprovado",
    faturado: "Faturado",
    rascunho: "Rascunho",
    cancelado: "Cancelado",
    bloqueado: "Bloqueado",
    convertida: "Convertida",
    ativo: "Ativo",
    suspenso: "Suspenso",
    encerrado: "Encerrado",
  };
  const CICLO_LABEL = { mensal: "Mensal", trimestral: "Trimestral", anual: "Anual", unico: "Único" };
  function onlyDigits(s) { return String(s || "").replace(/\D/g, ""); }
  function isCnpj(doc) { return onlyDigits(doc).length === 14; }
  function escapeHtml(s) {
    return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
  }
  function iconOf(item) {
    return item.icon || item.fallbackIcon || "icon-file-text";
  }

  function renderNav() {
    const nav = document.getElementById("vendas-nav");
    let html = "";
    for (const node of MENU) {
      if (node.type === "view") {
        html += `<a class="menu-item" href="#${node.id}" data-nav="${node.id}">
          <svg class="icon"><use href="${I}#${node.icon}"/></svg>
          <span class="menu-label">${node.label}</span>
        </a>`;
        continue;
      }
      if (node.type === "group") {
        html += `<div class="menu-item has-children ${node.open ? "open" : ""}" data-group="${node.id}">
          <svg class="icon"><use href="${I}#${node.icon}"/></svg>
          <span class="menu-label">${node.label}</span>
          <svg class="icon icon-16 menu-arrow"><use href="${I}#icon-chevron-down"/></svg>
        </div>`;
        html += `<div class="menu-submenu ${node.open ? "open" : ""}" id="sub-${node.id}">`;
        for (const item of node.items) {
          if (item.type === "link") {
            html += `<a class="menu-item" href="${item.href}">
              <svg class="icon"><use href="${I}#${iconOf(item)}"/></svg>
              <span class="menu-label">${item.label}</span>
            </a>`;
          } else if (item.type === "view") {
            html += `<a class="menu-item" href="#${item.id}" data-nav="${item.id}">
              <svg class="icon"><use href="${I}#${iconOf(item)}"/></svg>
              <span class="menu-label">${item.label}</span>
            </a>`;
          } else {
            html += `<a class="menu-item soon" href="#${item.id}" data-nav="${item.id}" data-soon="1"
              data-section="${item.section || node.label}" data-label="${item.label}">
              <svg class="icon"><use href="${I}#${iconOf(item)}"/></svg>
              <span class="menu-label">${item.label}</span>
              <span class="soon-tag">em breve</span>
            </a>`;
          }
        }
        html += `</div>`;
      }
    }
    html += `<a class="menu-item" href="../index4.html">
      <svg class="icon"><use href="${I}#icon-chevron-left"/></svg>
      <span class="menu-label">Menu</span>
    </a>`;
    nav.innerHTML = html;

    nav.querySelectorAll("[data-group]").forEach((el) => {
      el.addEventListener("click", () => {
        const id = el.dataset.group;
        const sub = document.getElementById("sub-" + id);
        el.classList.toggle("open");
        if (sub) sub.classList.toggle("open");
      });
    });

    nav.querySelectorAll("[data-nav]").forEach((a) => {
      a.addEventListener("click", (e) => {
        e.preventDefault();
        showView(a.dataset.nav, {
          soon: a.dataset.soon === "1",
          label: a.dataset.label || a.querySelector(".menu-label")?.textContent,
          section: a.dataset.section || "",
        });
      });
    });
  }

  let currentDoc = null;
  let listReturn = "pedidos";

  function showView(id, meta = {}) {
    const target = id || "dashboard";
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));

    if (target === "dashboard") {
      document.getElementById("view-dashboard").classList.add("active");
    } else if (target === "pedidos") {
      listReturn = "pedidos";
      document.getElementById("view-pedidos").classList.add("active");
      applyFilter();
    } else if (target === "cotacoes") {
      listReturn = "cotacoes";
      document.getElementById("view-cotacoes").classList.add("active");
      renderCotacoes();
    } else if (target === "contratos") {
      document.getElementById("view-contratos").classList.add("active");
      renderContratos();
    } else if (target === "faturas") {
      document.getElementById("view-faturas").classList.add("active");
      renderFaturas();
    } else if (target === "receber") {
      document.getElementById("view-receber").classList.add("active");
      renderReceber();
    } else if (target === "relatorio") {
      document.getElementById("view-relatorio").classList.add("active");
      renderRelatorio();
    } else if (target === "kanban") {
      document.getElementById("view-kanban").classList.add("active");
      renderKanban();
    } else if (target === "calendario") {
      document.getElementById("view-calendario").classList.add("active");
      renderCalendario();
    } else if (target === "pivot") {
      document.getElementById("view-pivot").classList.add("active");
      renderPivot();
    } else if (target === "catalogo") {
      document.getElementById("view-catalogo").classList.add("active");
      renderCatalogo();
    } else if (target === "entregas") {
      document.getElementById("view-entregas").classList.add("active");
      renderEntregas();
    } else if (target === "entrega-form") {
      document.getElementById("view-entrega-form").classList.add("active");
    } else if (target === "nfe") {
      document.getElementById("view-nfe").classList.add("active");
      renderNfe();
    } else if (target === "nfe-form") {
      document.getElementById("view-nfe-form").classList.add("active");
    } else if (target === "form" || target.startsWith("doc-")) {
      document.getElementById("view-form").classList.add("active");
    } else {
      document.getElementById("view-placeholder").classList.add("active");
      const section = meta.section || "Vendas";
      const label = meta.label || target;
      document.getElementById("ph-crumb").textContent = `BECRP / Vendas / ${section}`;
      document.getElementById("ph-title").textContent = label;
      document.getElementById("ph-name").textContent = label;
      document.getElementById("ph-desc").textContent = meta.soon
        ? "Componente previsto no módulo de Vendas Corporativas (B2B). Em implementação."
        : "Área do módulo de Vendas.";
    }

    document.querySelectorAll("#vendas-nav [data-nav]").forEach((a) => {
      const activeNav = target === "form" ? listReturn : target;
      a.classList.toggle("active", a.dataset.nav === activeNav);
    });
    if (!target.startsWith("doc-") && target !== "form") {
      history.replaceState(null, "", "#" + target);
    }
  }

  window.addEventListener("hashchange", () => {
    const raw = (location.hash || "#dashboard").slice(1);
    if (raw.startsWith("doc-")) {
      openForm(raw.replace("doc-", ""));
      return;
    }
    const link = document.querySelector(`#vendas-nav [data-nav="${raw}"]`);
    showView(raw, {
      soon: link?.dataset.soon === "1",
      label: link?.dataset.label || link?.querySelector(".menu-label")?.textContent,
      section: link?.dataset.section || "",
    });
  });

  function calcLine(i) {
    const qtd = Number(i.qtd) || 0;
    const preco = Number(i.preco) || 0;
    const desc = Number(i.desconto) || 0;
    const base = qtd * preco * (1 - desc / 100);
    return Number(i.subtotal != null ? i.subtotal : base);
  }

  function calcTotals(doc) {
    const lines = doc.itens || [];
    let subtotal = 0;
    let impostos = 0;
    lines.forEach((i) => {
      const line = calcLine(i);
      const tax = Number(i.imposto) || 0;
      subtotal += line;
      impostos += line * (tax / 100);
    });
    return { subtotal, impostos, total: subtotal + impostos };
  }

  function createNew(tipo, prefill = {}) {
    const hoje = new Date();
    const ymd = hoje.toISOString().slice(0, 10);
    const validade = new Date(hoje.getTime() + 15 * 86400000).toISOString().slice(0, 10);
    const doc = Object.assign({
      tipo,
      data: ymd,
      hora: hoje.toTimeString().slice(0, 8),
      validade,
      razao_social: "",
      cnpj: "",
      ie: "",
      cidade: "",
      uf: "",
      endereco_cobranca: "",
      endereco_entrega: "",
      lista_precos: "",
      lista_precos_id: "",
      vendedor: (JSON.parse(localStorage.getItem("user_data") || "{}").nome) || "Admin",
      equipe: "",
      ref_cliente: "",
      empresa: "",
      condicao_pg: "",
      forma_pg: "",
      status: "rascunho",
      notas: "",
      info_extra: "",
      smart: { entregas: 0, faturas: 0, compras: 0, assinaturas: 0, projetos: 0, tarefas: 0 },
      itens: [],
    }, prefill);
    saveDoc(doc, "create").then((res) => {
      if (res.status !== "ok") return alert(res.message || "Erro ao criar documento");
      doc.id = res.id;
      doc.numero = res.numero;
      pedidos.unshift(doc);
      openForm(doc.id);
    });
  }

  async function saveDoc(doc, action) {
    try {
      return await window.api("/api/vendas/b2b", {
        method: "POST",
        body: JSON.stringify(Object.assign({ action }, doc)),
      });
    } catch (e) {
      return { status: "error", message: String(e) };
    }
  }

  async function refreshFromServer() {
    try {
      const data = await window.api("/api/vendas/b2b");
      const remote = (data.pedidos || []).filter((p) => isCnpj(p.cnpj) || p.tipo === "cotacao" || p.status === "rascunho");
      pedidos = remote;
      renderDashboard();
      applyFilter();
      if (listReturn === "cotacoes") renderCotacoes();
      const ativos = ["kanban", "calendario", "pivot", "relatorio"];
      ativos.forEach((v) => {
        const el = document.getElementById("view-" + v);
        if (el && el.classList.contains("active")) {
          if (v === "kanban") renderKanban();
          else if (v === "calendario") renderCalendario();
          else if (v === "pivot") renderPivot();
          else renderRelatorio();
        }
      });
      return true;
    } catch (e) {
      return false;
    }
  }

  const READONLY_FIELDS = [
    ["numero", "Número"],
    ["data", "Data"],
    ["validade", "Validade"],
    ["vendedor", "Vendedor"],
    ["equipe", "Equipe"],
    ["empresa", "Empresa"],
  ];
  const EDITABLE_FIELDS = [
    ["razao_social", "Razão social", "text"],
    ["cnpj", "CNPJ", "text"],
    ["ie", "Inscrição estadual", "text"],
    ["cidade", "Cidade", "text"],
    ["uf", "UF", "text"],
    ["endereco_cobranca", "Endereço de cobrança", "textarea"],
    ["endereco_entrega", "Endereço de entrega", "textarea"],
    ["condicao_pg", "Condição de pagamento", "text"],
    ["forma_pg", "Forma de pagamento", "text"],
    ["ref_cliente", "Referência do cliente", "text"],
  ];

  let produtosDl = [];
  let priceLists = [];
  let catalogProdutos = [];
  let clientesB2b = [];
  async function loadProdutos() {
    try {
      const data = await window.api("/api/admin/produtos");
      if (data.status === "ok") produtosDl = data.produtos || [];
    } catch (e) { produtosDl = []; }
    const dl = document.getElementById("produtos-dl");
    if (dl) dl.innerHTML = produtosDl.map((p) =>
      `<option value="${escapeHtml(p.nome || p.id)}" data-id="${escapeHtml(p.id)}"></option>`).join("");
  }
  async function loadClientes() {
    try {
      const data = await window.api("/api/vendas/b2b/clientes");
      clientesB2b = data.status === "ok" ? (data.clientes || []) : [];
    } catch (e) { clientesB2b = []; }
    const dl = document.getElementById("clientes-dl");
    if (dl) dl.innerHTML = clientesB2b.map((c) =>
      `<option value="${escapeHtml(c.razao_social)}" data-cnpj="${escapeHtml(c.cnpj)}" data-id="${escapeHtml(c.id)}"></option>`).join("");
  }
  function setField(key, val) {
    const el = document.querySelector(`[data-field="${key}"]`);
    if (el) el.value = val || "";
    currentDoc[key] = val || "";
  }
  async function loadCatalogo() {
    try {
      const data = await window.api("/api/vendas/b2b/catalog");
      if (data.status === "ok") {
        priceLists = data.price_lists || [];
        catalogProdutos = data.produtos || [];
      }
    } catch (e) { priceLists = []; catalogProdutos = []; }
    const catView = document.getElementById("view-catalogo");
    if (catView && catView.classList.contains("active")) renderCatalogo();
  }
  function produtoIdForName(nome) {
    const found = produtosDl.find((p) => String(p.nome) === String(nome));
    return found ? found.id : "";
  }
  function resolveLinePrice(produtoNome, prodId, listaId) {
    if (!produtoNome) return 0;
    const p = catalogProdutos.find((x) =>
      String(x.nome) === String(produtoNome) || (prodId && String(x.id) === String(prodId)));
    if (!p) return 0;
    const pl = priceLists.find((l) => String(l.id) === String(listaId));
    if (pl && pl.items && String(p.id) in pl.items) return Number(pl.items[String(p.id)]) || 0;
    return Number(p.preco) || 0;
  }
  function renderListaSelect(v, locked = false) {
    const atual = v.lista_precos_id || priceLists.find((l) => String(l.name) === String(v.lista_precos))?.id || "";
    if (!priceLists.length) {
      return `<div class="so-field"><label>Lista de preços</label>
        <input type="text" data-field="lista_precos" value="${escapeHtml(v.lista_precos || "")}" ${locked ? "disabled" : ""}></div>`;
    }
    return `<div class="so-field"><label>Lista de preços</label>
      <select data-field="lista_precos" ${locked ? "disabled" : ""}>
        <option value="">Preço base (sem lista)</option>
        ${priceLists.map((l) => `<option value="${escapeHtml(l.id)}" ${String(l.id) === String(atual) ? "selected" : ""}>${escapeHtml(l.name)}</option>`).join("")}
      </select></div>`;
  }

  function isLocked(v) {
    return ["faturado", "cancelado", "bloqueado", "convertida"].includes(v.status);
  }
  function renderHeaderEditable(v) {
    const locked = isLocked(v);
    const ro = READONLY_FIELDS.map(([key, label]) => {
      const val = key === "data" ? `${v.data || "—"} ${v.hora || ""}` : (v[key] != null ? v[key] : "—");
      return `<div class="so-field"><label>${label}</label><div class="val">${escapeHtml(String(val))}</div></div>`;
    }).join("");
    const ed = EDITABLE_FIELDS.map(([key, label, type]) => {
      const val = v[key] != null ? String(v[key]) : "";
      if (key === "razao_social") {
        return `<div class="so-field"><label>${label}</label>
          <input type="text" data-field="razao_social" list="clientes-dl" value="${escapeHtml(val)}" ${locked ? "disabled" : ""}></div>`;
      }
      const input = type === "textarea"
        ? `<textarea data-field="${key}" ${locked ? "disabled" : ""}>${escapeHtml(val)}</textarea>`
        : `<input type="text" data-field="${key}" value="${escapeHtml(val)}" ${locked ? "disabled" : ""}>`;
      return `<div class="so-field"><label>${label}</label>${input}</div>`;
    }).join("");
    return ro + renderListaSelect(v, locked) + ed;
  }

  function renderLinesEditable(v) {
    const locked = isLocked(v);
    const body = document.getElementById("so-lines-body");
    const itens = v.itens || [];
    if (!itens.length) {
      body.innerHTML = `<tr><td colspan="9" class="empty">Sem linhas ${locked ? "" : "— adicione abaixo"}</td></tr>`;
      return;
    }
    body.innerHTML = itens.map((i, idx) => `
      <tr data-idx="${idx}">
        <td><input type="text" class="ln-produto" value="${escapeHtml(i.produto || "")}" list="produtos-dl" ${locked ? "disabled" : ""}></td>
        <td><input type="text" class="ln-descricao" value="${escapeHtml(i.descricao || "")}" ${locked ? "disabled" : ""}></td>
        <td><input type="number" class="ln-qtd" value="${i.qtd}" ${locked ? "disabled" : ""}></td>
        <td><input type="text" class="ln-uom" value="${escapeHtml(i.uom || "UN")}" ${locked ? "disabled" : ""}></td>
        <td><input type="text" class="ln-preco" data-mask="moeda" inputmode="decimal" value="${i.preco ? Mascaras.fmtMoeda(String(Math.round(Number(i.preco) * 100))) : ""}" ${locked ? "disabled" : ""}></td>
        <td><input type="number" class="ln-desconto" value="${Number(i.desconto) || 0}" ${locked ? "disabled" : ""}></td>
        <td><input type="number" class="ln-imposto" value="${Number(i.imposto) || 0}" ${locked ? "disabled" : ""}></td>
        <td class="money ln-subtotal">${money(calcLine(i))}</td>
        <td>${locked ? "" : '<button type="button" class="so-btn danger ln-remove" title="Remover linha">×</button>'}</td>
      </tr>`).join("");
    body.querySelectorAll("input").forEach((el) => el.addEventListener("input", syncLines));
    body.querySelectorAll(".ln-produto").forEach((el) => el.addEventListener("change", () => {
      const nome = el.value.trim();
      const p = catalogProdutos.find((x) => String(x.nome) === String(nome));
      if (p) {
        el.closest("tr").querySelector(".ln-preco").value =
          Mascaras.fmtMoeda(String(Math.round(Number(resolveLinePrice(nome, p.id, currentDoc.lista_precos_id || "")) * 100)));
      }
      syncLines();
    }));
    body.querySelectorAll(".ln-remove").forEach((btn) => btn.addEventListener("click", (e) => {
      const row = e.target.closest("tr");
      currentDoc.itens.splice(Number(row.dataset.idx), 1);
      renderLinesEditable(currentDoc);
      recalcTotals();
    }));
  }

  function collectLines() {
    const rows = document.querySelectorAll("#so-lines-body tr[data-idx]");
    const itens = [];
    rows.forEach((row) => {
      const produto = row.querySelector(".ln-produto").value.trim();
      const qtd = Number(row.querySelector(".ln-qtd").value) || 0;
      if (!produto && qtd === 0) return;
      const preco = Number(Mascaras.limparMoeda(row.querySelector(".ln-preco").value)) || 0;
      itens.push({
        prod_id: produtoIdForName(produto) || currentDoc.itens[Number(row.dataset.idx)]?.prod_id || "",
        produto,
        descricao: row.querySelector(".ln-descricao").value.trim(),
        qtd,
        uom: row.querySelector(".ln-uom").value.trim() || "UN",
        preco,
        desconto: Number(row.querySelector(".ln-desconto").value) || 0,
        imposto: Number(row.querySelector(".ln-imposto").value) || 0,
      });
    });
    return itens;
  }

  function syncLines() {
    currentDoc.itens = collectLines();
    recalcTotals();
  }

  function recalcTotals() {
    const totals = calcTotals(currentDoc);
    document.getElementById("so-totals").innerHTML = `
      <div class="row"><span>Subtotal</span><span class="money">${money(totals.subtotal)}</span></div>
      <div class="row"><span>Impostos</span><span class="money">${money(totals.impostos)}</span></div>
      <div class="row total"><span>Total</span><span class="money">${money(totals.total)}</span></div>
    `;
    document.querySelectorAll("#so-lines-body tr[data-idx]").forEach((row) => {
      const idx = Number(row.dataset.idx);
      row.querySelector(".ln-subtotal").textContent = money(calcLine(currentDoc.itens[idx] || {}));
    });
  }

  function collectDoc() {
    EDITABLE_FIELDS.forEach(([key]) => {
      const el = document.querySelector(`[data-field="${key}"]`);
      if (el) currentDoc[key] = el.value.trim();
    });
    const lsel = document.querySelector('[data-field="lista_precos"]');
    if (lsel) {
      const lid = lsel.value;
      const pl = priceLists.find((l) => String(l.id) === String(lid));
      currentDoc.lista_precos_id = lid || "";
      currentDoc.lista_precos = lid ? (pl ? pl.name : lid) : "";
    }
    const notas = document.querySelector("#so-notas-input");
    if (notas) currentDoc.notas = notas.value;
    const extra = document.querySelector("#so-extras-input");
    if (extra) currentDoc.info_extra = extra.value;
    currentDoc.itens = collectLines();
    return currentDoc;
  }

  async function saveNow() {
    const doc = collectDoc();
    const res = await saveDoc(doc, "update");
    if (res.status !== "ok") { alert(res.message || "Falha ao salvar"); return false; }
    await refreshFromServer();
    currentDoc = pedidos.find((p) => String(p.id) === String(doc.id)) || currentDoc;
    return true;
  }

  function openForm(id) {
    const v = pedidos.find((x) => String(x.id) === String(id));
    if (!v) return;
    currentDoc = v;
    window._currentDoc = v;
    listReturn = v.tipo === "cotacao" ? "cotacoes" : "pedidos";
    const tipoLabel = v.tipo === "cotacao" ? "Cotação" : "Pedido de Venda";
    const st = v.status || "pendente";
    const locked = isLocked(v);
    const smart = v.smart || {};

    document.getElementById("so-smart").innerHTML = [
      ["Entregas", smart.entregas || 0],
      ["Faturas", smart.faturas || 0],
      ["Compras", smart.compras || 0],
      ["Assinaturas", smart.assinaturas || 0],
      ["Projetos", smart.projetos || 0],
      ["Tarefas", smart.tarefas || 0],
    ].map(([label, n]) => `
      <button type="button" class="so-smart-btn" data-smart="${label}">
        <strong>${n}</strong><span>${label}</span>
      </button>`).join("");

    const btns = [];
    if (!locked) btns.push('<button type="button" class="so-btn primary" data-action="salvar">Salvar</button>');
    if (["rascunho", "pendente"].includes(st)) btns.push('<button type="button" class="so-btn primary" data-action="confirmar">Confirmar</button>');
    if (v.tipo === "cotacao" && !["convertida", "cancelado"].includes(st))
      btns.push('<button type="button" class="so-btn primary" data-action="converter">Converter em Pedido</button>');
    if (v.tipo !== "cotacao" && ["rascunho", "pendente"].includes(st)) btns.push('<button type="button" class="so-btn" data-action="aprovar">Aprovar</button>');
    if (v.tipo !== "cotacao" && st === "aprovado") btns.push('<button type="button" class="so-btn" data-action="fatura">Criar Fatura</button>');
    if (v.tipo !== "cotacao" && st === "faturado") {
      btns.push('<button type="button" class="so-btn" data-action="devolver">Devolver</button>');
    }
    if (v.tipo !== "cotacao" && st === "faturado" && v.nfe_numero
        && String(v.nfe_status || "RASCUNHO").toUpperCase() === "RASCUNHO") {
      btns.push('<button type="button" class="so-btn primary" data-action="autorizar_nfe">Autorizar NF-e</button>');
    }
    if (v.id && !["cancelado"].includes(st)) {
      btns.push('<button type="button" class="so-btn" data-action="gerar_contrato">Gerar Contrato</button>');
    }
    btns.push('<button type="button" class="so-btn" data-action="duplicar">Duplicar</button>');
    if (v.id) btns.push(`<button type="button" class="so-btn" onclick="printPedido(window._currentDoc)">Imprimir PDF</button>`);
    if (!locked && st !== "bloqueado") btns.push('<button type="button" class="so-btn" data-action="bloquear">Bloquear</button>');
    if (st === "bloqueado") btns.push('<button type="button" class="so-btn" data-action="bloquear">Desbloquear</button>');
    if (!locked) btns.push('<button type="button" class="so-btn danger" data-action="cancelar">Cancelar</button>');
    if (st !== "faturado") btns.push('<button type="button" class="so-btn danger" data-action="excluir">Excluir</button>');
    document.getElementById("so-actions").innerHTML = btns.join("");

    document.getElementById("so-status").innerHTML =
      `<div class="so-status badge badge-${escapeHtml(st)}">${tipoLabel} · ${STATUS_LABEL[st] || st}</div>`;

    document.getElementById("so-header").innerHTML = renderHeaderEditable(v);
    document.getElementById("so-lines-body").innerHTML = "";
    renderLinesEditable(v);
    recalcTotals();

    const notasVal = v.notas || "";
    const extrasVal = v.info_extra || "";
    document.getElementById("so-extras").innerHTML =
      `<textarea id="so-extras-input" style="width:100%;min-height:90px;background:rgba(0,0,0,.2);border:1px solid var(--border-color);border-radius:8px;color:var(--text-primary);padding:8px 10px;font-size:13px">${escapeHtml(extrasVal)}</textarea>`;
    document.getElementById("so-notas").innerHTML =
      `<textarea id="so-notas-input" style="width:100%;min-height:90px;background:rgba(0,0,0,.2);border:1px solid var(--border-color);border-radius:8px;color:var(--text-primary);padding:8px 10px;font-size:13px">${escapeHtml(notasVal)}</textarea>`;

    document.querySelectorAll(".so-tab").forEach((t) => t.classList.toggle("active", t.dataset.pane === "linhas"));
    document.querySelectorAll(".so-pane").forEach((p) => p.classList.toggle("active", p.id === "pane-linhas"));

    showView("form");
    history.replaceState(null, "", "#doc-" + v.id);

    document.getElementById("btn-add-line").onclick = () => {
      if (isLocked(currentDoc)) return;
      currentDoc.itens.push({ produto: "", qtd: 1, uom: "UN", preco: 0, desconto: 0, imposto: 0 });
      renderLinesEditable(currentDoc);
      recalcTotals();
    };
    document.getElementById("btn-add-line").disabled = locked;
    document.getElementById("btn-aplicar-precos").disabled = locked;

    const lsel = document.querySelector('[data-field="lista_precos"]');
    if (lsel) {
      lsel.onchange = () => {
        const lid = lsel.value;
        const pl = priceLists.find((l) => String(l.id) === String(lid));
        currentDoc.lista_precos_id = lid || "";
        currentDoc.lista_precos = lid ? (pl ? pl.name : lid) : "";
      };
    }

    const razaoInput = document.querySelector('[data-field="razao_social"]');
    if (razaoInput) {
      razaoInput.onchange = () => {
        const nome = razaoInput.value.trim();
        const cli = clientesB2b.find((c) => String(c.razao_social) === String(nome));
        if (!cli) return;
        setField("cnpj", cli.cnpj);
        setField("ie", cli.ie);
        setField("cidade", cli.cidade);
        setField("uf", cli.uf);
        setField("endereco_cobranca", cli.endereco_cobranca);
        if (!currentDoc.endereco_entrega) setField("endereco_entrega", cli.endereco_cobranca);
        currentDoc.cliente_id = cli.id;
        currentDoc.cliente_nome = cli.razao_social;
        currentDoc.payment_terms = cli.payment_terms || "30";
        // Lista padrão do parceiro → pedido
        if (cli.default_price_list_id) {
          const pl = priceLists.find((l) => String(l.id) === String(cli.default_price_list_id));
          currentDoc.lista_precos_id = cli.default_price_list_id;
          currentDoc.lista_precos = pl ? pl.name : cli.default_price_list_id;
          const lsel = document.querySelector('[data-field="lista_precos"]');
          if (lsel) lsel.value = cli.default_price_list_id;
        }
      };
    }

    document.getElementById("btn-aplicar-precos").onclick = () => {
      if (isLocked(currentDoc)) return;
      const lid = currentDoc.lista_precos_id || "";
      currentDoc.itens = collectLines().map((i) => {
        i.preco = resolveLinePrice(i.produto, i.prod_id, lid);
        return i;
      });
      renderLinesEditable(currentDoc);
      recalcTotals();
    };

    document.querySelectorAll("#so-actions [data-action]").forEach((btn) => {
      btn.onclick = async () => {
        const a = btn.dataset.action;
        const doc = currentDoc;
        if (a === "salvar") { if (await saveNow()) openForm(doc.id); return; }
        if (a === "confirmar") {
          if (!(await saveNow())) return;
          const res = await saveDoc({ id: doc.id, status: "pendente" }, "status");
          if (res.status === "ok") { await refreshFromServer(); openForm(doc.id); }
          else alert(res.message || "Falha ao confirmar");
          return;
        }
        if (a === "aprovar") {
          if (!(await saveNow())) return;
          let payload = { id: doc.id };
          let res = await saveDoc(payload, "aprovar");
          if (res.status !== "ok" && res.code === "reserva_parcial") {
            const okPartial = confirm(
              (res.message || "Estoque insuficiente.") +
              "\n\nConfirmar pedido parcial (reservar só o disponível)?"
            );
            if (!okPartial) return;
            payload = { id: doc.id, allow_partial: true };
            res = await saveDoc(payload, "aprovar");
          }
          if (res.status === "ok") {
            const parts = ["Pedido aprovado"];
            if (res.entrega && res.entrega.id) parts.push("Entrega " + res.entrega.id);
            if (res.credit && res.credit.message) parts.push(res.credit.message);
            if (res.reserva && res.reserva.parcial) parts.push("Reserva parcial");
            if ((res.reserva_warnings || (res.reserva && res.reserva.warnings) || []).length)
              parts.push("Avisos de reserva");
            alert(parts.join(" · "));
            await refreshFromServer(); openForm(doc.id);
          } else alert(res.message || "Falha ao aprovar");
          return;
        }
        if (a === "converter") {
          if (!(await saveNow())) return;
          if (!confirm("Converter esta cotação em Pedido de Venda?")) return;
          const res = await saveDoc({ id: doc.id }, "converter");
          if (res.status === "ok") {
            alert(res.message || ("Pedido " + (res.pedido_numero || "") + " criado"));
            await refreshFromServer();
            if (res.pedido_id) openForm(res.pedido_id);
            else openForm(doc.id);
          } else alert(res.message || "Falha ao converter");
          return;
        }
        if (a === "fatura") {
          if (!(await saveNow())) return;
          const res = await saveDoc({ id: doc.id }, "faturar");
          if (res.status === "ok") {
            const parts = ["Fatura " + (res.fatura_numero || "")];
            if (res.ar && res.ar.titulos) parts.push(res.ar.titulos.length + " título(s) AR");
            if (res.nfe && res.nfe.numero) parts.push("NF-e " + res.nfe.numero + " (rascunho)");
            if (res.entrega_id) parts.push("Entrega " + res.entrega_id);
            if (res.estoque === "na_entrega") parts.push("Estoque na saída da entrega");
            alert(parts.join(" · "));
            await refreshFromServer(); openForm(doc.id);
          } else alert(res.message || "Falha ao faturar");
          return;
        }
        if (a === "devolver") {
          if (!confirm("Registrar devolução deste pedido?\n\nIsso gerará nota de crédito e retorno ao estoque.")) return;
          const res = await saveDoc({ id: doc.id }, "devolver");
          if (res.status === "ok") {
            alert(res.message || "Devolução registrada");
            await refreshFromServer(); openForm(doc.id);
          } else alert(res.message || "Falha ao devolver");
          return;
        }
        if (a === "autorizar_nfe") {
          const simular = confirm(
            "Autorizar NF-e " + (doc.nfe_numero || "") + "?\n\n" +
            "OK = simular homologação (sem certificado)\n" +
            "Cancelar = abortar\n\n" +
            "Para SEFAZ real use Fiscal → NF-e com certificado."
          );
          if (!simular) return;
          const res = await saveDoc({ id: doc.id, simular: true }, "autorizar_nfe");
          if (res.status === "ok") {
            const n = res.nfe || {};
            alert("NF-e " + (n.numero || "") + " · " + (n.status || "") +
              (n.protocolo ? " · prot. " + n.protocolo : ""));
            await refreshFromServer(); openForm(doc.id);
          } else alert(res.message || "Falha ao autorizar NF-e");
          return;
        }
        if (a === "cancelar") {
          if (!(await saveNow())) return;
          const res = await saveDoc({ id: doc.id, status: "cancelado" }, "status");
          if (res.status === "ok") { await refreshFromServer(); openForm(doc.id); }
          else alert(res.message || "Falha ao cancelar");
          return;
        }
        if (a === "bloquear") {
          const novo = doc.status === "bloqueado" ? "pendente" : "bloqueado";
          if (novo === "bloqueado" && !(await saveNow())) return;
          const res = await saveDoc({ id: doc.id, status: novo }, "status");
          if (res.status === "ok") { await refreshFromServer(); openForm(doc.id); }
          else alert(res.message || "Falha ao bloquear");
          return;
        }
        if (a === "gerar_contrato") {
          if (!doc.id) return alert("Salve o documento antes de gerar contrato");
          if (!confirm("Gerar contrato a partir deste " + tipoLabel + "?")) return;
          const res = await window.api("/api/vendas/b2b/contratos", {
            method: "POST",
            body: JSON.stringify({ action: "from_pedido", pedido_id: doc.id }),
          });
          if (res.status === "ok") {
            alert("Contrato " + (res.contrato && res.contrato.numero) + " criado");
            showView("contratos");
            openContrato(res.contrato.id);
          } else alert(res.message || "Falha ao gerar contrato");
          return;
        }
        if (a === "duplicar") {
          const clone = Object.assign({}, collectDoc());
          delete clone.id; delete clone.numero;
          delete clone.data; delete clone.hora; delete clone.validade;
          clone.status = "rascunho";
          clone.itens = (currentDoc.itens || []).map((i) => Object.assign({}, i));
          createNew(clone.tipo === "cotacao" ? "cotacao" : "pedido", clone);          return;
        }
        if (a === "excluir") {
          if (!confirm(`Excluir ${tipoLabel} ${doc.numero || doc.id}? Esta ação não pode ser desfeita.`)) return;
          const res = await saveDoc({ id: doc.id }, "delete");
          if (res.status === "ok") {
            await refreshFromServer();
            showView("list");
            history.replaceState(null, "", "#vendas");
          } else alert(res.message || "Falha ao excluir");
          return;
        }
        alert(`Ação "${a}" no ${tipoLabel} ${v.numero || v.id} — em breve (workflow B2B).`);
      };
    });
    document.querySelectorAll("#so-smart [data-smart]").forEach((btn) => {
      btn.onclick = () => {
        const label = btn.dataset.smart;
        if (label === "Entregas" && currentDoc && currentDoc.entrega_id) {
          alert("Delivery Order: " + currentDoc.entrega_id +
            "\nAbra Operações → Entregas para acompanhar.\nEstoque baixa na saída (depart).");
          return;
        }
        if (label === "Faturas" && currentDoc && currentDoc.fatura_numero) {
          alert("Fatura " + currentDoc.fatura_numero +
            (currentDoc.nfe_numero ? " · NF-e " + currentDoc.nfe_numero : ""));
          return;
        }
        alert(`Smart button "${label}" — em breve.`);
      };
    });
  }

  let contratosCache = [];
  let currentContratoId = null;

  async function renderContratos() {
    const tbody = document.getElementById("contratos-tbody");
    const q = (document.getElementById("ct-q")?.value || "").trim();
    const st = (document.getElementById("ct-status")?.value || "").trim();
    const qs = new URLSearchParams();
    if (q) qs.set("q", q);
    if (st) qs.set("status", st);
    try {
      const data = await window.api("/api/vendas/b2b/contratos" + (qs.toString() ? "?" + qs : ""));
      contratosCache = data.contratos || [];
      if (!contratosCache.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty">Nenhum contrato</td></tr>';
        return;
      }
      tbody.innerHTML = contratosCache.map((c) => `
        <tr data-ct-id="${c.id}">
          <td><span class="badge">${escapeHtml(c.numero || ("#" + c.id))}</span></td>
          <td>${escapeHtml(c.titulo || "—")}</td>
          <td><div class="empresa-cell"><strong>${escapeHtml(c.razao_social || "—")}</strong>
            <span class="cnpj">${escapeHtml(c.cnpj || "—")}</span></div></td>
          <td>${escapeHtml((c.inicio || "—") + " → " + (c.fim || "—"))}</td>
          <td>${escapeHtml(CICLO_LABEL[c.ciclo] || c.ciclo || "—")}</td>
          <td class="money">${money(c.valor)}</td>
          <td><span class="badge badge-${escapeHtml(c.status || "rascunho")}">${escapeHtml(STATUS_LABEL[c.status] || c.status)}</span></td>
        </tr>`).join("");
      tbody.querySelectorAll("tr[data-ct-id]").forEach((tr) => {
        tr.onclick = () => openContrato(tr.dataset.ctId);
      });
      if (currentContratoId) openContrato(currentContratoId);
    } catch (e) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty">Erro ao carregar contratos</td></tr>';
    }
  }

  function openContrato(id) {
    const c = contratosCache.find((x) => String(x.id) === String(id));
    const panel = document.getElementById("ct-panel");
    if (!c) { panel.style.display = "none"; return; }
    currentContratoId = c.id;
    const st = c.status || "rascunho";
    const gens = (c.pedidos_gerados || []).map((g) =>
      `<li>Pedido ${escapeHtml(g.numero || g.pedido_id)} · ${escapeHtml(g.em || "")}</li>`
    ).join("") || "<li class='muted'>Nenhum pedido gerado</li>";
    const itens = (c.itens || []).map((it) =>
      `<tr><td>${escapeHtml(it.produto || it.prod_id || "—")}</td>
       <td>${it.qtd}</td><td class="money">${money(it.preco)}</td>
       <td class="money">${money(it.subtotal)}</td></tr>`
    ).join("") || '<tr><td colspan="4" class="muted">Sem itens</td></tr>';

    const actions = [];
    if (st === "rascunho") {
      actions.push('<button type="button" class="so-btn primary" data-ct="ativar">Ativar</button>');
      actions.push('<button type="button" class="so-btn danger" data-ct="cancelar">Cancelar</button>');
    }
    if (st === "ativo") {
      actions.push('<button type="button" class="so-btn primary" data-ct="gerar_pedido">Gerar Pedido</button>');
      actions.push('<button type="button" class="so-btn" data-ct="suspender">Suspender</button>');
      actions.push('<button type="button" class="so-btn" data-ct="encerrar">Encerrar</button>');
      actions.push('<button type="button" class="so-btn danger" data-ct="cancelar">Cancelar</button>');
    }
    if (st === "suspenso") {
      actions.push('<button type="button" class="so-btn primary" data-ct="ativar">Reativar</button>');
      actions.push('<button type="button" class="so-btn" data-ct="encerrar">Encerrar</button>');
    }

    panel.style.display = "block";
    panel.innerHTML = `
      <h3>${escapeHtml(c.numero)} · ${escapeHtml(c.titulo || "")}
        <span class="badge badge-${escapeHtml(st)}" style="margin-left:8px">${escapeHtml(STATUS_LABEL[st] || st)}</span>
      </h3>
      <p class="muted">${escapeHtml(c.razao_social || "")} · CNPJ ${escapeHtml(c.cnpj || "—")}
        · ${escapeHtml(CICLO_LABEL[c.ciclo] || c.ciclo)} · renovação ${escapeHtml(c.renovacao || "manual")}</p>
      <p>Vigência: <strong>${escapeHtml(c.inicio || "—")}</strong> → <strong>${escapeHtml(c.fim || "—")}</strong>
        · Valor: <strong class="money">${money(c.valor)}</strong></p>
      <div class="ct-actions">${actions.join("")}
        <button type="button" class="so-btn" data-ct="fechar">Fechar</button>
      </div>
      <div class="table-wrap"><table class="data">
        <thead><tr><th>Item</th><th>Qtd</th><th>Preço</th><th>Subtotal</th></tr></thead>
        <tbody>${itens}</tbody>
      </table></div>
      <p style="margin-top:12px"><strong>Pedidos gerados</strong></p>
      <ul>${gens}</ul>
      ${c.notas ? `<p class="muted" style="margin-top:8px">${escapeHtml(c.notas)}</p>` : ""}
    `;
    panel.querySelectorAll("[data-ct]").forEach((btn) => {
      btn.onclick = async () => {
        const act = btn.dataset.ct;
        if (act === "fechar") { panel.style.display = "none"; currentContratoId = null; return; }
        if (act === "gerar_pedido" && !confirm("Gerar pedido de venda a partir deste contrato?")) return;
        if (act === "cancelar" && !confirm("Cancelar contrato?")) return;
        const res = await window.api("/api/vendas/b2b/contratos", {
          method: "POST",
          body: JSON.stringify({ action: act, id: c.id }),
        });
        if (res.status !== "ok") return alert(res.message || "Falha");
        if (act === "gerar_pedido" && res.pedido) {
          alert("Pedido " + (res.pedido.numero || res.pedido.id) + " criado");
          await refreshFromServer();
        }
        await renderContratos();
        openContrato(c.id);
      };
    });
  }

  function showNovoContratoForm() {
    const panel = document.getElementById("ct-panel");
    currentContratoId = null;
    panel.style.display = "block";
    panel.innerHTML = `
      <h3>Novo Contrato</h3>
      <div class="ct-form-grid">
        <label>Título<input class="form-input" id="ct-f-titulo" placeholder="Fornecimento anual"></label>
        <label>Razão social<input class="form-input" id="ct-f-razao" required></label>
        <label>CNPJ<input class="form-input" id="ct-f-cnpj" placeholder="14 dígitos"></label>
        <label>Início<input class="form-input" id="ct-f-inicio" type="date"></label>
        <label>Fim<input class="form-input" id="ct-f-fim" type="date"></label>
        <label>Ciclo<select class="form-input" id="ct-f-ciclo">
          <option value="mensal">Mensal</option>
          <option value="trimestral">Trimestral</option>
          <option value="anual">Anual</option>
          <option value="unico">Único</option>
        </select></label>
        <label>Renovação<select class="form-input" id="ct-f-renov">
          <option value="manual">Manual</option>
          <option value="automatica">Automática</option>
          <option value="nao">Não renova</option>
        </select></label>
        <label>Valor (R$)<input class="form-input" id="ct-f-valor" type="text" data-mask="moeda" inputmode="decimal" value="0"></label>
        <label>Condição<input class="form-input" id="ct-f-terms" value="30"></label>
        <label>Item (descrição)<input class="form-input" id="ct-f-item" placeholder="Serviço / produto"></label>
        <label>Qtd item<input class="form-input" id="ct-f-qtd" type="number" step="0.001" min="0" value="1"></label>
      </div>
      <label style="display:block;margin:8px 0;font-size:12px;color:var(--text-muted)">Notas
        <textarea class="form-input" id="ct-f-notas" rows="2" style="width:100%"></textarea>
      </label>
      <div class="ct-actions">
        <button type="button" class="so-btn primary" id="ct-f-salvar">Salvar rascunho</button>
        <button type="button" class="so-btn" id="ct-f-cancel">Cancelar</button>
      </div>
    `;
    const today = new Date().toISOString().slice(0, 10);
    document.getElementById("ct-f-inicio").value = today;
    document.getElementById("ct-f-cancel").onclick = () => { panel.style.display = "none"; };
    document.getElementById("ct-f-salvar").onclick = async () => {
      const razao = document.getElementById("ct-f-razao").value.trim();
      const cnpj = onlyDigits(document.getElementById("ct-f-cnpj").value);
      if (!razao) return alert("Informe a razão social");
      if (cnpj && cnpj.length !== 14) return alert("CNPJ deve ter 14 dígitos");
      const valor = Number(Mascaras.limparMoeda(document.getElementById("ct-f-valor").value)) || 0;
      const itemDesc = document.getElementById("ct-f-item").value.trim();
      const qtd = Number(document.getElementById("ct-f-qtd").value) || 1;
      const itens = itemDesc ? [{
        produto: itemDesc, qtd, preco: valor, subtotal: valor,
      }] : (valor > 0 ? [{ produto: "Contrato", qtd: 1, preco: valor, subtotal: valor }] : []);
      const res = await window.api("/api/vendas/b2b/contratos", {
        method: "POST",
        body: JSON.stringify({
          action: "create",
          titulo: document.getElementById("ct-f-titulo").value.trim(),
          razao_social: razao,
          cnpj,
          inicio: document.getElementById("ct-f-inicio").value,
          fim: document.getElementById("ct-f-fim").value,
          ciclo: document.getElementById("ct-f-ciclo").value,
          renovacao: document.getElementById("ct-f-renov").value,
          valor,
          payment_terms: document.getElementById("ct-f-terms").value,
          notas: document.getElementById("ct-f-notas").value,
          itens,
        }),
      });
      if (res.status !== "ok") return alert(res.message || "Falha ao criar");
      await renderContratos();
      openContrato(res.contrato.id);
    };
  }

  async function renderFaturas() {
    const tbody = document.getElementById("faturas-tbody");
    try {
      const data = await window.api("/api/vendas/b2b/faturas");
      const list = (data.faturas || []).filter((f) => f && f.pedido_id != null);
      if (!list.length) {
        tbody.innerHTML = '<tr><td colspan="9" class="empty">Nenhuma fatura de venda criada</td></tr>';
        return;
      }
      tbody.innerHTML = list.map((f) => `
        <tr>
          <td><span class="badge">${escapeHtml(f.numero || ("FV" + f.id))}</span></td>
          <td>${escapeHtml(f.pedido_numero || ("#" + f.pedido_id))}</td>
          <td>${escapeHtml(f.data_emissao || "—")}</td>
          <td>${escapeHtml(f.data_vencimento || "—")}</td>
          <td><div class="empresa-cell"><strong>${escapeHtml(f.cliente || "—")}</strong><span class="cnpj">${escapeHtml(f.cnpj || "—")}</span></div></td>
          <td>${f.itens_count || 0}</td>
          <td class="money">${money(f.total)}</td>
          <td><span class="badge badge-${String(f.status).toLowerCase() === "paga" ? "faturado" : "pendente"}">${escapeHtml(f.status || "PENDENTE")}</span></td>
          <td><button type="button" class="so-btn fat-print" data-idx="${list.indexOf(f)}">Imprimir</button></td>
        </tr>`).join("");
      tbody.querySelectorAll(".fat-print").forEach(btn => {
        btn.onclick = () => printFatura(list[Number(btn.dataset.idx)]);
      });
    } catch (e) {
      tbody.innerHTML = '<tr><td colspan="9" class="empty">Erro ao carregar faturas</td></tr>';
    }
  }

  async function renderReceber() {
    const tbody = document.getElementById("ar-tbody");
    const summary = document.getElementById("ar-summary");
    const q = (document.getElementById("ar-q")?.value || "").trim();
    const st = (document.getElementById("ar-status")?.value || "").trim();
    const qs = new URLSearchParams();
    if (q) qs.set("q", q);
    if (st) qs.set("status", st);
    try {
      const data = await window.api("/api/vendas/b2b/receber?" + qs.toString());
      const list = data.titulos || [];
      if (summary) {
        summary.textContent = list.length
          ? `${list.length} título(s) · saldo aberto ${money(data.saldo_aberto)}`
          : "Nenhum título";
      }
      if (!list.length) {
        tbody.innerHTML = '<tr><td colspan="9" class="empty">Nenhum título a receber</td></tr>';
        return;
      }
      tbody.innerHTML = list.map((t) => {
        const badge = t.status === "pago" ? "faturado" : (t.status === "parcial" ? "aprovado" : "pendente");
        const canPay = t.status === "aberto" || t.status === "parcial";
        return `
        <tr data-ar="${escapeHtml(t.id)}">
          <td><span class="badge">${escapeHtml(t.id)}</span></td>
          <td><div class="empresa-cell"><strong>${escapeHtml(t.cliente || "—")}</strong><span class="cnpj">${escapeHtml(t.cnpj || "")}</span></div></td>
          <td>${escapeHtml(t.pedido_numero || "—")} / ${escapeHtml(t.fatura_numero || "—")}</td>
          <td>${t.parcela || 1}/${t.parcelas || 1}</td>
          <td>${escapeHtml(t.vencimento || "—")}</td>
          <td class="money">${money(t.valor)}</td>
          <td class="money">${money(t.saldo)}</td>
          <td><span class="badge badge-${badge}">${escapeHtml(t.status || "aberto")}</span></td>
          <td>${canPay ? `<button type="button" class="so-btn ar-baixar" data-id="${escapeHtml(t.id)}" data-saldo="${t.saldo}">Baixar</button>` : "—"}</td>
        </tr>`;
      }).join("");
      tbody.querySelectorAll(".ar-baixar").forEach((btn) => {
        btn.onclick = async () => {
          const id = btn.dataset.id;
          const saldo = btn.dataset.saldo;
          if (!confirm(`Baixar título ${id} (saldo ${money(saldo)})?`)) return;
          const res = await window.api("/api/vendas/b2b/receber", {
            method: "POST",
            body: JSON.stringify({ id }),
          });
          if (res.status === "ok") { alert("Baixa registrada"); renderReceber(); }
          else alert(res.message || "Falha na baixa");
        };
      });
    } catch (e) {
      tbody.innerHTML = '<tr><td colspan="9" class="empty">Erro ao carregar contas a receber</td></tr>';
    }
  }

  const FLOW = {
    rascunho: ["pendente", "cancelado", "bloqueado"],
    pendente: ["aprovado", "cancelado", "bloqueado"],
    aprovado: ["faturado", "cancelado", "bloqueado"],
    bloqueado: ["pendente"],
    faturado: [],
    cancelado: [],
  };

  // ═══════════ ENTREGAS ═══════════
  const ENTREGA_STATUS = { pendente:"Pendente", conferido:"Conferido", em_transito:"Em Trânsito", entregue:"Entregue", cancelado:"Cancelado" };
  let entregas = [];

  async function loadEntregas() {
    try {
      const data = await window.api("/api/vendas/b2b/entregas");
      entregas = data.entregas || [];
    } catch(e) { entregas = []; }
  }

  async function renderEntregas() {
    await loadEntregas();
    const tbody = document.getElementById("entregas-tbody");
    const q = (document.getElementById("ent-q")?.value || "").toLowerCase();
    const st = (document.getElementById("ent-status")?.value || "");
    let list = entregas;
    if (q) list = list.filter(e => (e.cliente||"").toLowerCase().includes(q) || (e.pedido_numero||"").toLowerCase().includes(q) || (e.id||"").toLowerCase().includes(q));
    if (st) list = list.filter(e => e.status === st);
    if (!list.length) { tbody.innerHTML = '<tr><td colspan="8" class="empty">Nenhuma entrega encontrada</td></tr>'; return; }
    tbody.innerHTML = list.map(e => {
      const badge = e.status === "entregue" ? "faturado" : e.status === "cancelado" ? "cancelado" : e.status === "conferido" ? "aprovado" : "pendente";
      return `<tr>
        <td><span class="badge">${escapeHtml(e.id)}</span></td>
        <td>${escapeHtml(e.pedido_numero || e.pedido_id || "—")}</td>
        <td>${escapeHtml(e.cliente || "—")}</td>
        <td>${e.itens_count || 0}</td>
        <td>${escapeHtml(e.data_agendamento || "—")} ${e.hora_agendamento ? " às " + escapeHtml(e.hora_agendamento) : ""}</td>
        <td class="money">${e.peso_total || "—"}</td>
        <td><span class="badge badge-${badge}">${ENTREGA_STATUS[e.status] || e.status}</span></td>
        <td><button type="button" class="so-btn ent-editar" data-id="${escapeHtml(e.id)}">Abrir</button></td>
      </tr>`;
    }).join("");
    tbody.querySelectorAll(".ent-editar").forEach(btn => {
      btn.onclick = () => openEntregaForm(btn.dataset.id);
    });
  }

  async function openEntregaForm(id) {
    showView("entrega-form");
    const titulo = document.getElementById("ent-form-titulo");
    const statusDiv = document.getElementById("ent-form-status");
    const actionsDiv = document.getElementById("ef-actions");
    if (id) {
      const e = entregas.find(x => x.id === id);
      if (!e) return;
      titulo.textContent = "Entrega " + id;
      statusDiv.innerHTML = `<span class="badge badge-${e.status === "entregue" ? "faturado" : e.status === "cancelado" ? "cancelado" : "pendente"}">${ENTREGA_STATUS[e.status] || e.status}</span>`;
      document.getElementById("ef-pedido").value = e.pedido_id || "";
      document.getElementById("ef-cliente").textContent = e.cliente || "—";
      document.getElementById("ef-endereco").value = e.endereco_entrega || "";
      document.getElementById("ef-data").value = e.data_agendamento || "";
      document.getElementById("ef-hora").value = e.hora_agendamento || "08:00";
      document.getElementById("ef-peso").value = e.peso_total || "";
      document.getElementById("ef-volume").value = e.volume || "";
      document.getElementById("ef-transportadora").value = e.transportadora || "";
      document.getElementById("ef-nfe").value = e.nfe_numero || "";
      const itensBody = document.getElementById("ef-itens");
      itensBody.innerHTML = (e.itens || []).map(it => `<tr>
        <td>${escapeHtml(it.produto_nome || it.produto_id)}</td>
        <td>${it.qtd_solicitada || 0}</td>
        <td><input type="number" class="form-input ent-qtd-conf" data-item-id="${it.id}" value="${it.qtd_conferida || it.qtd_solicitada || 0}" min="0" style="width:80px;padding:4px 6px;font-size:12px"></td>
        <td>${escapeHtml(it.unidade || "UN")}</td>
        <td><span class="badge badge-${it.status === "conferido" ? "aprovado" : "pendente"}">${escapeHtml(it.status || "pendente")}</span></td>
      </tr>`).join("");
      const botoes = [];
      if (e.status === "pendente") {
        botoes.push(`<button type="button" class="so-btn primary" data-action="conferir">Conferir</button>`);
        botoes.push(`<button type="button" class="so-btn" data-action="em_transito">Em Trânsito</button>`);
        botoes.push(`<button type="button" class="so-btn danger" data-action="cancelar">Cancelar</button>`);
      } else if (e.status === "conferido") {
        botoes.push(`<button type="button" class="so-btn primary" data-action="em_transito">Em Trânsito</button>`);
      } else if (e.status === "em_transito") {
        botoes.push(`<button type="button" class="so-btn primary" data-action="entregue">Confirmar Entrega</button>`);
      }
      actionsDiv.innerHTML = botoes.join("");
      actionsDiv.querySelectorAll("[data-action]").forEach(btn => {
        btn.onclick = async () => {
          const newStatus = btn.dataset.action;
          if (newStatus === "cancelar" && !confirm("Cancelar esta entrega?")) return;
          const res = await window.api("/api/vendas/b2b/entregas", {
            method: "POST",
            body: JSON.stringify({ id: e.id, status: newStatus }),
          });
          if (res.status === "ok") { await renderEntregas(); openEntregaForm(e.id); }
          else alert(res.message || "Erro");
        };
      });
    } else {
      titulo.textContent = "Nova Entrega";
      statusDiv.innerHTML = "";
      actionsDiv.innerHTML = `<button type="button" class="so-btn primary" id="btn-salvar-entrega">Salvar</button>`;
    }
  }

  // ═══════════ NF-e ═══════════
  const NFE_STATUS = { rascunho:"Rascunho", transmitida:"Transmitida", autorizada:"Autorizada", rejeitada:"Rejeitada", cancelada:"Cancelada" };
  let nfeLista = [];

  async function loadNfe() {
    try {
      const data = await window.api("/api/vendas/b2b/nfe");
      nfeLista = data.nfe || data.notas || [];
    } catch(e) { nfeLista = []; }
  }

  async function renderNfe() {
    await loadNfe();
    const tbody = document.getElementById("nfe-tbody");
    const q = (document.getElementById("nfe-q")?.value || "").toLowerCase();
    const st = (document.getElementById("nfe-status")?.value || "");
    let list = nfeLista;
    if (q) list = list.filter(n => (n.numero||"").includes(q) || (n.cliente||"").toLowerCase().includes(q));
    if (st) list = list.filter(n => n.status === st);
    if (!list.length) { tbody.innerHTML = '<tr><td colspan="9" class="empty">Nenhuma NF-e encontrada</td></tr>'; return; }
    tbody.innerHTML = list.map(n => {
      const badge = n.status === "autorizada" ? "faturado" : n.status === "rejeitada" || n.status === "cancelada" ? "cancelado" : "pendente";
      return `<tr>
        <td><span class="badge">${escapeHtml(n.numero || "—")}</span></td>
        <td>${escapeHtml(n.serie || "1")}</td>
        <td>${escapeHtml(n.data_emissao || "—")}</td>
        <td>${escapeHtml(n.cliente || "—")}</td>
        <td class="cnpj">${escapeHtml(n.cnpj_dest || "—")}</td>
        <td class="money">${money(n.valor_total)}</td>
        <td style="font-size:11px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${escapeHtml(n.chave_acesso || "")}">${escapeHtml(n.chave_acesso || "—")}</td>
        <td><span class="badge badge-${badge}">${NFE_STATUS[n.status] || n.status}</span></td>
        <td><button type="button" class="so-btn nfe-ver" data-id="${escapeHtml(n.id)}">Ver</button></td>
      </tr>`;
    }).join("");
    tbody.querySelectorAll(".nfe-ver").forEach(btn => {
      btn.onclick = () => openNfeForm(btn.dataset.id);
    });
  }

  async function openNfeForm(id) {
    showView("nfe-form");
    const titulo = document.getElementById("nfe-form-titulo");
    const statusDiv = document.getElementById("nfe-form-status");
    const actionsDiv = document.getElementById("nfe-form-actions");
    if (id) {
      const n = nfeLista.find(x => x.id === id);
      if (!n) return;
      titulo.textContent = "NF-e " + (n.numero || id);
      statusDiv.innerHTML = `<span class="badge badge-${n.status === "autorizada" ? "faturado" : n.status === "cancelada" ? "cancelado" : "pendente"}">${NFE_STATUS[n.status] || n.status}</span>`;
      document.getElementById("nf-cnpj-emit").textContent = n.emitente_cnpj || "—";
      document.getElementById("nf-rs-emit").textContent = n.emitente_razao || "—";
      document.getElementById("nf-ie-emit").textContent = n.emitente_ie || "—";
      document.getElementById("nf-ender-emit").textContent = n.emitente_endereco || "—";
      document.getElementById("nf-cnpj-dest").textContent = n.cnpj_dest || "—";
      document.getElementById("nf-rs-dest").textContent = n.cliente || "—";
      document.getElementById("nf-ie-dest").textContent = n.ie_dest || "—";
      document.getElementById("nf-ender-dest").textContent = n.endereco_dest || "—";
      document.getElementById("nf-frete-modalidade").value = n.frete_modalidade || "9";
      document.getElementById("nf-transportadora").value = n.transportadora || "";
      document.getElementById("nf-finalidade").value = n.finalidade || "1";
      document.getElementById("nf-forma-emissao").value = n.forma_emissao || "1";
      document.getElementById("nf-presenca").value = n.presenca_comprador || "1";
      document.getElementById("nf-info-adic").value = n.info_adicional || "";
      const itensBody = document.getElementById("nf-itens");
      itensBody.innerHTML = (n.itens || []).map(it => `<tr>
        <td>${escapeHtml(it.produto_nome || it.produto_id)}</td>
        <td>${escapeHtml(it.cfop || "5102")}</td>
        <td>${escapeHtml(it.unidade || "UN")}</td>
        <td>${it.quantidade || 0}</td>
        <td class="money">${money(it.valor_unitario)}</td>
        <td class="money">${money(it.valor_total)}</td>
        <td class="money">${money(it.bc_icms)}</td>
        <td>${it.aliquota_icms || 0}%</td>
        <td class="money">${money(it.valor_icms)}</td>
        <td>${it.aliquota_ipi || 0}%</td>
        <td>${it.aliquota_pis || 0}%</td>
        <td>${it.aliquota_cofins || 0}%</td>
      </tr>`).join("");
      calcNfeTotals(n.itens || []);
      if (n.status === "rascunho") {
        actionsDiv.innerHTML = `<button type="button" class="so-btn primary" data-action="transmitir">Transmitir à SEFAZ</button>
          <button type="button" class="so-btn danger" data-action="cancelar">Cancelar NF-e</button>`;
      } else {
        actionsDiv.innerHTML = `<button type="button" class="so-btn" onclick="showView('nfe')">← Voltar à lista</button>`;
      }
    } else {
      titulo.textContent = "Nova NF-e";
      statusDiv.innerHTML = '<span class="badge badge-rascunho">Rascunho</span>';
      actionsDiv.innerHTML = `<button type="button" class="so-btn primary" id="btn-salvar-nfe">Salvar Rascunho</button>
        <button type="button" class="so-btn" onclick="showView('nfe')">Cancelar</button>`;
    }
  }

  function calcNfeTotals(itens) {
    let totalProd = 0, totalIcms = 0, totalIPI = 0, totalPIS = 0, totalCOFINS = 0;
    itens.forEach(it => {
      totalProd += Number(it.valor_total) || 0;
      totalIcms += Number(it.valor_icms) || 0;
      totalIPI += (Number(it.bc_icms) * Number(it.aliquota_ipi || 0) / 100) || 0;
      totalPIS += (Number(it.valor_total) * Number(it.aliquota_pis || 0) / 100) || 0;
      totalCOFINS += (Number(it.valor_total) * Number(it.aliquota_cofins || 0) / 100) || 0;
    });
    const el = document.getElementById("nf-totals");
    if (!el) return;
    el.innerHTML = `
      <div class="row"><span>Produtos</span><span class="money">${money(totalProd)}</span></div>
      <div class="row"><span>ICMS</span><span class="money">${money(totalIcms)}</span></div>
      <div class="row"><span>IPI</span><span class="money">${money(totalIPI)}</span></div>
      <div class="row"><span>PIS</span><span class="money">${money(totalPIS)}</span></div>
      <div class="row"><span>COFINS</span><span class="money">${money(totalCOFINS)}</span></div>
      <div class="row total"><span>Total NF-e</span><span>${money(totalProd)}</span></div>`;
  }

  // ═══════════ PDF ═══════════
  function printPedido(doc) {
    if (!doc) return;
    const win = window.open("", "_blank");
    const lines = (doc.itens || []).map(it =>
      `<tr><td>${escapeHtml(it.produto_nome || it.produto_id)}</td><td>${it.quantidade || 0}</td><td>${escapeHtml(it.unidade || "UN")}</td><td class="money">${money(it.preco_unitario)}</td><td>${it.desconto || 0}%</td><td class="money">${money(it.subtotal)}</td></tr>`
    ).join("");
    win.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Pedido ${escapeHtml(doc.numero || doc.id)}</title>
      <style>body{font-family:Arial,sans-serif;font-size:13px;color:#111;padding:30px;max-width:800px;margin:0 auto}
      h1{font-size:18px;margin:0 0 4px}h2{font-size:14px;margin:16px 0 8px;color:#333}
      .header{display:flex;justify-content:space-between;border-bottom:2px solid #111;padding-bottom:12px;margin-bottom:16px}
      .header .emitente{font-size:12px;color:#555}
      table{width:100%;border-collapse:collapse;margin:8px 0}th,td{padding:6px 8px;border:1px solid #ddd;text-align:left;font-size:12px}
      th{background:#f5f5f5;font-weight:700}.money{text-align:right;font-variant-numeric:tabular-nums}
      .totals{margin-left:auto;width:280px}.totals .row{display:flex;justify-content:space-between;padding:3px 0;font-size:13px}
      .totals .row.total{border-top:2px solid #111;margin-top:4px;padding-top:6px;font-weight:700;font-size:15px}
      .footer{margin-top:24px;border-top:1px solid #ccc;padding-top:12px;font-size:11px;color:#666}
      @media print{body{padding:15px}}</style></head><body>
      <div class="header"><div><h1>Pedido de Venda</h1><div class="emitente">BECRP — Vendas Corporativas</div></div>
      <div style="text-align:right"><strong>${escapeHtml(doc.numero || doc.id)}</strong><br>Data: ${escapeHtml(doc.data || "—")}<br>Status: ${escapeHtml(doc.status || "—")}</div></div>
      <h2>Cliente</h2>
      <p><strong>${escapeHtml(doc.razao_social || doc.cliente || "—")}</strong><br>
      CNPJ: ${escapeHtml(doc.cnpj || "—")}<br>
      ${doc.endereco_cobranca ? "Endereço: " + escapeHtml(doc.endereco_cobranca) : ""}</p>
      <h2>Itens</h2>
      <table><thead><tr><th>Produto</th><th>Qtd</th><th>Un.</th><th>Preço Unit.</th><th>Desc.</th><th>Subtotal</th></tr></thead>
      <tbody>${lines}</tbody></table>
      <div class="totals">
        <div class="row"><span>Subtotal</span><span class="money">${money(doc.subtotal)}</span></div>
        <div class="row"><span>Descontos</span><span class="money">${money(doc.descontos)}</span></div>
        <div class="row"><span>Impostos</span><span class="money">${money(doc.impostos)}</span></div>
        <div class="row total"><span>TOTAL</span><span class="money">${money(doc.total)}</span></div>
      </div>
      ${doc.notas ? "<h2>Notas</h2><p>" + escapeHtml(doc.notas) + "</p>" : ""}
      <div class="footer">Documento gerado automaticamente pelo BECRP — ${new Date().toLocaleString("pt-BR")}</div>
      </body></html>`);
    win.document.close();
    setTimeout(() => win.print(), 300);
  }

  function printFatura(fatura) {
    if (!fatura) return;
    const win = window.open("", "_blank");
    const lines = (fatura.itens || []).map(it =>
      `<tr><td>${escapeHtml(it.produto_nome || it.produto_id)}</td><td>${it.quantidade || 0}</td><td>${escapeHtml(it.unidade || "UN")}</td><td class="money">${money(it.valor_unitario)}</td><td class="money">${money(it.valor_total)}</td></tr>`
    ).join("");
    win.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Fatura ${escapeHtml(fatura.numero || fatura.id)}</title>
      <style>body{font-family:Arial,sans-serif;font-size:13px;color:#111;padding:30px;max-width:800px;margin:0 auto}
      h1{font-size:18px;margin:0 0 4px}h2{font-size:14px;margin:16px 0 8px;color:#333}
      .header{display:flex;justify-content:space-between;border-bottom:2px solid #111;padding-bottom:12px;margin-bottom:16px}
      .header .emitente{font-size:12px;color:#555}
      table{width:100%;border-collapse:collapse;margin:8px 0}th,td{padding:6px 8px;border:1px solid #ddd;text-align:left;font-size:12px}
      th{background:#f5f5f5;font-weight:700}.money{text-align:right;font-variant-numeric:tabular-nums}
      .totals{margin-left:auto;width:280px}.totals .row{display:flex;justify-content:space-between;padding:3px 0;font-size:13px}
      .totals .row.total{border-top:2px solid #111;margin-top:4px;padding-top:6px;font-weight:700;font-size:15px}
      .footer{margin-top:24px;border-top:1px solid #ccc;padding-top:12px;font-size:11px;color:#666}
      @media print{body{padding:15px}}</style></head><body>
      <div class="header"><div><h1>Fatura de Venda</h1><div class="emitente">BECRP — Vendas Corporativas</div></div>
      <div style="text-align:right"><strong>${escapeHtml(fatura.numero || fatura.id)}</strong><br>Emissão: ${escapeHtml(fatura.emissao || "—")}<br>Vencimento: ${escapeHtml(fatura.vencimento || "—")}</div></div>
      <h2>Cliente</h2>
      <p><strong>${escapeHtml(fatura.cliente || "—")}</strong><br>CNPJ: ${escapeHtml(fatura.cnpj || "—")}</p>
      <h2>Itens</h2>
      <table><thead><tr><th>Produto</th><th>Qtd</th><th>Un.</th><th>Vl. Unit.</th><th>Vl. Total</th></tr></thead>
      <tbody>${lines}</tbody></table>
      <div class="totals">
        <div class="row"><span>Subtotal</span><span class="money">${money(fatura.subtotal)}</span></div>
        <div class="row"><span>Impostos</span><span class="money">${money(fatura.impostos)}</span></div>
        <div class="row total"><span>TOTAL</span><span class="money">${money(fatura.total)}</span></div>
      </div>
      <div class="footer">Documento gerado automaticamente pelo BECRP — ${new Date().toLocaleString("pt-BR")}</div>
      </body></html>`);
    win.document.close();
    setTimeout(() => win.print(), 300);
  }

  const KANBAN_STATUS = ["rascunho", "pendente", "aprovado", "faturado", "bloqueado", "cancelado"];
  const STATUS_DOT = {
    rascunho: "#94a3b8", pendente: "#eab308", aprovado: "#3b82f6",
    faturado: "#22c55e", bloqueado: "#94a3b8", cancelado: "#ef4444",
  };
  let kanbanDrag = null;

  function kanbanFiltroTipo(list) {
    const t = document.getElementById("kanban-tipo").value;
    if (!t) return list;
    return list.filter((p) => p.tipo === t || (t === "pedido" && !p.tipo));
  }

  function renderKanban() {
    const board = document.getElementById("kanban-board");
    const list = kanbanFiltroTipo(pedidos);
    const porStatus = {};
    KANBAN_STATUS.forEach((s) => porStatus[s] = []);
    list.forEach((p) => { (porStatus[p.status] || porStatus.rascunho).push(p); });
    board.innerHTML = KANBAN_STATUS.map((s) => {
      const items = porStatus[s];
      return `<div class="kanban-col" data-kanban-status="${s}">
        <div class="kanban-head">
          <span class="kanban-dot" style="background:${STATUS_DOT[s]}"></span>
          <span>${STATUS_LABEL[s] || s}</span>
          <span class="kanban-count">${items.length}</span>
        </div>
        <div class="kanban-body">
          ${items.length ? items.map((p) => {
            const locked = isLocked(p);
            return `<div class="kanban-card" data-kanban-id="${p.id}" draggable="${locked ? "false" : "true"}">
              <div class="kcard-top"><strong>${escapeHtml(p.numero || "#" + p.id)}</strong>
                <span class="badge badge-${escapeHtml(p.status)}">${STATUS_LABEL[p.status] || p.status}</span></div>
              <div class="kcard-nome">${escapeHtml(p.razao_social || "—")}</div>
              <div class="kcard-sub">${escapeHtml(p.cnpj || "")} · ${escapeHtml(p.data || "—")} · ${escapeHtml(p.uf || "")}</div>
              <div class="kcard-total">${money(calcTotals(p).total)}</div>
            </div>`;
          }).join("") : '<div class="empty" style="padding:1rem;font-size:12px">Vazio</div>'}
        </div>
      </div>`;
    }).join("");

    board.querySelectorAll(".kanban-card").forEach((card) => {
      card.onclick = () => openForm(card.dataset.kanbanId);
      card.ondragstart = (e) => {
        const doc = pedidos.find((p) => String(p.id) === String(card.dataset.kanbanId));
        if (!doc || isLocked(doc)) { e.preventDefault(); return; }
        kanbanDrag = { id: card.dataset.kanbanId, status: doc.status };
        card.classList.add("kanban-dragging");
      };
      card.ondragend = () => {
        kanbanDrag = null;
        card.classList.remove("kanban-dragging");
        board.querySelectorAll(".kanban-col").forEach((c) => c.classList.remove("kanban-drop"));
      };
    });

    board.querySelectorAll(".kanban-col").forEach((col) => {
      col.ondragover = (e) => { e.preventDefault(); };
      col.ondragenter = () => {
        if (kanbanDrag && FLOW[kanbanDrag.status]?.includes(col.dataset.kanbanStatus)) {
          col.classList.add("kanban-drop");
        }
      };
      col.ondragleave = () => col.classList.remove("kanban-drop");
      col.ondrop = async (e) => {
        e.preventDefault();
        col.classList.remove("kanban-drop");
        if (!kanbanDrag) return;
        const destino = col.dataset.kanbanStatus;
        if (destino === kanbanDrag.status) { kanbanDrag = null; return; }
        if (!FLOW[kanbanDrag.status]?.includes(destino)) {
          alert(`Transição inválida: ${STATUS_LABEL[kanbanDrag.status]} → ${STATUS_LABEL[destino]}`);
          kanbanDrag = null;
          return;
        }
        const res = await saveDoc({ id: kanbanDrag.id, status: destino }, "status");
        kanbanDrag = null;
        if (res.status === "ok") { await refreshFromServer(); renderKanban(); }
        else alert(res.message || "Falha ao mover cartão");
      };
    });
  }

  let calCursor = (() => {
    const agora = new Date();
    return { y: agora.getFullYear(), m: agora.getMonth() };
  })();
  const MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
  const DOW = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"];

  function calFiltroTipo(list) {
    const t = document.getElementById("cal-tipo").value;
    if (!t) return list;
    return list.filter((p) => p.tipo === t || (t === "pedido" && !p.tipo));
  }

  function renderCalendario() {
    document.getElementById("cal-titulo").textContent = `${MESES[calCursor.m]} ${calCursor.y}`;
    const grid = document.getElementById("cal-grid");
    const list = calFiltroTipo(pedidos);
    const porData = {};
    list.forEach((p) => { (porData[p.data] = porData[p.data] || []).push(p); });

    const primeiro = new Date(calCursor.y, calCursor.m, 1);
    let offset = (primeiro.getDay() + 6) % 7; // semana começa segunda
    const hoje = new Date().toISOString().slice(0, 10);

    let html = DOW.map((d) => `<div class="cal-dow">${d}</div>`).join("");
    const inicia = new Date(calCursor.y, calCursor.m, 1 - offset);
    for (let i = 0; i < 42; i++) {
      const dt = new Date(inicia.getFullYear(), inicia.getMonth(), inicia.getDate() + i);
      const ymd = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`;
      const fora = dt.getMonth() !== calCursor.m;
      const docs = porData[ymd] || [];
      html += `<div class="cal-cell ${fora ? "cal-out" : ""} ${ymd === hoje ? "cal-hoje" : ""}">
        <div class="cal-num">${dt.getDate()}</div>
        <div class="cal-chips">${docs.slice(0, 4).map((p) =>
          `<span class="cal-chip badge badge-${escapeHtml(p.status)}" data-cal-id="${p.id}" title="${escapeHtml(p.numero)} · ${escapeHtml(p.razao_social || "")}">${escapeHtml(p.numero || "#" + p.id)}</span>`).join("")}
          ${docs.length > 4 ? `<span class="cal-num">+${docs.length - 4} mais</span>` : ""}
        </div>
      </div>`;
    }
    grid.innerHTML = html;
    grid.querySelectorAll("[data-cal-id]").forEach((chip) => {
      chip.onclick = () => openForm(chip.dataset.calId);
    });
  }

  function renderPivot() {
    const out = document.getElementById("pv-out");
    const linhaKey = document.getElementById("pv-linha").value;
    const colunaKey = document.getElementById("pv-coluna").value;
    const valorKey = document.getElementById("pv-valor").value;

    const linhaVal = (p) => ({
      vendedor: p.vendedor || "—",
      cliente: p.razao_social || "—",
      uf: p.uf || "—",
      tipo: p.tipo === "cotacao" ? "Cotação" : "Pedido",
    }[linhaKey]);
    const colunaVal = (p) => ({
      status: STATUS_LABEL[p.status] || p.status || "Pendente",
      mes: (p.data || "").slice(0, 7),
      tipo: p.tipo === "cotacao" ? "Cotação" : "Pedido",
    }[colunaKey]);
    const valor = (p) => {
      if (valorKey === "total") return calcTotals(p).total;
      if (valorKey === "qtd") return (p.itens || []).reduce((s, i) => s + (Number(i.qtd) || 0), 0);
      return 1;
    };

    const linhas = new Map(), colunas = new Map();
    const cel = (l, c) => ({ n: 0, v: 0 });
    pedidos.forEach((p) => {
      const l = linhaVal(p), c = colunaVal(p);
      if (!linhas.has(l)) linhas.set(l, new Map());
      if (!colunas.has(c)) colunas.set(c, cel());
      if (!linhas.get(l).has(c)) linhas.get(l).set(c, cel());
      const cell = linhas.get(l).get(c);
      cell.n += 1; cell.v += valor(p);
      colunas.get(c).n += 1; colunas.get(c).v += valor(p);
    });

    const fmt = valorKey === "total" ? money : (n) => String(Math.round(n * 100) / 100);
    const linhaTotais = new Map();
    linhas.forEach((celMap, l) => {
      let n = 0, v = 0;
      celMap.forEach((cell) => { n += cell.n; v += cell.v; });
      linhaTotais.set(l, { n, v });
    });

    const cols = [...colunas.keys()].sort();
    let html = `<div class="pivot-wrap"><table class="pivot">
      <thead><tr>
        <th class="corner">${document.getElementById("pv-linha").selectedOptions[0].textContent} \\ ${document.getElementById("pv-coluna").selectedOptions[0].textContent}</th>
        ${cols.map((c) => `<th>${escapeHtml(c)}</th>`).join("")}
        <th>Total</th>
      </tr></thead><tbody>`;
    const order = [...linhas.keys()].sort((a, b) => linhaTotais.get(b).v - linhaTotais.get(a).v);
    order.forEach((l) => {
      const lt = linhaTotais.get(l);
      html += `<tr>
        <td class="row-head">${escapeHtml(l)}</td>
        ${cols.map((c) => {
          const cell = linhas.get(l).get(c);
          return `<td>${cell ? fmt(cell.v) : "—"}</td>`;
        }).join("")}
        <td class="col-total">${fmt(lt.v)}</td>
      </tr>`;
    });
    let totN = 0, totV = 0;
    colunas.forEach((c) => { totN += c.n; totV += c.v; });
    html += `<tr class="totais">
      <td class="row-head">Total</td>
      ${cols.map((c) => `<td>${fmt(colunas.get(c).v)}</td>`).join("")}
      <td>${fmt(totV)}</td>
    </tr></tbody></table></div>`;
    out.innerHTML = html || '<div class="empty">Sem dados</div>';
  }

  function renderCatalogo() {
    const busca = (document.getElementById("cat-busca").value || "").trim().toLowerCase();
    const cat = document.getElementById("cat-categoria").value;
    const listaId = document.getElementById("cat-lista").value;
    const lista = priceLists.find((l) => String(l.id) === String(listaId)) || null;
    const produtos = catalogProdutos.length ? catalogProdutos : produtosDl;

    const cats = [...new Set(produtos.map((p) => p.categoria || p.category || "Sem categoria"))].sort();
    const catSel = document.getElementById("cat-categoria");
    if (catSel.options.length <= 1) {
      catSel.innerHTML = '<option value="">Todas</option>' +
        cats.map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("");
    }
    const listaSel = document.getElementById("cat-lista");
    if (listaSel.options.length <= 1) {
      listaSel.innerHTML = '<option value="">Preço base</option>' +
        priceLists.map((l) => `<option value="${escapeHtml(l.id)}">${escapeHtml(l.name)}</option>`).join("");
    }

    const filtered = produtos.filter((p) => {
      if (cat && (p.categoria || p.category || "Sem categoria") !== cat) return false;
      if (!busca) return true;
      const blob = [p.nome, p.name, p.codigo_barras, p.ncm, String(p.id)].join(" ").toLowerCase();
      return blob.includes(busca);
    });

    const tbody = document.getElementById("cat-tbody");
    if (!filtered.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="empty">Nenhum produto encontrado</td></tr>';
      document.getElementById("cat-note").textContent = "";
      return;
    }
    tbody.innerHTML = filtered.map((p) => {
      const pid = String(p.id);
      const nome = p.nome || p.name || "#" + pid;
      const precoBase = Number(p.preco) || 0;
      const precoLista = (lista && lista.items && pid in lista.items) ? Number(lista.items[pid]) : null;
      const estoque = p.stock != null ? p.stock : (p.qtd_estoque != null ? p.qtd_estoque : "—");
      return `<tr data-prod="${pid}">
        <td><span class="badge">#${escapeHtml(pid)}</span></td>
        <td><strong>${escapeHtml(nome)}</strong>
          <span class="cnpj" style="display:block">${escapeHtml(p.codigo_barras || "")}${p.ncm ? " · NCM " + escapeHtml(p.ncm) : ""}</span></td>
        <td>${escapeHtml(p.categoria || p.category || "—")}</td>
        <td>${escapeHtml(p.unidade || p.uom || "UN")}</td>
        <td>${estoque}</td>
        <td class="money">${money(precoBase)}</td>
        <td class="money">${precoLista != null ? money(precoLista) : '<span class="muted">= base</span>'}</td>
        <td><a class="so-btn ghost" style="padding:4px 10px;font-size:12px" href="produtos.html?id=${pid}&retorno=${encodeURIComponent('/pages/vendas.html#catalogo')}">Abrir</a></td>
      </tr>`;
    }).join("");
    tbody.querySelectorAll("tr[data-prod]").forEach((tr) => {
      tr.style.cursor = "pointer";
      tr.addEventListener("click", () => location.href = `produtos.html?id=${tr.dataset.prod}&retorno=${encodeURIComponent("/pages/vendas.html#catalogo")}`);
    });
    document.getElementById("cat-note").textContent =
      `${filtered.length} de ${produtos.length} produto(s) · ${lista ? "listando preço por: " + lista.name : "sem lista de preço aplicada"}`;
  }

  function rptOptions() {
    const v = document.getElementById("rpt-vendedor");
    const u = document.getElementById("rpt-uf");
    if (v.options.length > 1 && u.options.length > 1) return;
    const vends = new Set(), ufs = new Set();
    pedidos.forEach((p) => { if (p.vendedor) vends.add(p.vendedor); if (p.uf) ufs.add(p.uf); });
    const curV = v.value, curU = u.value;
    v.innerHTML = '<option value="">Todos</option>' +
      [...vends].sort().map((x) => `<option value="${escapeHtml(x)}">${escapeHtml(x)}</option>`).join("");
    u.innerHTML = '<option value="">Todas</option>' +
      [...ufs].sort().map((x) => `<option value="${escapeHtml(x)}">${escapeHtml(x)}</option>`).join("");
    v.value = curV; u.value = curU;
  }

  function rptTable(title, headers, rows, empty) {
    const head = `<thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>`;
    if (!rows.length) {
      return `<div class="dashboard-widget widget-md"><div class="widget-header"><span class="widget-title">${title}</span></div><div class="empty">${empty}</div></div>`;
    }
    return `<div class="dashboard-widget widget-md"><div class="widget-header"><span class="widget-title">${title}</span></div>
      <div class="table-wrap"><table class="data">${head}<tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table></div></div>`;
  }

  function renderRelatorio() {
    rptOptions();
    const de = document.getElementById("rpt-de").value;
    const ate = document.getElementById("rpt-ate").value;
    const tipo = document.getElementById("rpt-tipo").value;
    const status = document.getElementById("rpt-status").value;
    const vendedor = document.getElementById("rpt-vendedor").value;
    const uf = document.getElementById("rpt-uf").value;

    const base = pedidos.filter((p) => {
      if (tipo && p.tipo !== tipo && !(tipo === "pedido" && !p.tipo)) return false;
      if (status && p.status !== status) return false;
      if (vendedor && p.vendedor !== vendedor) return false;
      if (uf && p.uf !== uf) return false;
      if (de && (p.data || "") < de) return false;
      if (ate && (p.data || "") > ate) return false;
      return true;
    });

    const t = (d) => calcTotals(d);
    const receita = base.reduce((s, p) => s + t(p).total, 0);
    const impostos = base.reduce((s, p) => s + t(p).impostos, 0);
    const n = base.length;
    const ticket = n ? receita / n : 0;

    const porStatus = {}, porVendedor = {}, porUf = {}, prodAgg = {};
    base.forEach((p) => {
      const st = p.status || "pendente";
      porStatus[st] = porStatus[st] || { n: 0, total: 0 };
      porStatus[st].n += 1; porStatus[st].total += t(p).total;
      const vd = p.vendedor || "—";
      porVendedor[vd] = porVendedor[vd] || { n: 0, total: 0 };
      porVendedor[vd].n += 1; porVendedor[vd].total += t(p).total;
      const u = p.uf || "—";
      porUf[u] = porUf[u] || { n: 0, total: 0 };
      porUf[u].n += 1; porUf[u].total += t(p).total;
      (p.itens || []).forEach((i) => {
        const nome = i.produto || i.prod_id || "—";
        prodAgg[nome] = prodAgg[nome] || { qtd: 0, total: 0 };
        prodAgg[nome].qtd += Number(i.qtd) || 0;
        prodAgg[nome].total += calcLine(i);
      });
    });

    const porMes = {};
    base.forEach((p) => {
      const m = (p.data || "").slice(0, 7) || "—";
      porMes[m] = (porMes[m] || 0) + t(p).total;
    });
    const mesKeys = Object.keys(porMes).sort();
    const maxMes = Math.max(...mesKeys.map((k) => porMes[k]), 1);
    const maxSt = Math.max(...Object.entries(porStatus).map(([, v]) => v.total), 1);

    const chart = (title, keys, getVal, max) => `
      <div class="dashboard-widget widget-md">
        <div class="widget-header"><span class="widget-title">${title}</span></div>
        <div class="chart-bars">
          ${keys.map((k) => `
            <div class="chart-bar-col">
              <div class="chart-bar" style="height:${(getVal(k) / max) * 100}%">
                <span class="chart-bar-value">${money(getVal(k))}</span>
              </div>
              <span class="chart-bar-label">${escapeHtml(String(k))}</span>
            </div>`).join("")}
        </div>
      </div>`;

    const kpi = (label, value, color) => `
      <div class="kpi-card kpi-${color}">
        <div class="kpi-header"><span class="kpi-label-ico"></span></div>
        <div class="kpi-value">${value}</div>
        <div class="kpi-label">${label}</div>
      </div>`;
    const html = `
      <div class="dashboard-kpis" style="margin-top:16px">
        ${kpi("Receita (filtro)", money(receita), "primary")}
        ${kpi("Documentos", String(n), "info")}
        ${kpi("Ticket médio", money(ticket), "success")}
        ${kpi("Impostos", money(impostos), "warning")}
      </div>
      <div class="dashboard-widgets">
        ${chart("Receita por status", Object.keys(porStatus), (k) => porStatus[k].total, maxSt)}
        ${chart("Receita por mês", mesKeys, (k) => porMes[k], maxMes)}
        ${rptTable("Por status", ["Status", "Nº", "Total"], Object.entries(porStatus).map(([k, v]) => [STATUS_LABEL[k] || k, String(v.n), money(v.total)]), "Sem dados")}
        ${rptTable("Por vendedor", ["Vendedor", "Nº", "Total"], Object.entries(porVendedor).sort((a, b) => b[1].total - a[1].total).map(([k, v]) => [escapeHtml(k), String(v.n), money(v.total)]), "Sem dados")}
        ${rptTable("Por UF", ["UF", "Nº", "Total"], Object.entries(porUf).map(([k, v]) => [escapeHtml(k), String(v.n), money(v.total)]), "Sem dados")}
        ${rptTable("Top produtos", ["Produto", "Qtd", "Total"], Object.entries(prodAgg).sort((a, b) => b[1].total - a[1].total).slice(0, 10).map(([k, v]) => [escapeHtml(k), String(v.qtd), money(v.total)]), "Sem dados")}
      </div>`;
    document.getElementById("rpt-resultados").innerHTML = html;
    const meta = [];
    if (de) meta.push("De " + de);
    if (ate) meta.push("Até " + ate);
    if (tipo) meta.push(tipo === "cotacao" ? "Cotações" : "Pedidos");
    if (status) meta.push(STATUS_LABEL[status] || status);
    if (vendedor) meta.push("Vendedor: " + vendedor);
    if (uf) meta.push("UF: " + uf);
    meta.push(n + " documento(s)");
    const metaEl = document.getElementById("rpt-print-meta");
    if (metaEl) metaEl.textContent = meta.join(" · ");
  }

  document.querySelectorAll(".so-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".so-tab").forEach((t) => t.classList.toggle("active", t === tab));
      document.querySelectorAll(".so-pane").forEach((p) => {
        p.classList.toggle("active", p.id === "pane-" + tab.dataset.pane);
      });
    });
  });

  document.getElementById("btn-back-list").addEventListener("click", () => {
    showView(listReturn);
  });

  function renderList(list) {
    const tbody = document.getElementById("vendas-tbody");
    const onlyPedidos = list.filter((v) => v.tipo !== "cotacao");
    if (!onlyPedidos.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty">Nenhum pedido corporativo (CNPJ) encontrado</td></tr>';
      return;
    }
    tbody.innerHTML = onlyPedidos.map((v) => {
      const st = v.status || "pendente";
      const tot = calcTotals(v).total;
      return `<tr data-id="${v.id}">
        <td><span class="badge">${escapeHtml(v.numero || "#" + v.id)}</span></td>
        <td>${v.data || "—"}</td>
        <td><div class="empresa-cell"><strong>${escapeHtml(v.razao_social || "—")}</strong><span class="cnpj">${escapeHtml(v.cnpj || "—")}</span></div></td>
        <td>${escapeHtml(v.uf || "—")}</td>
        <td>${escapeHtml(v.condicao_pg || v.forma_pg || "—")}</td>
        <td><span class="badge badge-${escapeHtml(st)}">${STATUS_LABEL[st] || st}</span></td>
        <td class="money">${money(tot)}</td>
      </tr>`;
    }).join("");
    tbody.querySelectorAll("tr[data-id]").forEach((tr) => {
      tr.addEventListener("click", () => openForm(tr.dataset.id));
    });
  }

  function renderCotacoes() {
    const tbody = document.getElementById("cotacoes-tbody");
    const list = pedidos.filter((v) => v.tipo === "cotacao");
    if (!list.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty">Nenhuma cotação encontrada</td></tr>';
      return;
    }
    tbody.innerHTML = list.map((v) => {
      const st = v.status || "pendente";
      const tot = calcTotals(v).total;
      return `<tr data-id="${v.id}">
        <td><span class="badge">${escapeHtml(v.numero || "#" + v.id)}</span></td>
        <td>${v.data || "—"}</td>
        <td>${v.validade || "—"}</td>
        <td><div class="empresa-cell"><strong>${escapeHtml(v.razao_social || "—")}</strong><span class="cnpj">${escapeHtml(v.cnpj || "—")}</span></div></td>
        <td><span class="badge badge-${escapeHtml(st)}">${STATUS_LABEL[st] || st}</span></td>
        <td class="money">${money(tot)}</td>
      </tr>`;
    }).join("");
    tbody.querySelectorAll("tr[data-id]").forEach((tr) => {
      tr.addEventListener("click", () => openForm(tr.dataset.id));
    });
  }

  function applyFilter() {
    const q = (document.getElementById("search").value || "").trim().toLowerCase();
    const qDigits = onlyDigits(q);
    const base = pedidos.filter((v) => v.tipo !== "cotacao");
    const filtered = !q ? base : base.filter((v) => {
      const blob = [v.razao_social, v.cnpj, v.uf, v.cidade, v.condicao_pg, v.status, v.numero, v.id].join(" ").toLowerCase();
      return blob.includes(q) || (qDigits && onlyDigits(v.cnpj).includes(qDigits));
    });
    renderList(filtered);
  }
  function renderDashboard() {
    const total = pedidos.reduce((s, p) => s + calcTotals(p).total, 0);
    const pendentes = pedidos.filter((p) => p.status === "pendente").length;
    const faturados = pedidos.filter((p) => p.status === "faturado").length;
    const empresas = new Set(pedidos.map((p) => onlyDigits(p.cnpj))).size;

    document.getElementById("dash-kpis").innerHTML = [
      { label: "Volume negociado", value: money(total), icon: "icon-dollar", color: "primary", change: "+12%" },
      { label: "Pedidos pendentes", value: String(pendentes), icon: "icon-file-text", color: "warning", change: pendentes ? "atenção" : "ok" },
      { label: "Pedidos faturados", value: String(faturados), icon: "icon-printer", color: "success", change: "+8%" },
      { label: "Empresas (CNPJ)", value: String(empresas), icon: "icon-building", color: "info", change: String(empresas) },
    ].map((k) => `
      <div class="kpi-card kpi-${k.color}">
        <div class="kpi-header">
          <span class="kpi-icon"><svg class="icon icon-lg"><use href="${I}#${k.icon}"/></svg></span>
          <span class="kpi-change">${k.change}</span>
        </div>
        <div class="kpi-value">${k.value}</div>
        <div class="kpi-label">${k.label}</div>
      </div>`).join("");

    const recent = [...pedidos].sort((a, b) => String(b.data).localeCompare(String(a.data))).slice(0, 5);
    const maxBar = Math.max(...pedidos.map((p) => calcTotals(p).total), 1);

    document.getElementById("dash-widgets").innerHTML = `
      <div class="dashboard-widget widget-md">
        <div class="widget-header">
          <svg class="icon icon-md"><use href="${I}#icon-plus"/></svg>
          <span class="widget-title">Ações rápidas</span>
        </div>
        <div class="quick-actions-grid">
          <a class="quick-action-btn" href="#pedidos" data-go="pedidos"><svg class="icon"><use href="${I}#icon-dollar"/></svg><span>Pedidos de Venda</span></a>
          <a class="quick-action-btn" href="#cotacoes" data-go="cotacoes"><svg class="icon"><use href="${I}#icon-file-text"/></svg><span>Cotações</span></a>
          <a class="quick-action-btn" href="parceiros.html?role=CUSTOMER"><svg class="icon"><use href="${I}#icon-users"/></svg><span>Clientes</span></a>
          <a class="quick-action-btn" href="produtos.html"><svg class="icon"><use href="${I}#icon-box"/></svg><span>Produtos</span></a>
          <a class="quick-action-btn" href="produtos.html?novo=1&retorno=${encodeURIComponent('/pages/vendas.html#dashboard')}"><svg class="icon"><use href="${I}#icon-plus"/></svg><span>Novo produto</span></a>
        </div>
      </div>
      <div class="dashboard-widget widget-md">
        <div class="widget-header">
          <svg class="icon icon-md"><use href="${I}#icon-clock"/></svg>
          <span class="widget-title">Atividade recente</span>
        </div>
        <div class="activity-list">
          ${recent.length ? recent.map((p) => `
            <div class="activity-item">
              <span class="activity-dot activity-${p.status === "pendente" ? "warning" : p.status === "faturado" ? "success" : "info"}"></span>
              <div class="activity-content">
                <span class="activity-text">${escapeHtml(p.numero || "#" + p.id)} · ${escapeHtml(p.razao_social || "")}</span>
                <span class="activity-time">${escapeHtml(p.data || "")} · ${STATUS_LABEL[p.status] || p.status} · ${money(calcTotals(p).total)}</span>
              </div>
            </div>`).join("") : '<div class="empty">Sem atividade</div>'}
        </div>
      </div>
      <div class="dashboard-widget widget-lg">
        <div class="widget-header">
          <svg class="icon icon-md"><use href="${I}#icon-dollar"/></svg>
          <span class="widget-title">Volume por pedido</span>
        </div>
        <div class="chart-bars">
          ${pedidos.map((p) => `
            <div class="chart-bar-col">
              <div class="chart-bar" style="height:${(calcTotals(p).total / maxBar) * 100}%">
                <span class="chart-bar-value">${money(calcTotals(p).total)}</span>
              </div>
              <span class="chart-bar-label">${escapeHtml(p.numero || "#" + p.id)}</span>
            </div>`).join("")}
        </div>
      </div>`;

    document.querySelectorAll("[data-go]").forEach((el) => {
      el.addEventListener("click", (e) => {
        e.preventDefault();
        const link = document.querySelector(`#vendas-nav [data-nav="${el.dataset.go}"]`);
        showView(el.dataset.go, {
          soon: link?.dataset.soon === "1",
          label: link?.dataset.label || el.textContent.trim(),
          section: link?.dataset.section || "Pedidos",
        });
      });
    });
  }

  async function load() {
    const ok = await refreshFromServer();
    if (!ok) {
      document.getElementById("dash-kpis").innerHTML =
        '<div class="empty" style="color:#fca5a5">Erro ao carregar dashboard B2B</div>';
    }
  }

  const initial = (location.hash || "#dashboard").slice(1);
  renderNav();
  document.getElementById("search").addEventListener("input", applyFilter);
  document.getElementById("btn-refresh").addEventListener("click", () => { loadCatalogo(); load(); });
  document.getElementById("btn-refresh-cotacoes").addEventListener("click", () => {
    load().then(() => renderCotacoes());
  });
  document.getElementById("btn-refresh-faturas").addEventListener("click", renderFaturas);
  document.getElementById("btn-refresh-contratos").addEventListener("click", renderContratos);
  document.getElementById("btn-novo-contrato").addEventListener("click", showNovoContratoForm);
  document.getElementById("ct-q").addEventListener("keydown", (e) => {
    if (e.key === "Enter") renderContratos();
  });
  document.getElementById("ct-status").addEventListener("change", renderContratos);
  document.getElementById("btn-refresh-ar").addEventListener("click", renderReceber);
  document.getElementById("ar-q").addEventListener("keydown", (e) => {
    if (e.key === "Enter") renderReceber();
  });
  document.getElementById("ar-status").addEventListener("change", renderReceber);  document.getElementById("btn-rpt-filtrar").addEventListener("click", renderRelatorio);
  document.getElementById("btn-rpt-imprimir").addEventListener("click", () => {
    renderRelatorio();
    window.print();
  });
  document.getElementById("btn-rpt-limpar").addEventListener("click", () => {
    ["rpt-de", "rpt-ate", "rpt-tipo", "rpt-status", "rpt-vendedor", "rpt-uf"].forEach((id) => {
      document.getElementById(id).value = "";
    });
    renderRelatorio();
  });
  document.getElementById("btn-novo-pedido").addEventListener("click", () => createNew("pedido"));
  document.getElementById("btn-nova-cotacao").addEventListener("click", () => createNew("cotacao"));
  document.getElementById("btn-refresh-kanban").addEventListener("click", load);
  document.getElementById("kanban-tipo").addEventListener("change", renderKanban);
  document.getElementById("cal-prev").addEventListener("click", () => {
    calCursor.m--; if (calCursor.m < 0) { calCursor.m = 11; calCursor.y--; }
    renderCalendario();
  });
  document.getElementById("cal-next").addEventListener("click", () => {
    calCursor.m++; if (calCursor.m > 11) { calCursor.m = 0; calCursor.y++; }
    renderCalendario();
  });
  document.getElementById("cal-hoje").addEventListener("click", () => {
    const a = new Date();
    calCursor = { y: a.getFullYear(), m: a.getMonth() };
    renderCalendario();
  });
  document.getElementById("cal-tipo").addEventListener("change", renderCalendario);
  document.getElementById("btn-pv-aplicar").addEventListener("click", renderPivot);
  ["pv-linha", "pv-coluna", "pv-valor"].forEach((id) => {
    document.getElementById(id).addEventListener("change", renderPivot);
  });
  document.getElementById("btn-refresh-catalogo").addEventListener("click", () => { loadCatalogo(); renderCatalogo(); });
  document.getElementById("cat-busca").addEventListener("input", renderCatalogo);
  document.getElementById("cat-categoria").addEventListener("change", renderCatalogo);
  document.getElementById("cat-lista").addEventListener("change", renderCatalogo);

  // Entregas
  document.getElementById("btn-refresh-entregas").addEventListener("click", renderEntregas);
  document.getElementById("ent-q").addEventListener("keydown", (e) => { if (e.key === "Enter") renderEntregas(); });
  document.getElementById("ent-status").addEventListener("change", renderEntregas);
  document.getElementById("btn-back-entregas")?.addEventListener("click", () => showView("entregas"));

  // NF-e
  document.getElementById("btn-refresh-nfe").addEventListener("click", renderNfe);
  document.getElementById("nfe-q").addEventListener("keydown", (e) => { if (e.key === "Enter") renderNfe(); });
  document.getElementById("nfe-status").addEventListener("change", renderNfe);
  document.getElementById("btn-nova-nfe").addEventListener("click", () => openNfeForm(null));
  document.getElementById("btn-back-nfe")?.addEventListener("click", () => showView("nfe"));

  // NF-e / Entrega tabs
  document.querySelectorAll(".so-tab[data-pane]").forEach(tab => {
    tab.addEventListener("click", () => {
      const parent = tab.closest(".view") || tab.closest(".so-card") || document;
      parent.querySelectorAll(".so-tab").forEach(t => t.classList.toggle("active", t === tab));
      parent.querySelectorAll(".so-pane").forEach(p => p.classList.toggle("active", p.id === "pane-" + tab.dataset.pane));
    });
  });

  loadProdutos();
  loadClientes();
  loadCatalogo();

  if (initial.startsWith("doc-")) {
    load().then(() => openForm(initial.replace("doc-", "")));
  } else {
    const link = document.querySelector(`#vendas-nav [data-nav="${initial}"]`);
    if (initial === "pedidos" || initial === "cotacoes" || initial === "dashboard" || link) {
      showView(initial, {
        soon: link?.dataset.soon === "1",
        label: link?.dataset.label || link?.querySelector(".menu-label")?.textContent,
        section: link?.dataset.section || "",
      });
    } else {
      showView("dashboard");
    }
    load();
  }

  // Expose to global scope for onclick handlers
  window.showView = showView;
  window.printPedido = printPedido;
  window.printFatura = printFatura;
})();
