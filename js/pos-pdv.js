/**
 * BECRP POS — Terminal PDV (vendedor)
 * Smart Panel, sessões, catálogo, pedido/orçamento.
 */
(function () {
  "use strict";

  const LS_FAV = "becrp-pos-favorites";
  const LS_RECENT = "becrp-pos-recent";
  const LS_STORE = "becrp-pos-store-mode";

  const STOCK_LABELS = {
    local: { short: "Na loja", cls: "stock-ok" },
    branch: { short: "Outra filial", cls: "stock-branch" },
    transit: { short: "Em trânsito", cls: "stock-transit" },
    none: { short: "Indisponível", cls: "stock-none" },
  };

  const STOCK_MESSAGES = {
    local: (p) =>
      `<strong>Tem nesta loja</strong><br>${p.stock} un. disponíveis na filial atual.`,
    branch: () =>
      `<strong>Tem na Filial Centro em ~2h</strong><br>Retirada ou transferência expressa.`,
    transit: () =>
      `<strong>Em trânsito — chega amanhã</strong><br>Previsão de recebimento: amanhã, período da manhã.`,
    none: () =>
      `<strong>Sem previsão — ver similares</strong><br>Produto indisponível. Sugestão: item equivalente da mesma categoria.`,
  };

  const MOCK_CUSTOMERS = [
    {
      id: "cf",
      nome: "Consumidor final",
      av: "CF",
      cpf: "",
      telefone: "",
      hint: "Venda sem identificação",
      crediario: 0,
      ultimaCompra: null,
    },
    {
      id: "joao",
      nome: "João da Silva",
      av: "JS",
      cpf: "123.456.789-00",
      telefone: "(11) 98765-4321",
      hint: "",
      crediario: 340.5,
      ultimaCompra: "15/07/2026 · R$ 89,90",
    },
    {
      id: "ana",
      nome: "Ana Compras",
      av: "AC",
      cpf: "987.654.321-00",
      telefone: "(11) 91234-5678",
      hint: "",
      crediario: 0,
      ultimaCompra: "28/07/2026 · R$ 186,40",
    },
    {
      id: "sul",
      nome: "Sul Alimentos Ltda",
      av: "SA",
      cpf: "12.345.678/0001-90",
      telefone: "(11) 3333-4444",
      hint: "",
      crediario: 1240,
      ultimaCompra: "20/07/2026 · R$ 1.240,00",
    },
    {
      id: "maria",
      nome: "Maria Santos",
      av: "MS",
      cpf: "456.789.123-00",
      telefone: "(11) 99876-5432",
      hint: "",
      crediario: 85,
      ultimaCompra: "29/07/2026 · R$ 42,00",
    },
  ];

  const FALLBACK_FOTO = "../assets/images/sem-foto.png";

  const SAMPLE = [
    { id: 1, nome: "Arroz 5kg", preco: 32.9, stock: 40, cat: "Mercearia", sku: "000001", storeModes: ["mercearia"], stockStatus: "local", foto: "../assets/images/pos/1.svg" },
    { id: 2, nome: "Feijão 1kg", preco: 8.5, stock: 55, cat: "Mercearia", sku: "000002", storeModes: ["mercearia"], stockStatus: "local", foto: "../assets/images/pos/2.svg" },
    { id: 3, nome: "Óleo Soja 900ml", preco: 7.9, stock: 30, cat: "Mercearia", sku: "000003", storeModes: ["mercearia"], stockStatus: "branch", foto: "../assets/images/pos/3.svg" },
    { id: 4, nome: "Café 500g", preco: 18.9, stock: 22, cat: "Mercearia", sku: "000004", storeModes: ["mercearia"], stockStatus: "local", foto: "../assets/images/pos/4.svg" },
    { id: 5, nome: "Leite 1L", preco: 5.49, stock: 80, cat: "Frios", sku: "000005", storeModes: ["mercearia"], stockStatus: "local", foto: "../assets/images/pos/5.svg" },
    { id: 6, nome: "Queijo Mussarela", preco: 42.0, stock: 12, cat: "Frios", sku: "000006", storeModes: ["mercearia"], stockStatus: "transit", foto: "../assets/images/pos/6.svg" },
    { id: 7, nome: "Detergente", preco: 2.99, stock: 60, cat: "Limpeza", sku: "000007", storeModes: ["mercearia"], stockStatus: "local", foto: "../assets/images/pos/7.svg" },
    { id: 8, nome: "Sabão em pó", preco: 24.5, stock: 18, cat: "Limpeza", sku: "000008", storeModes: ["mercearia"], stockStatus: "none", foto: "../assets/images/pos/8.svg" },
    { id: 9, nome: "Banana prata", preco: 6.9, stock: 25, cat: "Hortifrúti", sku: "000009", peso: true, storeModes: ["mercearia"], stockStatus: "local", foto: "../assets/images/pos/9.svg" },
    {
      id: 10,
      nome: "Camisa Polo",
      preco: 89.9,
      stock: 24,
      cat: "Moda",
      sku: "000010",
      storeModes: ["moda", "mercearia"],
      stockStatus: "local",
      foto: "../assets/images/pos/10.svg",
      variants: { cores: ["Branca", "Preta", "Azul"], tamanhos: ["P", "M", "G", "GG"] },
    },
    {
      id: 11,
      nome: "Consultoria 1h",
      preco: 150,
      stock: 999,
      cat: "Serviços",
      sku: "000011",
      servico: true,
      storeModes: ["servico"],
      stockStatus: "local",
      foto: "../assets/images/pos/11.svg",
    },
    {
      id: 12,
      nome: "Calça Jeans",
      preco: 129.9,
      stock: 8,
      cat: "Moda",
      sku: "000012",
      storeModes: ["moda"],
      stockStatus: "branch",
      foto: "../assets/images/pos/12.svg",
      variants: { cores: ["Azul escuro", "Preto"], tamanhos: ["38", "40", "42", "44"] },
    },
  ];

  let mode = "pdv";
  let cat = "";
  let catalogTab = "todos";
  let storeMode = localStorage.getItem(LS_STORE) || "mercearia";
  let favorites = loadJson(LS_FAV, []);
  let recentIds = loadJson(LS_RECENT, []);

  let sessions = [];
  let activeSessionId = null;
  let nextSessionNum = 1;
  let nextOrderNum = 1043;

  let undoStack = [];
  let pendingVariant = null;
  let variantPick = { cor: "", tamanho: "" };
  let longPressTimer = null;

  let caixaDue = 186.4;
  let cashReceived = 0;
  let queueTimers = {};
  let cashMoves = [];
  /** @type {null | { kind: 'in'|'out', cents: number, reason: string, docType: string, docRef: string }} */
  let cashMovePad = null;

  const CASH_REASONS = {
    in: ["Fundo de troco", "Reforço de caixa", "Troco de sangria", "Outro"],
    out: ["Depósito banco", "Pagamento fornecedor", "Vale funcionário", "Compra mercado", "Cofre", "Outro"],
  };

  /** @type {null | object} */
  let numpad = null;
  /** @type {null | object} */
  let adjPad = null;
  /** @type {null | object} */
  let parcPad = null;

  const SMART_NAMES = {
    summary: "Resumo do Pedido",
    customer: "Pesquisa de Clientes",
    discount: "Desconto",
    parcel: "Parcelamento",
    numpad: "Quantidade",
    text: "Observação",
    stock: "Estoque",
    variant: "Variação",
    payment: "Pagamento",
  };

  const SMART_CTX_IDS = ["summary", "customer", "discount", "parcel", "numpad", "text", "stock", "variant"];

  function loadJson(key, fallback) {
    try {
      const v = localStorage.getItem(key);
      return v ? JSON.parse(v) : fallback;
    } catch {
      return fallback;
    }
  }

  function saveJson(key, val) {
    localStorage.setItem(key, JSON.stringify(val));
  }

  const money = (v) =>
    "R$ " + (Number(v) || 0).toFixed(2).replace(".", ",").replace(/\B(?=(\d{3})+(?!\d))/g, ".");

  function parseNumpadRaw(raw, allowDecimal) {
    if (!raw || raw === ".") return 0;
    const n = allowDecimal ? parseFloat(raw) : parseInt(raw, 10);
    return Number.isFinite(n) ? n : 0;
  }

  function formatDisplay(raw, allowDecimal) {
    if (!raw) return allowDecimal ? "0,00" : "0";
    if (allowDecimal) {
      if (raw.includes(".")) {
        const [a, b = ""] = raw.split(".");
        return (a || "0") + "," + b.slice(0, 3);
      }
      return raw + ",00";
    }
    return raw;
  }

  function relTime(ts) {
    const diff = Date.now() - ts;
    const min = Math.floor(diff / 60000);
    if (min < 1) return "agora";
    if (min < 60) return "há " + min + " min";
    const h = Math.floor(min / 60);
    if (h < 24) return "há " + h + " h";
    return "há " + Math.floor(h / 24) + " d";
  }

  function defaultClient() {
    return { id: "cf", nome: "Consumidor final", av: "CF", hint: "Toque para buscar" };
  }

  function emptySessionState(num) {
    return {
      id: "s" + num,
      num,
      status: "active",
      lines: [],
      selectedLine: -1,
      client: defaultClient(),
      orderDisc: { type: "val", value: 0 },
      orderAcr: { type: "val", value: 0 },
      orderParc: null,
      orderType: "pedido",
      updatedAt: Date.now(),
      queueStatus: null,
    };
  }

  function getSession() {
    return sessions.find((s) => s.id === activeSessionId) || null;
  }

  function sessionSnapshot() {
    const s = getSession();
    if (!s) return null;
    return JSON.parse(JSON.stringify({
      lines: s.lines,
      selectedLine: s.selectedLine,
      client: s.client,
      orderDisc: s.orderDisc,
      orderAcr: s.orderAcr,
      orderParc: s.orderParc,
      orderType: s.orderType,
    }));
  }

  function pushUndo(label) {
    const snap = sessionSnapshot();
    if (!snap) return;
    undoStack.push({ label, snap });
    if (undoStack.length > 20) undoStack.shift();
    syncUndoBtn();
  }

  function syncUndoBtn() {
    const btn = document.getElementById("btn-undo");
    if (btn) btn.disabled = undoStack.length === 0;
  }

  function undoLast() {
    const entry = undoStack.pop();
    if (!entry) return;
    const s = getSession();
    if (!s) return;
    Object.assign(s, entry.snap);
    renderAll();
    document.getElementById("status-hint").textContent = "Desfeito: " + entry.label;
    syncUndoBtn();
  }

  function createSession() {
    const s = emptySessionState(nextSessionNum++);
    sessions.push(s);
    activeSessionId = s.id;
    undoStack = [];
    syncUndoBtn();
    renderSessions();
    renderAll();
    return s;
  }

  function switchSession(id) {
    const s = sessions.find((x) => x.id === id);
    if (!s) return;
    activeSessionId = id;
    if (s.status === "suspended") s.status = "active";
    undoStack = [];
    syncUndoBtn();
    closeNumpad();
    cancelAdjPad();
    cancelParcelPad();
    setSmartCtx("summary");
    renderSessions();
    renderAll();
  }

  function suspendCurrentSession() {
    const s = getSession();
    if (!s) return;
    if (!s.lines.length) {
      document.getElementById("status-hint").textContent = "Nada para suspender — adicione itens";
      return;
    }
    s.status = "suspended";
    s.updatedAt = Date.now();
    createSession();
    document.getElementById("status-hint").textContent = "Pedido suspenso — nova sessão iniciada";
  }

  function renderSessions() {
    const rail = document.getElementById("pos-sessions");
    if (!rail) return;
    const list = sessions
      .map((s) => {
        const n = s.lines.length;
        const total = sessionTotal(s);
        const isActive = s.id === activeSessionId;
        const statusLabel = s.status === "suspended" ? "susp." : "ativa";
        const clientShort =
          s.client.nome.length > 10 ? s.client.nome.slice(0, 9) + "…" : s.client.nome;
        return `
      <button type="button" class="ss-btn ${isActive ? "active" : ""} ${s.status === "suspended" ? "suspended" : ""}"
        data-session="${s.id}" title="${s.client.nome}">
        <strong class="ss-client">${clientShort}</strong>
        <span class="ss-meta">${n} it · ${money(total)}</span>
        <span class="ss-time">${relTime(s.updatedAt)}</span>
        <span class="ss-status">${statusLabel}</span>
        ${n > 0 && s.status === "suspended" ? `<span class="ss-badge">${n}</span>` : ""}
      </button>`;
      })
      .join("");
    rail.innerHTML =
      list +
      '<button type="button" class="ss-btn new" title="Nova venda" id="btn-new-session">+</button>';
    rail.querySelectorAll("[data-session]").forEach((btn) => {
      btn.addEventListener("click", () => switchSession(btn.dataset.session));
    });
    document.getElementById("btn-new-session").addEventListener("click", () => {
      createSession();
      document.getElementById("status-hint").textContent = "Nova sessão de venda";
    });
  }

  function sessionSubtotal(s) {
    return s.lines.reduce((sum, l) => sum + lineTotal(l), 0);
  }

  function sessionDiscAmount(s) {
    const sub = sessionSubtotal(s);
    if (s.orderDisc.type === "pct") return Math.min(sub, (sub * (s.orderDisc.value || 0)) / 100);
    return Math.min(sub, s.orderDisc.value || 0);
  }

  function sessionAcrAmount(s) {
    const sub = sessionSubtotal(s);
    if (s.orderAcr.type === "pct") return (sub * (s.orderAcr.value || 0)) / 100;
    return s.orderAcr.value || 0;
  }

  function sessionTotal(s) {
    return Math.max(0, sessionSubtotal(s) - sessionDiscAmount(s) + sessionAcrAmount(s));
  }

  function lineTotal(l) {
    return (Number(l.qtd) || 0) * (Number(l.preco) || 0);
  }

  function orderSubtotal() {
    const s = getSession();
    return s ? sessionSubtotal(s) : 0;
  }

  function orderDiscAmount() {
    const s = getSession();
    return s ? sessionDiscAmount(s) : 0;
  }

  function orderAcrAmount() {
    const s = getSession();
    return s ? sessionAcrAmount(s) : 0;
  }

  function orderTotal() {
    const s = getSession();
    return s ? sessionTotal(s) : 0;
  }

  function setSmartCtx(ctx, titleOverride) {
    const panel = document.getElementById("pos-smart");
    if (!SMART_CTX_IDS.includes(ctx)) ctx = "summary";
    panel.dataset.ctx = ctx;
    SMART_CTX_IDS.forEach((id) => {
      const el = document.getElementById("smart-ctx-" + id);
      if (el) el.hidden = id !== ctx;
    });
    document.getElementById("smart-ctx-name").textContent =
      titleOverride || SMART_NAMES[ctx] || ctx;
    panel.classList.toggle("tool-open", ctx !== "summary");
  }

  function setCaixaCtx(ctx) {
    const card = document.getElementById("caixa-receive");
    if (!card) return;
    card.dataset.ctx = ctx;
    document.getElementById("caixa-ctx-default").hidden = ctx !== "default";
    document.getElementById("caixa-ctx-numpad").hidden = ctx !== "numpad";
    const move = document.getElementById("caixa-ctx-cashmove");
    if (move) move.hidden = ctx !== "cashmove";
  }

  function syncCashMoveUI() {
    if (!cashMovePad) return;
    document.getElementById("cashmove-display").textContent = money((cashMovePad.cents || 0) / 100);
  }

  function openCashMove(kind) {
    setMode("caixa");
    if (numpad) closeNumpad();
    cashMovePad = { kind, cents: 0, reason: "", docType: "", docRef: "" };
    document.getElementById("cashmove-title").textContent =
      kind === "in" ? "Suprimento" : "Sangria";
    document.getElementById("cashmove-sub").textContent =
      kind === "in" ? "Entrada de dinheiro no caixa" : "Saída de dinheiro do caixa";
    const box = document.getElementById("cashmove-reasons");
    box.innerHTML = CASH_REASONS[kind]
      .map(
        (r) =>
          `<button type="button" class="phrase-chip" data-reason="${r}">${r}</button>`
      )
      .join("");
    document.getElementById("cashmove-reason-extra").value = "";
    document.getElementById("cashmove-doc-type").value = "";
    document.getElementById("cashmove-doc-ref").value = "";
    document.getElementById("cashmove-doc-ref").disabled = true;
    setCaixaCtx("cashmove");
    syncCashMoveUI();
  }

  function cashMoveKey(k) {
    if (!cashMovePad) return;
    if (k === "bk") cashMovePad.cents = Math.floor((cashMovePad.cents || 0) / 10);
    else if (k === "00") cashMovePad.cents = Math.min((cashMovePad.cents || 0) * 100, 999999999);
    else if (/^\d$/.test(k))
      cashMovePad.cents = Math.min((cashMovePad.cents || 0) * 10 + Number(k), 999999999);
    syncCashMoveUI();
  }

  function cancelCashMove() {
    cashMovePad = null;
    setCaixaCtx("default");
  }

  function applyCashMove() {
    if (!cashMovePad) return;
    const val = (cashMovePad.cents || 0) / 100;
    if (val <= 0) {
      document.getElementById("status-hint").textContent = "Informe o valor";
      return;
    }
    let reason =
      cashMovePad.reason ||
      (document.getElementById("cashmove-reason-extra").value || "").trim();
    const extra = (document.getElementById("cashmove-reason-extra").value || "").trim();
    if (cashMovePad.reason && extra) reason = cashMovePad.reason + " — " + extra;
    if (!reason) {
      document.getElementById("status-hint").textContent = "Informe o motivo";
      return;
    }
    const docType = document.getElementById("cashmove-doc-type").value;
    const docRef = (document.getElementById("cashmove-doc-ref").value || "").trim();
    if (docType && !docRef) {
      document.getElementById("status-hint").textContent = "Informe a referência do documento";
      return;
    }
    cashMoves.unshift({
      id: Date.now(),
      kind: cashMovePad.kind,
      value: val,
      reason,
      docType,
      docRef,
      at: Date.now(),
    });
    const label = cashMovePad.kind === "in" ? "Suprimento" : "Sangria";
    document.getElementById("status-hint").textContent =
      label + " " + money(val) + " · " + reason + (docRef ? " · doc " + docRef : "");
    cashMovePad = null;
    setCaixaCtx("default");
    renderCashMoveLog();
  }

  function renderCashMoveLog() {
    const el = document.getElementById("cash-move-log");
    if (!el) return;
    if (!cashMoves.length) {
      el.innerHTML = '<p class="mode-note">Nenhum suprimento/sangria nesta sessão.</p>';
      return;
    }
    const docLabels = {
      recibo: "Recibo/NF",
      vale: "Vale",
      banco: "Banco",
      pedido: "Pedido/OS",
      outro: "Doc",
    };
    el.innerHTML = cashMoves
      .slice(0, 8)
      .map((m) => {
        const dir = m.kind === "in" ? "IN +" : "OUT −";
        const cls = m.kind === "in" ? "in" : "out";
        const doc = m.docType
          ? " · " + (docLabels[m.docType] || "Doc") + " " + m.docRef
          : "";
        const t = new Date(m.at).toLocaleTimeString("pt-BR", {
          hour: "2-digit",
          minute: "2-digit",
        });
        return `<div class="cash-move-item ${cls}">
          <strong>${dir} ${money(m.value)}</strong>
          <span>${m.reason}${doc}</span>
          <em>${t}</em>
        </div>`;
      })
      .join("");
  }

  function syncNumpadUI() {
    if (!numpad) return;
    const isSide = numpad.host === "side";
    if (isSide) {
      document.getElementById("numpad-field-label").textContent = numpad.fieldLabel || numpad.title;
      document.getElementById("numpad-sub").textContent = numpad.sub || "";
      let text = formatDisplay(numpad.raw, numpad.allowDecimal);
      if (numpad.kind === "weight") text = text + " kg";
      if (numpad.kind === "price") text = "R$ " + text;
      document.getElementById("numpad-display").textContent = text;
    } else {
      document.getElementById("caixa-numpad-title").textContent = numpad.title;
      document.getElementById("caixa-numpad-sub").textContent = numpad.sub;
      document.getElementById("caixa-numpad-display").textContent = formatDisplay(
        numpad.raw,
        numpad.allowDecimal
      );
    }
  }

  function syncAdjPadUI() {
    if (!adjPad) return;
    const el = document.getElementById("disc-display");
    if (adjPad.type === "pct") {
      const n = adjPad.pctRaw || "0";
      el.textContent = n.replace(".", ",") + " %";
    } else {
      el.textContent = money(adjPad.cents / 100);
    }
  }

  function openAdjPad(field) {
    const s = getSession();
    if (!s || !s.lines.length) {
      document.getElementById("status-hint").textContent = "Adicione itens antes";
      return;
    }
    const src = field === "disc" ? s.orderDisc : s.orderAcr;
    adjPad = { field, type: src.type || "val", cents: 0, pctRaw: "" };
    if (src.type === "pct") {
      adjPad.type = "pct";
      adjPad.pctRaw = src.value ? String(src.value) : "";
    } else {
      adjPad.cents = Math.round((src.value || 0) * 100);
    }
    const typeVal = document.querySelector('input[name="disc-type"][value="val"]');
    const typePct = document.querySelector('input[name="disc-type"][value="pct"]');
    if (typeVal && typePct) {
      typeVal.checked = adjPad.type === "val";
      typePct.checked = adjPad.type === "pct";
    }
    setSmartCtx("discount", field === "acr" ? "Majoração" : "Desconto");
    syncAdjPadUI();
  }

  function adjPadKey(k) {
    if (!adjPad) return;
    if (adjPad.type === "pct") {
      if (k === "bk") adjPad.pctRaw = adjPad.pctRaw.slice(0, -1);
      else if (k === "00") adjPad.pctRaw += "00";
      else if (k === ".") {
        if (!adjPad.pctRaw.includes(".")) adjPad.pctRaw = (adjPad.pctRaw || "0") + ".";
      } else if (/^\d$/.test(k)) {
        const dec = adjPad.pctRaw.split(".")[1];
        if (dec && dec.length >= 2) return;
        if (adjPad.pctRaw.replace(".", "").length >= 5) return;
        adjPad.pctRaw += k;
      }
    } else {
      if (k === "bk") adjPad.cents = Math.floor(adjPad.cents / 10);
      else if (k === "00") adjPad.cents = Math.min(adjPad.cents * 100, 999999999);
      else if (/^\d$/.test(k)) adjPad.cents = Math.min(adjPad.cents * 10 + Number(k), 999999999);
    }
    syncAdjPadUI();
  }

  function applyAdjPad() {
    if (!adjPad) return;
    const s = getSession();
    if (!s) return;
    pushUndo(adjPad.field === "disc" ? "desconto" : "acréscimo");
    const sub = orderSubtotal();
    let next = { type: "val", value: 0 };
    if (adjPad.type === "pct") {
      next = { type: "pct", value: Math.min(100, Math.max(0, parseFloat(adjPad.pctRaw) || 0)) };
    } else {
      const val = Math.max(0, adjPad.cents / 100);
      next = { type: "val", value: adjPad.field === "disc" ? Math.min(sub, val) : val };
    }
    if (adjPad.field === "disc") s.orderDisc = next;
    else s.orderAcr = next;
    adjPad = null;
    setSmartCtx("summary");
    renderOrder();
  }

  function cancelAdjPad() {
    adjPad = null;
    setSmartCtx("summary");
  }

  function calcParcela(total, n, jurosPct) {
    n = Math.max(1, Math.floor(n) || 1);
    const j = Math.max(0, Number(jurosPct) || 0) / 100;
    if (j === 0) return { n, parcela: total / n, totalComJuros: total };
    const fat = Math.pow(1 + j, n);
    const parcela = (total * j * fat) / (fat - 1);
    return { n, parcela, totalComJuros: parcela * n };
  }

  function syncParcUI() {
    if (!parcPad) return;
    document.getElementById("parc-total").textContent = money(orderTotal());
    document.getElementById("parc-n-btn").textContent = String(parcPad.n || 1);
    document.getElementById("parc-j-btn").textContent =
      ((parcPad.jCents || 0) / 100).toFixed(2).replace(".", ",") + "%";
    document.getElementById("parc-n-btn").classList.toggle("active", parcPad.focus === "n");
    document.getElementById("parc-j-btn").classList.toggle("active", parcPad.focus === "j");
    const r = calcParcela(orderTotal(), parcPad.n, (parcPad.jCents || 0) / 100);
    document.getElementById("parc-result").textContent = r.n + " × " + money(r.parcela);
  }

  function openParcelPad() {
    const s = getSession();
    if (!s || !s.lines.length) {
      document.getElementById("status-hint").textContent = "Adicione itens antes";
      return;
    }
    parcPad = {
      focus: "n",
      n: (s.orderParc && s.orderParc.n) || 10,
      jCents: s.orderParc ? Math.round((s.orderParc.jurosPct || 0) * 100) : 200,
    };
    setSmartCtx("parcel");
    syncParcUI();
  }

  function parcKey(k) {
    if (!parcPad) return;
    if (parcPad.focus === "n") {
      let n = parcPad.n || 0;
      if (k === "bk") n = Math.floor(n / 10);
      else if (k === "00") n = Math.min(n * 100, 48);
      else if (/^\d$/.test(k)) n = Math.min(n * 10 + Number(k), 48);
      parcPad.n = n || 0;
    } else {
      if (k === "bk") parcPad.jCents = Math.floor(parcPad.jCents / 10);
      else if (k === "00") parcPad.jCents = Math.min(parcPad.jCents * 100, 99999);
      else if (/^\d$/.test(k))
        parcPad.jCents = Math.min(parcPad.jCents * 10 + Number(k), 99999);
    }
    syncParcUI();
  }

  function applyParcelPad() {
    if (!parcPad) return;
    const s = getSession();
    if (!s) return;
    pushUndo("parcelamento");
    const n = Math.max(1, parcPad.n || 1);
    const jurosPct = (parcPad.jCents || 0) / 100;
    const r = calcParcela(orderTotal(), n, jurosPct);
    s.orderParc = { n: r.n, jurosPct, parcela: r.parcela };
    parcPad = null;
    setSmartCtx("summary");
    renderOrder();
  }

  function cancelParcelPad() {
    parcPad = null;
    setSmartCtx("summary");
  }

  function openNumpad(opts) {
    numpad = {
      kind: opts.kind,
      host: opts.host || "side",
      lineIdx: opts.lineIdx,
      raw: opts.initial != null ? String(opts.initial) : "",
      allowDecimal: !!opts.allowDecimal,
      title: opts.title,
      fieldLabel: opts.fieldLabel || opts.title,
      sub: opts.sub || "",
      moneyCents: !!opts.moneyCents,
      cents: opts.cents || 0,
    };
    if (numpad.moneyCents) {
      numpad.raw = "";
      if (numpad.host === "side") {
        document.getElementById("numpad-field-label").textContent =
          numpad.fieldLabel || numpad.title;
        document.getElementById("numpad-sub").textContent = numpad.sub || "";
        document.getElementById("numpad-display").textContent = money((numpad.cents || 0) / 100);
        setSmartCtx("numpad", opts.title);
        setCaixaCtx("default");
      } else {
        document.getElementById("caixa-numpad-title").textContent = numpad.title;
        document.getElementById("caixa-numpad-sub").textContent = numpad.sub;
        document.getElementById("caixa-numpad-display").textContent = money(
          (numpad.cents || 0) / 100
        );
        setCaixaCtx("numpad");
        setSmartCtx("summary");
      }
      return;
    }
    if (numpad.host === "side") {
      setSmartCtx("numpad", opts.title);
      setCaixaCtx("default");
    } else {
      setCaixaCtx("numpad");
      setSmartCtx("summary");
    }
    syncNumpadUI();
  }

  function closeNumpad() {
    numpad = null;
    setSmartCtx("summary");
    setCaixaCtx("default");
  }

  function confirmNumpad() {
    if (!numpad) return;
    const s = getSession();
    if (!s) return;
    const kind = numpad.kind;
    const idx = numpad.lineIdx;
    let val;
    if (numpad.moneyCents) {
      val = (numpad.cents || 0) / 100;
    } else {
      val = parseNumpadRaw(numpad.raw, numpad.allowDecimal);
    }

    if (kind === "qty") {
      if (val < 1) {
        document.getElementById("status-hint").textContent = "Quantidade mínima: 1";
        return;
      }
      if (s.lines[idx]) {
        pushUndo("quantidade");
        s.lines[idx].qtd = Math.floor(val);
        s.selectedLine = idx;
        renderOrder();
      }
    } else if (kind === "weight") {
      if (val <= 0) {
        document.getElementById("status-hint").textContent = "Informe o peso";
        return;
      }
      if (s.lines[idx]) {
        pushUndo("peso");
        s.lines[idx].qtd = Math.round(val * 1000) / 1000;
        s.selectedLine = idx;
        renderOrder();
      }
    } else if (kind === "price") {
      if (val <= 0) {
        document.getElementById("status-hint").textContent = "Informe o preço";
        return;
      }
      if (s.lines[idx]) {
        pushUndo("preço");
        s.lines[idx].preco = Math.round(val * 100) / 100;
        s.selectedLine = idx;
        renderOrder();
      }
    } else if (kind === "payment") {
      cashReceived = val;
      const troco = Math.max(0, cashReceived - caixaDue);
      document.getElementById("pay-hint").innerHTML =
        "Recebido <strong>" +
        money(cashReceived) +
        "</strong> · Troco <strong>" +
        money(troco) +
        "</strong>";
      document.getElementById("btn-confirm-pay").disabled = cashReceived < caixaDue;
      document.getElementById("status-hint").textContent =
        cashReceived >= caixaDue ? "Valor ok — confirme o pagamento" : "Valor insuficiente";
    }

    closeNumpad();
  }

  function numpadKey(k) {
    if (!numpad) return;
    if (numpad.moneyCents) {
      if (k === "bk") numpad.cents = Math.floor((numpad.cents || 0) / 10);
      else if (k === "00") numpad.cents = Math.min((numpad.cents || 0) * 100, 999999999);
      else if (/^\d$/.test(k))
        numpad.cents = Math.min((numpad.cents || 0) * 10 + Number(k), 999999999);
      document.getElementById(
        numpad.host === "side" ? "numpad-display" : "caixa-numpad-display"
      ).textContent = money((numpad.cents || 0) / 100);
      return;
    }
    if (k === "bk") {
      numpad.raw = numpad.raw.slice(0, -1);
    } else if (k === "00") {
      if (!numpad.allowDecimal && numpad.raw.length >= 5) return;
      numpad.raw = (numpad.raw === "0" || !numpad.raw ? "0" : numpad.raw) + "00";
      if (numpad.raw.startsWith("00") && numpad.raw.length > 2)
        numpad.raw = String(parseInt(numpad.raw, 10) || 0);
    } else if (k === ".") {
      if (!numpad.allowDecimal) return;
      if (numpad.raw.includes(".")) return;
      numpad.raw = (numpad.raw || "0") + ".";
    } else if (/^\d$/.test(k)) {
      if (!numpad.allowDecimal && numpad.raw.length >= 6) return;
      if (numpad.allowDecimal) {
        const dec = numpad.raw.split(".")[1];
        if (dec && dec.length >= 3) return;
      }
      numpad.raw = numpad.raw === "0" ? k : numpad.raw + k;
    }
    syncNumpadUI();
  }

  function openQtyPad(i) {
    const s = getSession();
    if (!s) return;
    const line = s.lines[i];
    if (!line) return;
    s.selectedLine = i;
    renderOrder();
    if (line.peso) {
      openNumpad({
        kind: "weight",
        host: "side",
        lineIdx: i,
        allowDecimal: true,
        initial: line.qtd,
        title: "Peso",
        fieldLabel: "Peso",
        sub: line.nome,
      });
    } else {
      openNumpad({
        kind: "qty",
        host: "side",
        lineIdx: i,
        allowDecimal: false,
        initial: line.qtd,
        title: "Quantidade",
        fieldLabel: "Quantidade",
        sub: line.nome,
      });
    }
  }

  function openPricePad() {
    const s = getSession();
    if (!s || s.selectedLine < 0 || !s.lines[s.selectedLine]) return;
    const line = s.lines[s.selectedLine];
    openNumpad({
      kind: "price",
      host: "side",
      lineIdx: s.selectedLine,
      moneyCents: true,
      cents: Math.round((line.preco || 0) * 100),
      title: "Valor Manual",
      fieldLabel: "Preço Unitário",
      sub: line.nome,
    });
  }

  function openNoteEditor() {
    const s = getSession();
    if (!s || s.selectedLine < 0 || !s.lines[s.selectedLine]) return;
    const line = s.lines[s.selectedLine];
    document.getElementById("text-title").textContent = "Observação";
    document.getElementById("text-sub").textContent = line.nome;
    document.getElementById("text-editor").value = line.obs || "";
    setSmartCtx("text", "Observação");
    document.getElementById("text-editor").focus();
  }

  function confirmText() {
    const s = getSession();
    if (s && s.selectedLine >= 0 && s.lines[s.selectedLine]) {
      pushUndo("observação");
      s.lines[s.selectedLine].obs = (document.getElementById("text-editor").value || "").trim();
      renderOrder();
    }
    setSmartCtx("summary");
  }

  function appendNotePhrase(phrase) {
    const ta = document.getElementById("text-editor");
    const cur = (ta.value || "").trim();
    ta.value = cur ? cur + "; " + phrase : phrase;
    ta.focus();
  }

  function stockMessageFor(product) {
    const st = product.stockStatus || "local";
    const fn = STOCK_MESSAGES[st] || STOCK_MESSAGES.local;
    return fn(product);
  }

  function openStock(productOverride) {
    let product = productOverride;
    const s = getSession();
    if (!product && s && s.selectedLine >= 0) {
      const line = s.lines[s.selectedLine];
      product = SAMPLE.find((p) => p.id === line.id);
      document.getElementById("stock-sub").textContent = line.nome;
    } else if (product) {
      document.getElementById("stock-sub").textContent = product.nome;
    } else {
      document.getElementById("stock-sub").textContent = "Consulta rápida";
      document.getElementById("stock-body").innerHTML =
        "Selecione um item do pedido ou um produto do mostruário para ver disponibilidade.";
      setSmartCtx("stock");
      return;
    }
    document.getElementById("stock-body").innerHTML = stockMessageFor(product);
    setSmartCtx("stock");
  }

  function openVariantPanel(product) {
    pendingVariant = product;
    variantPick = {
      cor: product.variants.cores[0] || "",
      tamanho: product.variants.tamanhos[0] || "",
    };
    document.getElementById("variant-sub").textContent = product.nome + " · " + money(product.preco);
    renderVariantSwatches();
    setSmartCtx("variant");
  }

  function renderVariantSwatches() {
    if (!pendingVariant) return;
    const coresEl = document.getElementById("variant-cores");
    const tamanhosEl = document.getElementById("variant-tamanhos");
    coresEl.innerHTML = pendingVariant.variants.cores
      .map(
        (c) =>
          `<button type="button" class="swatch ${c === variantPick.cor ? "active" : ""}" data-cor="${c}">${c}</button>`
      )
      .join("");
    tamanhosEl.innerHTML = pendingVariant.variants.tamanhos
      .map(
        (t) =>
          `<button type="button" class="swatch size ${t === variantPick.tamanho ? "active" : ""}" data-tam="${t}">${t}</button>`
      )
      .join("");
    coresEl.querySelectorAll("[data-cor]").forEach((btn) => {
      btn.addEventListener("click", () => {
        variantPick.cor = btn.dataset.cor;
        renderVariantSwatches();
      });
    });
    tamanhosEl.querySelectorAll("[data-tam]").forEach((btn) => {
      btn.addEventListener("click", () => {
        variantPick.tamanho = btn.dataset.tam;
        renderVariantSwatches();
      });
    });
  }

  function confirmVariant() {
    if (!pendingVariant) return;
    const label = pendingVariant.nome + " (" + variantPick.cor + " · " + variantPick.tamanho + ")";
    addLineToOrder({
      id: pendingVariant.id,
      nome: label,
      preco: pendingVariant.preco,
      qtd: 1,
      descPct: 0,
      variantKey: variantPick.cor + "|" + variantPick.tamanho,
    });
    pendingVariant = null;
    setSmartCtx("summary");
  }

  function cancelVariant() {
    pendingVariant = null;
    setSmartCtx("summary");
  }

  function openPaymentPad() {
    setMode("caixa");
    if (cashMovePad) cancelCashMove();
    openNumpad({
      kind: "payment",
      host: "caixa",
      moneyCents: true,
      cents: 0,
      title: "Valor recebido",
      fieldLabel: "Valor recebido",
      sub: "A receber " + money(caixaDue),
    });
  }

  function clientHint(c) {
    if (c.id === "cf") return "Toque para buscar";
    const parts = [];
    if (c.crediario > 0) parts.push("Crediário " + money(c.crediario));
    if (c.ultimaCompra) parts.push("última compra " + c.ultimaCompra);
    return parts.join(" · ") || "Cliente";
  }

  function pickClient(c) {
    const s = getSession();
    if (!s) return;
    s.client = {
      id: c.id,
      nome: c.nome,
      av: c.av,
      hint: clientHint(c),
      crediario: c.crediario,
      ultimaCompra: c.ultimaCompra,
    };
    s.updatedAt = Date.now();
    document.getElementById("client-name").textContent = c.nome;
    document.getElementById("client-av").textContent = c.av;
    document.getElementById("client-hint").textContent = s.client.hint;
    renderSessions();
    setSmartCtx("summary");
  }

  function renderClientResults() {
    const q = (document.getElementById("client-search").value || "").toLowerCase().trim();
    const list = MOCK_CUSTOMERS.filter((c) => {
      if (!q) return true;
      return (
        c.nome.toLowerCase().includes(q) ||
        (c.cpf && c.cpf.replace(/\D/g, "").includes(q.replace(/\D/g, ""))) ||
        (c.telefone && c.telefone.replace(/\D/g, "").includes(q.replace(/\D/g, "")))
      );
    });
    const box = document.getElementById("client-results");
    box.innerHTML = list
      .map(
        (c) => `
      <button type="button" class="client-chip" data-pick="${c.id}" style="width:100%;margin-top:8px;text-align:left">
        <div class="av">${c.av}</div>
        <div class="who">
          <strong>${c.nome}</strong>
          <span>${c.id === "cf" ? c.hint : [c.cpf, c.telefone].filter(Boolean).join(" · ")}</span>
        </div>
      </button>`
      )
      .join("");
    box.querySelectorAll("[data-pick]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const c = MOCK_CUSTOMERS.find((x) => x.id === btn.dataset.pick);
        if (c) pickClient(c);
      });
    });
  }

  function toggleFavorite(id) {
    const n = Number(id);
    const idx = favorites.indexOf(n);
    if (idx >= 0) favorites.splice(idx, 1);
    else favorites.push(n);
    saveJson(LS_FAV, favorites);
    renderProducts();
    document.getElementById("status-hint").textContent =
      idx >= 0 ? "Removido dos favoritos" : "Adicionado aos favoritos";
  }

  function trackRecent(id) {
    const n = Number(id);
    recentIds = recentIds.filter((x) => x !== n);
    recentIds.unshift(n);
    if (recentIds.length > 12) recentIds = recentIds.slice(0, 12);
    saveJson(LS_RECENT, recentIds);
  }

  function filteredProducts() {
    const q = (document.getElementById("prod-search").value || "").toLowerCase().trim();
    let list = SAMPLE.slice();

    if (storeMode === "mercearia") {
      list = list.filter((p) => !p.storeModes || p.storeModes.includes("mercearia") || p.cat !== "Serviços");
    } else if (storeMode === "moda") {
      list = list.sort((a, b) => {
        const aModa = a.variants ? 0 : 1;
        const bModa = b.variants ? 0 : 1;
        return aModa - bModa;
      });
    } else if (storeMode === "servico") {
      list = list.filter((p) => p.servico || p.storeModes?.includes("servico") || p.cat === "Serviços");
      if (!list.length) list = SAMPLE.filter((p) => p.servico);
    }

    if (catalogTab === "favoritos") {
      list = list.filter((p) => favorites.includes(p.id));
    } else if (catalogTab === "ultimos") {
      list = recentIds.map((id) => SAMPLE.find((p) => p.id === id)).filter(Boolean);
    }

    return list.filter((p) => {
      if (cat && p.cat !== cat) return false;
      if (!q) return true;
      return (
        p.nome.toLowerCase().includes(q) ||
        p.sku.includes(q) ||
        String(p.id).includes(q)
      );
    });
  }

  function renderCats() {
    const cats = ["", ...new Set(SAMPLE.map((p) => p.cat))];
    document.getElementById("prod-cats").innerHTML = cats
      .map(
        (c) =>
          `<button type="button" class="pos-cat ${c === cat ? "active" : ""}" data-cat="${c}">${
            c || "Todos"
          }</button>`
      )
      .join("");
  }

  function renderCatalogTabs() {
    document.querySelectorAll("#catalog-tabs button").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === catalogTab);
    });
  }

  function stockBadgeHtml(p) {
    const st = STOCK_LABELS[p.stockStatus || "local"] || STOCK_LABELS.local;
    return `<span class="stock-badge ${st.cls}">${st.short}</span>`;
  }

  function renderProducts() {
    const list = filteredProducts();
    document.getElementById("prod-grid").innerHTML = list
      .map((p) => {
        const fav = favorites.includes(p.id);
        const src = p.foto || FALLBACK_FOTO;
        return `
      <button type="button" class="prod-card ${fav ? "fav" : ""}" data-id="${p.id}">
        <span class="prod-fav ${fav ? "on" : ""}" data-fav="${p.id}" title="Favorito">★</span>
        <div class="thumb">
          <img src="${src}" alt="" loading="lazy" onerror="this.onerror=null;this.src='${FALLBACK_FOTO}'">
        </div>
        <div class="name">${p.nome}</div>
        <div class="price">${money(p.preco)}${p.peso ? "<small>/kg</small>" : p.servico ? "<small>/hora</small>" : ""}</div>
        ${stockBadgeHtml(p)}
      </button>`;
      })
      .join("");
  }

  function syncOrderTypeUI() {
    const s = getSession();
    if (!s) return;
    document.querySelectorAll("#order-type-toggle button").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.type === s.orderType);
    });
    const isOrc = s.orderType === "orcamento";
    document.getElementById("order-panel-title").textContent = isOrc ? "Orçamento" : "Pedido";
    document.getElementById("btn-send-cashier").textContent = isOrc ? "Salvar orçamento" : "Enviar ao caixa";
    document.getElementById("btn-convert-order").hidden = !isOrc;
    document.getElementById("btn-send-cashier").disabled = !s.lines.length;
  }

  function renderQueueBanner() {
    const el = document.getElementById("queue-banner");
    const s = getSession();
    if (!s || !s.queueStatus) {
      el.hidden = true;
      return;
    }
    el.hidden = false;
    const labels = { aguardando: "Aguardando", pagamento: "Em pagamento", pago: "Pago" };
    el.className = "queue-banner state-" + s.queueStatus.state;
    el.innerHTML =
      `<strong>Pedido #${s.queueStatus.orderNum} na fila</strong> · ${labels[s.queueStatus.state] || s.queueStatus.state}`;
  }

  function renderOrder() {
    const s = getSession();
    const box = document.getElementById("order-lines");
    const empty = document.getElementById("order-empty");
    if (!s) return;

    const n = s.lines.length;
    document.getElementById("order-count").textContent = n + (n === 1 ? " item" : " itens");
    document.getElementById("summary-items-label").textContent =
      n + (n === 1 ? " produto" : " produtos");
    document.getElementById("summary-sub").textContent = money(orderSubtotal());
    const discAmt = orderDiscAmount();
    const acrAmt = orderAcrAmount();
    document.getElementById("summary-disc").textContent =
      s.orderDisc.type === "pct" && s.orderDisc.value
        ? money(discAmt) + " (" + s.orderDisc.value + "%)"
        : money(discAmt);
    document.getElementById("summary-acr").textContent =
      s.orderAcr.type === "pct" && s.orderAcr.value
        ? money(acrAmt) + " (" + s.orderAcr.value + "%)"
        : money(acrAmt);
    document.getElementById("summary-parc").textContent = s.orderParc
      ? s.orderParc.n + " × " + money(s.orderParc.parcela)
      : "—";
    document.getElementById("order-total").textContent = money(orderTotal());
    document.getElementById("btn-side-note").disabled = s.selectedLine < 0 || !s.lines[s.selectedLine];
    document.getElementById("btn-side-price").disabled = s.selectedLine < 0 || !s.lines[s.selectedLine];

    syncOrderTypeUI();
    renderQueueBanner();

    if (!n) {
      box.innerHTML = "";
      box.appendChild(empty);
      empty.style.display = "grid";
      return;
    }
    empty.style.display = "none";
    box.innerHTML = s.lines
      .map((l, i) => {
        const qtyLabel = l.peso ? String(l.qtd).replace(".", ",") + " kg" : String(l.qtd);
        const note = l.obs ? `<span class="disc" title="${l.obs}">obs</span>` : "";
        return `
      <div class="order-line ${i === s.selectedLine ? "sel" : ""}" data-idx="${i}">
        <div class="title">${l.nome} ${note}</div>
        <div class="line-total">${money(lineTotal(l))}</div>
        <div class="meta">${money(l.preco)}${l.peso ? "/kg" : " un."}</div>
        <div></div>
        <div class="qty-row">
          <button type="button" data-act="dec" data-idx="${i}">−</button>
          <button type="button" class="qty qty-btn" data-act="qty" data-idx="${i}" title="Alterar">${qtyLabel}</button>
          <button type="button" data-act="inc" data-idx="${i}">+</button>
          <button type="button" data-act="rm" data-idx="${i}" title="Remover">×</button>
        </div>
      </div>`;
      })
      .join("");
    s.updatedAt = Date.now();
    renderSessions();
  }

  function addLineToOrder(line) {
    const s = getSession();
    if (!s) return;
    pushUndo("adicionar item");
    s.lines.push(line);
    s.selectedLine = s.lines.length - 1;
    if (line.id) trackRecent(line.id);
    renderOrder();
  }

  function addProduct(id) {
    const p = SAMPLE.find((x) => x.id === Number(id));
    if (!p) return;
    const s = getSession();
    if (!s) return;

    if (p.variants && (storeMode === "moda" || p.id === 10)) {
      openVariantPanel(p);
      return;
    }

    if (p.peso) {
      const hit = s.lines.find((l) => l.id === p.id && !l.variantKey);
      if (!hit) {
        pushUndo("adicionar item");
        s.lines.push({ id: p.id, nome: p.nome, preco: p.preco, qtd: 0, peso: true, descPct: 0 });
      }
      s.selectedLine = s.lines.findIndex((l) => l.id === p.id && l.peso);
      trackRecent(p.id);
      renderOrder();
      openQtyPad(s.selectedLine);
      return;
    }

    const hit = s.lines.find(
      (l) => l.id === p.id && !l.peso && !l.variantKey
    );
    pushUndo("adicionar item");
    if (hit) hit.qtd += 1;
    else s.lines.push({ id: p.id, nome: p.nome, preco: p.preco, qtd: 1, descPct: 0 });
    s.selectedLine = s.lines.findIndex(
      (l) => l.id === p.id && !l.peso && !l.variantKey
    );
    trackRecent(p.id);
    renderOrder();
  }

  function addToFila(session, orderNum) {
    const list = document.getElementById("fila-list");
    const el = document.createElement("div");
    el.className = "fila-item";
    el.dataset.order = String(orderNum);
    el.innerHTML = `
      <div>
        <strong>Pedido #${orderNum} · ${session.client.nome}</strong>
        <span>PDV · agora · ${session.lines.length} ${session.lines.length === 1 ? "item" : "itens"}</span>
      </div>
      <div class="val">${money(sessionTotal(session))}</div>`;
    el.addEventListener("click", () => {
      document.querySelectorAll("#fila-list .fila-item").forEach((x) => x.classList.remove("active"));
      el.classList.add("active");
      caixaDue = sessionTotal(session);
      document.getElementById("caixa-due").textContent = money(caixaDue);
    });
    list.insertBefore(el, list.firstChild);
  }

  function startQueueMock(session) {
    const orderNum = nextOrderNum++;
    session.queueStatus = { orderNum, state: "aguardando" };
    renderQueueBanner();
    addToFila(session, orderNum);

    const states = ["aguardando", "pagamento", "pago"];
    let step = 0;
    if (queueTimers[session.id]) clearInterval(queueTimers[session.id]);
    queueTimers[session.id] = setInterval(() => {
      step++;
      if (step >= states.length) {
        clearInterval(queueTimers[session.id]);
        delete queueTimers[session.id];
        return;
      }
      session.queueStatus.state = states[step];
      renderQueueBanner();
      const labels = { aguardando: "Aguardando", pagamento: "Em pagamento", pago: "Pago" };
      document.getElementById("status-hint").textContent =
        "Pedido #" + orderNum + " · " + labels[session.queueStatus.state];
    }, 4000);
  }

  function sendToCashier() {
    const s = getSession();
    if (!s || !s.lines.length) return;

    if (s.orderType === "orcamento") {
      document.getElementById("status-hint").textContent =
        "Orçamento salvo (mock) · " + money(orderTotal());
      s.lines = [];
      s.selectedLine = -1;
      s.orderDisc = { type: "val", value: 0 };
      s.orderAcr = { type: "val", value: 0 };
      s.orderParc = null;
      undoStack = [];
      syncUndoBtn();
      renderOrder();
      return;
    }

    startQueueMock(s);
    document.getElementById("status-hint").textContent =
      "Pedido #" + s.queueStatus.orderNum + " na fila · Aguardando · " + money(orderTotal());

    s.lines = [];
    s.selectedLine = -1;
    s.orderDisc = { type: "val", value: 0 };
    s.orderAcr = { type: "val", value: 0 };
    s.orderParc = null;
    undoStack = [];
    syncUndoBtn();
    renderOrder();
  }

  function convertToOrder() {
    const s = getSession();
    if (!s) return;
    s.orderType = "pedido";
    syncOrderTypeUI();
    document.getElementById("status-hint").textContent = "Orçamento convertido em pedido";
  }

  function setStoreMode(next) {
    storeMode = next;
    localStorage.setItem(LS_STORE, next);
    document.querySelectorAll("#store-mode button").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.store === next);
    });
    const labels = { mercearia: "Mercearia", moda: "Moda", servico: "Serviço" };
    document.getElementById("status-store").textContent = "Loja: " + (labels[next] || next);
    renderProducts();
  }

  function renderAll() {
    renderCats();
    renderCatalogTabs();
    renderProducts();
    renderOrder();
    const s = getSession();
    if (s) {
      document.getElementById("client-name").textContent = s.client.nome;
      document.getElementById("client-av").textContent = s.client.av;
      document.getElementById("client-hint").textContent = s.client.hint;
    }
  }

  function setMode(next) {
    mode = next;
    if (numpad && numpad.host === "side" && mode !== "pdv") closeNumpad();
    if (numpad && numpad.host === "caixa" && mode !== "caixa") closeNumpad();
    if (mode !== "pdv") setSmartCtx("summary");
    document.querySelectorAll(".pos-mode button").forEach((b) => {
      b.classList.toggle("active", b.dataset.mode === mode);
    });
    document.getElementById("view-pdv").classList.toggle("active", mode === "pdv");
    document.getElementById("view-caixa").classList.toggle("active", mode === "caixa");
    document.getElementById("top-mode-label").textContent =
      mode === "pdv" ? "Terminal PDV" : "Terminal Caixa";
    document.getElementById("status-mode").textContent =
      mode === "pdv" ? "Modo PDV" : "Modo Caixa";
  }

  function bindNumpadKeys(el) {
    el.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-k]");
      if (btn) numpadKey(btn.dataset.k);
    });
  }

  function boot() {
    const user = (window.AuthService && window.AuthService.getUser()) || {};
    const name = user.nome || user.usuario || "Operador";
    document.getElementById("op-name").textContent = name;
    document.getElementById("status-user").textContent = name;

    createSession();
    setStoreMode(storeMode);
    renderClientResults();
    renderAll();
    setSmartCtx("summary");
    setCaixaCtx("default");
    setMode("pdv");
    syncUndoBtn();

    setInterval(() => {
      const d = new Date();
      document.getElementById("clock").textContent = d.toLocaleTimeString("pt-BR", {
        hour: "2-digit",
        minute: "2-digit",
      });
      renderSessions();
    }, 30000);

    document.querySelectorAll(".pos-mode button").forEach((btn) => {
      btn.addEventListener("click", () => setMode(btn.dataset.mode));
    });

    document.querySelectorAll("#store-mode button").forEach((btn) => {
      btn.addEventListener("click", () => setStoreMode(btn.dataset.store));
    });

    document.getElementById("prod-cats").addEventListener("click", (e) => {
      const btn = e.target.closest(".pos-cat");
      if (!btn) return;
      cat = btn.dataset.cat || "";
      renderCats();
      renderProducts();
    });

    document.getElementById("catalog-tabs").addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-tab]");
      if (!btn) return;
      catalogTab = btn.dataset.tab;
      renderCatalogTabs();
      renderProducts();
    });

    document.getElementById("prod-search").addEventListener("input", renderProducts);

    document.getElementById("prod-grid").addEventListener("click", (e) => {
      const favBtn = e.target.closest("[data-fav]");
      if (favBtn) {
        e.stopPropagation();
        toggleFavorite(favBtn.dataset.fav);
        return;
      }
      const card = e.target.closest(".prod-card");
      if (card) addProduct(card.dataset.id);
    });

    document.getElementById("prod-grid").addEventListener("mousedown", (e) => {
      const card = e.target.closest(".prod-card");
      if (!card || e.target.closest("[data-fav]")) return;
      longPressTimer = setTimeout(() => toggleFavorite(card.dataset.id), 600);
    });
    document.getElementById("prod-grid").addEventListener("mouseup", () => clearTimeout(longPressTimer));
    document.getElementById("prod-grid").addEventListener("mouseleave", () => clearTimeout(longPressTimer));

    document.getElementById("order-lines").addEventListener("click", (e) => {
      const s = getSession();
      if (!s) return;
      const btn = e.target.closest("button[data-act]");
      if (btn) {
        const i = Number(btn.dataset.idx);
        const act = btn.dataset.act;
        if (act === "qty") {
          openQtyPad(i);
          return;
        }
        pushUndo(act === "rm" ? "remover item" : "quantidade");
        if (act === "inc") {
          if (s.lines[i].peso) {
            undoStack.pop();
            openQtyPad(i);
            return;
          }
          s.lines[i].qtd += 1;
        }
        if (act === "dec") {
          if (s.lines[i].peso) {
            undoStack.pop();
            openQtyPad(i);
            return;
          }
          s.lines[i].qtd = Math.max(1, s.lines[i].qtd - 1);
        }
        if (act === "rm") {
          s.lines.splice(i, 1);
          s.selectedLine = Math.min(i, s.lines.length - 1);
          if (!s.lines.length) s.selectedLine = -1;
          if (numpad && numpad.lineIdx === i) closeNumpad();
        }
        s.selectedLine = s.lines.length
          ? Math.min(Math.max(s.selectedLine, 0), s.lines.length - 1)
          : -1;
        renderOrder();
        syncUndoBtn();
        return;
      }
      const line = e.target.closest(".order-line");
      if (line) {
        s.selectedLine = Number(line.dataset.idx);
        renderOrder();
      }
    });

    bindNumpadKeys(document.getElementById("numpad-keys"));
    bindNumpadKeys(document.getElementById("caixa-numpad-keys"));
    document.getElementById("numpad-ok").addEventListener("click", confirmNumpad);
    document.getElementById("numpad-cancel").addEventListener("click", closeNumpad);
    document.getElementById("caixa-numpad-ok").addEventListener("click", confirmNumpad);
    document.getElementById("caixa-numpad-cancel").addEventListener("click", closeNumpad);

    document.getElementById("btn-clear").addEventListener("click", () => {
      const s = getSession();
      if (!s) return;
      if (s.lines.length) pushUndo("limpar pedido");
      s.lines = [];
      s.selectedLine = -1;
      s.orderDisc = { type: "val", value: 0 };
      s.orderAcr = { type: "val", value: 0 };
      s.orderParc = null;
      closeNumpad();
      cancelAdjPad();
      cancelParcelPad();
      renderOrder();
      syncUndoBtn();
    });

    document.getElementById("btn-suspend").addEventListener("click", suspendCurrentSession);
    document.getElementById("btn-undo").addEventListener("click", undoLast);
    document.getElementById("btn-send-cashier").addEventListener("click", sendToCashier);
    document.getElementById("btn-convert-order").addEventListener("click", convertToOrder);

    document.getElementById("order-type-toggle").addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-type]");
      if (!btn) return;
      const s = getSession();
      if (s) {
        s.orderType = btn.dataset.type;
        syncOrderTypeUI();
      }
    });

    document.getElementById("btn-client").addEventListener("click", () => {
      setSmartCtx("customer");
      document.getElementById("client-search").value = "";
      renderClientResults();
      document.getElementById("client-search").focus();
    });
    document.getElementById("client-search").addEventListener("input", renderClientResults);
    document.getElementById("btn-customer-back").addEventListener("click", () => setSmartCtx("summary"));
    document.getElementById("btn-stock-back").addEventListener("click", () => setSmartCtx("summary"));
    document.getElementById("btn-side-note").addEventListener("click", openNoteEditor);
    document.getElementById("btn-side-price").addEventListener("click", openPricePad);
    document.getElementById("btn-side-stock").addEventListener("click", () => openStock());
    document.getElementById("text-ok").addEventListener("click", confirmText);
    document.getElementById("text-cancel").addEventListener("click", () => setSmartCtx("summary"));

    document.getElementById("note-phrases").addEventListener("click", (e) => {
      const chip = e.target.closest("[data-phrase]");
      if (chip) appendNotePhrase(chip.dataset.phrase);
    });

    document.getElementById("btn-open-discount").addEventListener("click", () => openAdjPad("disc"));
    document.getElementById("btn-open-surcharge").addEventListener("click", () => openAdjPad("acr"));
    document.getElementById("btn-open-installments").addEventListener("click", openParcelPad);
    document.getElementById("disc-cancel").addEventListener("click", cancelAdjPad);
    document.getElementById("disc-apply").addEventListener("click", applyAdjPad);
    document.getElementById("disc-keys").addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-k]");
      if (btn && adjPad) adjPadKey(btn.dataset.k);
    });
    document.querySelectorAll('input[name="disc-type"]').forEach((r) => {
      r.addEventListener("change", () => {
        if (!adjPad) return;
        adjPad.type = r.value;
        adjPad.cents = 0;
        adjPad.pctRaw = "";
        syncAdjPadUI();
      });
    });

    document.getElementById("parc-cancel").addEventListener("click", cancelParcelPad);
    document.getElementById("parc-apply").addEventListener("click", applyParcelPad);
    document.getElementById("parc-keys").addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-k]");
      if (btn && parcPad) parcKey(btn.dataset.k);
    });
    document.getElementById("parc-n-btn").addEventListener("click", () => {
      if (!parcPad) return;
      parcPad.focus = "n";
      syncParcUI();
    });
    document.getElementById("parc-j-btn").addEventListener("click", () => {
      if (!parcPad) return;
      parcPad.focus = "j";
      syncParcUI();
    });

    document.getElementById("variant-cancel").addEventListener("click", cancelVariant);
    document.getElementById("variant-apply").addEventListener("click", confirmVariant);

    document.getElementById("pay-dinheiro")?.addEventListener("click", openPaymentPad);
    document.getElementById("caixa-action-bar")?.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-pay]");
      if (btn) {
        const kind = btn.dataset.pay;
        document.querySelectorAll("#caixa-action-bar button[data-pay]").forEach((b) =>
          b.classList.toggle("active", b === btn)
        );
        if (kind === "dinheiro") {
          openPaymentPad();
          return;
        }
        if (cashMovePad) cancelCashMove();
        setCaixaCtx("default");
        const labels = {
          pix: "PIX — QR na próxima etapa",
          debito: "Débito — TEF na próxima etapa",
          credito: "Crédito — TEF na próxima etapa",
          voucher: "Voucher — validação na próxima etapa",
        };
        document.getElementById("pay-hint").textContent = labels[kind] || kind;
        document.getElementById("btn-confirm-pay").disabled = false;
      }
    });
    document.getElementById("btn-suprimento")?.addEventListener("click", () => openCashMove("in"));
    document.getElementById("btn-sangria")?.addEventListener("click", () => openCashMove("out"));
    document.getElementById("cashmove-cancel")?.addEventListener("click", cancelCashMove);
    document.getElementById("cashmove-apply")?.addEventListener("click", applyCashMove);
    document.getElementById("cashmove-keys")?.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-k]");
      if (btn && cashMovePad) cashMoveKey(btn.dataset.k);
    });
    document.getElementById("cashmove-reasons")?.addEventListener("click", (e) => {
      const chip = e.target.closest("[data-reason]");
      if (!chip || !cashMovePad) return;
      cashMovePad.reason = chip.dataset.reason;
      document.querySelectorAll("#cashmove-reasons .phrase-chip").forEach((c) =>
        c.classList.toggle("active", c === chip)
      );
    });
    document.getElementById("cashmove-doc-type")?.addEventListener("change", (e) => {
      const ref = document.getElementById("cashmove-doc-ref");
      ref.disabled = !e.target.value;
      if (!e.target.value) ref.value = "";
      else ref.focus();
    });

    document.getElementById("btn-confirm-pay").addEventListener("click", () => {
      document.getElementById("status-hint").textContent =
        "Pagamento confirmado (mock) — NFC-e na próxima etapa";
      document.getElementById("btn-confirm-pay").disabled = true;
    });

    renderCashMoveLog();
    document.querySelectorAll("#fila-list .fila-item").forEach((el) => {
      el.addEventListener("click", () => {
        document.querySelectorAll("#fila-list .fila-item").forEach((x) => x.classList.remove("active"));
        el.classList.add("active");
        const val = el.querySelector(".val");
        if (val) {
          caixaDue = parseFloat(val.textContent.replace(/[^\d,]/g, "").replace(",", ".")) || 0;
          document.getElementById("caixa-due").textContent = money(caixaDue);
        }
      });
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        if (cashMovePad) {
          e.preventDefault();
          cancelCashMove();
          return;
        }
        if (parcPad) {
          e.preventDefault();
          cancelParcelPad();
          return;
        }
        if (adjPad) {
          e.preventDefault();
          cancelAdjPad();
          return;
        }
        if (pendingVariant) {
          e.preventDefault();
          cancelVariant();
          return;
        }
        const ctx = document.getElementById("pos-smart").dataset.ctx;
        if (numpad) {
          e.preventDefault();
          closeNumpad();
          return;
        }
        if (ctx && ctx !== "summary") {
          e.preventDefault();
          setSmartCtx("summary");
          return;
        }
      }
      if (cashMovePad) {
        if (e.key === "Enter") {
          e.preventDefault();
          applyCashMove();
          return;
        }
        if (e.key === "Backspace") {
          e.preventDefault();
          cashMoveKey("bk");
          return;
        }
        if (/^\d$/.test(e.key)) {
          e.preventDefault();
          cashMoveKey(e.key);
        }
        return;
      }
      if (parcPad) {
        if (e.key === "Enter") {
          e.preventDefault();
          applyParcelPad();
          return;
        }
        if (e.key === "Backspace") {
          e.preventDefault();
          parcKey("bk");
          return;
        }
        if (/^\d$/.test(e.key)) {
          e.preventDefault();
          parcKey(e.key);
        }
        return;
      }
      if (adjPad) {
        if (e.key === "Enter") {
          e.preventDefault();
          applyAdjPad();
          return;
        }
        if (e.key === "Backspace") {
          e.preventDefault();
          adjPadKey("bk");
          return;
        }
        if (/^\d$/.test(e.key)) {
          e.preventDefault();
          adjPadKey(e.key);
          return;
        }
        if (e.key === "." || e.key === ",") {
          e.preventDefault();
          adjPadKey(".");
        }
        return;
      }
      if (!numpad) return;
      if (e.key === "Enter") {
        e.preventDefault();
        confirmNumpad();
        return;
      }
      if (e.key === "Backspace") {
        e.preventDefault();
        numpadKey("bk");
        return;
      }
      if (/^\d$/.test(e.key)) {
        e.preventDefault();
        numpadKey(e.key);
        return;
      }
      if (e.key === "." || e.key === ",") {
        e.preventDefault();
        numpadKey(".");
      }
    });
  }

  let booted = false;
  function bootOnce() {
    if (booted) return;
    booted = true;
    boot();
  }
  document.addEventListener("auth:ready", bootOnce);
  if (window.__authReady || (window.AuthService && window.AuthService.getToken())) bootOnce();
})();
