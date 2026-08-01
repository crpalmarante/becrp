/**
 * BECRP POS — Terminal PDV (vendedor)
 * Smart Panel, sessões, catálogo, pedido/orçamento.
 */
(function () {
  "use strict";

  const LS_FAV = "becrp-pos-favorites";
  const LS_RECENT = "becrp-pos-recent";
  const LS_TRAINING = "becrp-pos-training";
  const LS_GOAL = "becrp-pos-daily-goal";
  const DAILY_TARGET = 5000;

  const STOCK_LABELS = {
    local: { short: "Na loja", long: "Disponível nesta filial", cls: "stock-ok" },
    branch: { short: "Outra filial", long: "Retirada em outra filial (~2h)", cls: "stock-branch" },
    transit: { short: "Em trânsito", long: "Em trânsito — chega amanhã", cls: "stock-transit" },
    none: { short: "Indisponível", long: "Sem previsão — ver similares", cls: "stock-none" },
  };

  const STOCK_MESSAGES = {
    local: (p) => {
      const label = (p.promise && p.promise.label) || "Disponível nesta loja";
      return `<strong>${label}</strong><br>${p.stock} un. disponíveis na filial atual.`;
    },
    branch: (p) => {
      const label =
        (p.promise && p.promise.label) ||
        (p.promiseBranches && p.promiseBranches[0] && p.promiseBranches[0].label) ||
        "Disponível em outra filial (~2h)";
      const extra =
        p.promiseBranches && p.promiseBranches.length > 1
          ? `<br>Também em ${p.promiseBranches
              .slice(1)
              .map((b) => b.estabelecimento_nome)
              .join(", ")}.`
          : "<br>Retirada ou transferência expressa.";
      return `<strong>${label}</strong>${extra}`;
    },
    transit: (p) => {
      const label = (p.promise && p.promise.label) || "Em trânsito — chega em breve";
      const origem = p.promise && p.promise.origem ? `<br>Origem: ${p.promise.origem}.` : "";
      return `<strong>${label}</strong>${origem}`;
    },
    none: (p) => {
      const label = (p.promise && p.promise.label) || "Sem previsão — ver similares";
      return `<strong>${label}</strong><br>Produto indisponível. Sugestão: item equivalente da mesma categoria.`;
    },
  };

  const CONSUMIDOR_FINAL = {
    id: "cf",
    nome: "Consumidor final",
    av: "CF",
    cpf: "",
    telefone: "",
    hint: "Venda sem identificação",
    crediario: 0,
    ultimaCompra: null,
    historico: [],
  };

  /** Clientes do PDV — demo até a API responder. */
  let MOCK_CUSTOMERS = [
    CONSUMIDOR_FINAL,
    {
      id: "joao",
      nome: "João da Silva",
      av: "JS",
      cpf: "123.456.789-00",
      telefone: "(11) 98765-4321",
      hint: "",
      crediario: 340.5,
      ultimaCompra: "15/07/2026 · R$ 89,90",
      historico: [
        { nome: "Arroz 5kg", quando: "15/07/2026" },
        { nome: "Feijão 1kg", quando: "02/07/2026" },
        { nome: "Café 500g", quando: "20/06/2026" },
      ],
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
      historico: [
        { nome: "Detergente", quando: "28/07/2026" },
        { nome: "Leite 1L", quando: "15/07/2026" },
      ],
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
      historico: [
        { nome: "Arroz 5kg (cx)", quando: "20/07/2026" },
        { nome: "Óleo Soja 900ml", quando: "05/07/2026" },
      ],
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
      tamanhoUsual: "M",
      historico: [
        { nome: "Camisa Polo (Preta · M)", quando: "29/07/2026" },
        { nome: "Calça Jeans (38)", quando: "10/06/2026" },
      ],
    },
  ];

  const MOCK_PAST_SALES = []; // legado — troca usa /api/pos/vendas
  let pastSalesCache = [];

  const PROMO_RULES = [
    { id: "det3", label: "3+ Detergentes −10%", productIds: [7], minQty: 3, pct: 10 },
    { id: "leite3x2", label: "Leite 3 por 2", productIds: [5], buy: 3, pay: 2 },
  ];

  /** Campanhas ativas (API) — categoria + vigência + forma opcional */
  let liveCampaigns = [];

  const FALLBACK_FOTO = "../assets/images/sem-foto.png";

  /** Catálogo do PDV — demo até a API responder. */
  let dataSource = "demo";
  let SAMPLE = [
    {
      id: 1,
      nome: "Arroz 5kg",
      preco: 32.9,
      stock: 40,
      cat: "Mercearia",
      subcat: "Grãos",
      sku: "000001",
      stockStatus: "local",
      criadoEm: "2026-01-10",
      descricao: "Arroz tipo 1, pacote familiar 5 kg. Ideal para o dia a dia.",
      foto: "../assets/images/pos/1.svg",
      fotos: ["../assets/images/pos/1.svg", "../assets/images/pos/2.svg", "../assets/images/pos/4.svg"],
    },
    {
      id: 2,
      nome: "Feijão 1kg",
      preco: 8.5,
      stock: 55,
      cat: "Mercearia",
      subcat: "Grãos",
      sku: "000002",
      stockStatus: "local",
      criadoEm: "2026-02-01",
      descricao: "Feijão carioca selecionado, pacote 1 kg.",
      foto: "../assets/images/pos/2.svg",
      fotos: ["../assets/images/pos/2.svg", "../assets/images/pos/1.svg"],
    },
    {
      id: 3,
      nome: "Óleo Soja 900ml",
      preco: 7.9,
      stock: 30,
      cat: "Mercearia",
      subcat: "Óleos",
      sku: "000003",
      stockStatus: "branch",
      criadoEm: "2026-03-12",
      descricao: "Óleo de soja refinado 900 ml. Disponível para retirada em filial.",
      foto: "../assets/images/pos/3.svg",
      fotos: ["../assets/images/pos/3.svg", "../assets/images/pos/7.svg"],
    },
    {
      id: 4,
      nome: "Café 500g",
      preco: 18.9,
      stock: 22,
      cat: "Mercearia",
      subcat: "Bebidas secas",
      sku: "000004",
      stockStatus: "local",
      novo: true,
      criadoEm: "2026-07-20",
      descricao: "Café torrado e moído 500 g — torra média.",
      foto: "../assets/images/pos/4.svg",
      fotos: ["../assets/images/pos/4.svg", "../assets/images/pos/5.svg", "../assets/images/pos/1.svg"],
    },
    {
      id: 5,
      nome: "Leite 1L",
      preco: 5.49,
      stock: 80,
      cat: "Frios",
      subcat: "Laticínios",
      sku: "000005",
      ean: "7891000100055",
      stockStatus: "local",
      alertas: ["promo"],
      criadoEm: "2026-04-01",
      descricao: "Leite integral UHT 1 L. Promoção ativa: leve 3 pague 2.",
      foto: "../assets/images/pos/5.svg",
      fotos: ["../assets/images/pos/5.svg", "../assets/images/pos/6.svg"],
    },
    {
      id: 6,
      nome: "Queijo Mussarela",
      preco: 42.0,
      stock: 12,
      cat: "Frios",
      subcat: "Laticínios",
      sku: "000006",
      stockStatus: "transit",
      criadoEm: "2026-05-18",
      descricao: "Mussarela fatiada — venda por kg aproximado no balcão.",
      foto: "../assets/images/pos/6.svg",
      fotos: ["../assets/images/pos/6.svg", "../assets/images/pos/5.svg"],
    },
    {
      id: 7,
      nome: "Detergente",
      preco: 2.99,
      stock: 60,
      cat: "Limpeza",
      subcat: "Louça",
      sku: "000007",
      ean: "7891000100007",
      stockStatus: "local",
      alertas: ["promo"],
      criadoEm: "2026-03-01",
      descricao: "Detergente líquido neutro. Promo: 3+ unidades com 10% off.",
      foto: "../assets/images/pos/7.svg",
      fotos: ["../assets/images/pos/7.svg", "../assets/images/pos/8.svg"],
    },
    {
      id: 8,
      nome: "Sabão em pó",
      preco: 24.5,
      stock: 0,
      cat: "Limpeza",
      subcat: "Roupas",
      sku: "000008",
      stockStatus: "none",
      similares: [7, 2],
      alertas: ["recall"],
      criadoEm: "2025-11-01",
      descricao: "Sabão em pó 1 kg. Atenção: produto em recall — confirme antes de vender.",
      foto: "../assets/images/pos/8.svg",
      fotos: ["../assets/images/pos/8.svg", "../assets/images/pos/7.svg"],
    },
    {
      id: 9,
      nome: "Banana prata",
      preco: 6.9,
      stock: 25,
      cat: "Hortifrúti",
      subcat: "Frutas",
      sku: "000009",
      peso: true,
      stockStatus: "local",
      novo: true,
      criadoEm: "2026-07-28",
      descricao: "Banana prata fresca — informe o peso na balança.",
      foto: "../assets/images/pos/9.svg",
      fotos: ["../assets/images/pos/9.svg", "../assets/images/pos/2.svg"],
    },
    {
      id: 10,
      nome: "Camisa Polo",
      preco: 89.9,
      stock: 24,
      cat: "Moda",
      subcat: "Camisetas",
      sku: "000010",
      stockStatus: "local",
      novo: true,
      criadoEm: "2026-07-15",
      descricao: "Polo piquet com gola — ajuste clássico. Escolha cor e tamanho.",
      foto: "../assets/images/pos/10.svg",
      fotos: ["../assets/images/pos/10.svg", "../assets/images/pos/12.svg", "../assets/images/pos/11.svg"],
      variants: {
        cores: ["Branca", "Preta", "Azul"],
        tamanhos: ["P", "M", "G", "GG"],
        ajusteCor: { Branca: 0, Preta: 0, Azul: 5 },
        ajusteTam: { P: 0, M: 0, G: 5, GG: 10 },
      },
    },
    {
      id: 11,
      nome: "Consultoria 1h",
      preco: 150,
      stock: 999,
      cat: "Serviços",
      subcat: "Consultoria",
      sku: "000011",
      servico: true,
      stockStatus: "local",
      criadoEm: "2026-06-01",
      descricao: "Hora técnica de consultoria — agende após o fechamento do pedido.",
      foto: "../assets/images/pos/11.svg",
      fotos: ["../assets/images/pos/11.svg"],
    },
    {
      id: 12,
      nome: "Calça Jeans",
      preco: 129.9,
      stock: 8,
      cat: "Moda",
      subcat: "Calças",
      sku: "000012",
      stockStatus: "branch",
      criadoEm: "2026-07-01",
      descricao: "Jeans reta, lavagem média. Retirada em outra filial sob consulta.",
      foto: "../assets/images/pos/12.svg",
      fotos: ["../assets/images/pos/12.svg", "../assets/images/pos/10.svg"],
      variants: {
        cores: ["Azul escuro", "Preto"],
        tamanhos: ["38", "40", "42", "44"],
        ajusteCor: { "Azul escuro": 0, Preto: 10 },
        ajusteTam: { "38": 0, "40": 0, "42": 5, "44": 10 },
      },
    },
  ];

  let mode = "pdv";
  let cat = "";
  let subcat = "";
  let catalogTab = "todos";
  let catalogSort = "relevancia";
  let catalogPrice = "";
  let catalogAvail = "";
  let favorites = loadJson(LS_FAV, []);
  let recentIds = loadJson(LS_RECENT, []);
  let consultaMode = false;
  let trainingMode = localStorage.getItem(LS_TRAINING) === "1";
  /** Contexto do terminal / estabelecimento (API /api/pos/contexto). */
  let posContexto = null;
  /** @type {null | object} */
  let pendingPriceProduct = null;
  /** @type {null | object} */
  let pendingRecallProduct = null;
  /** @type {null | { product: object, fotoIdx: number, cor: string, tamanho: string }} */
  let showcaseState = null;

  let sessions = [];
  let activeSessionId = null;
  let nextSessionNum = 1;
  let nextOrderNum = 1043;

  let undoStack = [];
  let pendingVariant = null;
  let variantPick = { cor: "", tamanho: "" };
  let longPressTimer = null;
  /** @type {"note"|"service"} */
  let textEditorMode = "note";

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
    price: "Consulta de Preço",
    exchange: "Troca / Devolução",
    "mgr-auth": "Aprovação do gerente",
    similar: "Produtos Similares",
    payment: "Pagamento",
  };

  const SMART_CTX_IDS = [
    "summary", "customer", "discount", "parcel", "numpad", "text", "stock", "variant",
    "price", "exchange", "mgr-auth", "similar",
  ];

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
      esperaLabel: null,
      esperaPriority: 0,
      trocaAprovacao: null,
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
    if (s.status === "suspended" || s.status === "espera") s.status = "active";
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

  function markEsperaSession() {
    const s = getSession();
    if (!s) return;
    if (!s.lines.length) {
      document.getElementById("status-hint").textContent = "Nada para espera — adicione itens ou selecione cliente";
      return;
    }
    const firstName =
      s.client.nome !== "Consumidor final"
        ? s.client.nome.split(" ")[0]
        : prompt("Nome do cliente (espera/camarim):", "") || "Cliente";
    s.status = "espera";
    s.esperaLabel = firstName;
    s.esperaPriority = s.lines.length >= 5 ? 2 : 1;
    s.updatedAt = Date.now();
    createSession();
    document.getElementById("status-hint").textContent =
      "Espera · " + firstName + " — nova sessão iniciada";
  }

  function todayKey() {
    return new Date().toISOString().slice(0, 10);
  }

  function getDailyGoalProgress() {
    const data = loadJson(LS_GOAL, { date: "", total: 0 });
    if (data.date !== todayKey()) return { total: 0, target: DAILY_TARGET };
    return { total: data.total || 0, target: DAILY_TARGET };
  }

  function addToDailyGoal(amount) {
    const data = loadJson(LS_GOAL, { date: "", total: 0 });
    if (data.date !== todayKey()) {
      data.date = todayKey();
      data.total = 0;
    }
    data.total = (data.total || 0) + amount;
    saveJson(LS_GOAL, data);
    renderGoalStatus();
  }

  function renderGoalStatus() {
    const el = document.getElementById("status-goal");
    if (!el) return;
    const { total, target } = getDailyGoalProgress();
    const pct = target > 0 ? Math.min(100, Math.round((total / target) * 100)) : 0;
    el.textContent = "Meta " + pct + "%";
    el.title = money(total) + " de " + money(target) + " hoje";
  }

  function syncTrainingUI() {
    const app = document.getElementById("pos-app");
    const btn = document.getElementById("btn-training");
    const banner = document.getElementById("training-banner");
    if (app) app.classList.toggle("training", trainingMode);
    document.body.classList.toggle("training", trainingMode);
    if (btn) btn.classList.toggle("active", trainingMode);
    if (banner) banner.hidden = !trainingMode;
    const modeEl = document.getElementById("status-mode");
    if (modeEl && mode === "pdv") {
      modeEl.textContent = trainingMode ? "Modo PDV · TREINO" : "Modo PDV";
    }
  }

  function setTrainingMode(on) {
    trainingMode = !!on;
    localStorage.setItem(LS_TRAINING, trainingMode ? "1" : "0");
    syncTrainingUI();
    document.getElementById("status-hint").textContent = trainingMode
      ? "Modo treinamento ativo — vendas não vão ao caixa real"
      : "Modo treinamento desligado";
  }

  function syncConsultaUI() {
    const btn = document.getElementById("btn-consulta");
    if (btn) btn.classList.toggle("active", consultaMode);
  }

  function normFormaPg(fp) {
    const s = String(fp || "")
      .trim()
      .toLowerCase();
    if (!s) return "";
    if (["dinheiro", "cash", "especie", "espécie"].includes(s)) return "dinheiro";
    if (s === "pix") return "pix";
    if (["debito", "débito", "debit"].includes(s)) return "debito";
    if (["credito", "crédito", "credit"].includes(s)) return "credito";
    if (["voucher", "vale", "vr", "va"].includes(s)) return "voucher";
    return s;
  }

  function productCategoria(productId) {
    const p = SAMPLE.find((x) => String(x.id) === String(productId));
    return (p && (p.cat || p.categoria)) || "";
  }

  function campaignActiveToday(camp) {
    if (!camp || camp.active === false) return false;
    const today = new Date().toISOString().slice(0, 10);
    if (camp.start && today < String(camp.start).slice(0, 10)) return false;
    if (camp.end && today > String(camp.end).slice(0, 10)) return false;
    return true;
  }

  function calcCampaignsForSession(s, formaPg) {
    let discount = 0;
    const labels = [];
    const hints = [];
    const want = formaPg == null ? null : normFormaPg(formaPg);
    (liveCampaigns || []).forEach((camp) => {
      if (!campaignActiveToday(camp)) return;
      const campFp = normFormaPg(camp.forma_pg);
      if (campFp) {
        if (want == null) {
          // PDV: só hint (desconto no caixa com essa forma)
        } else if (want !== campFp) {
          return;
        }
      }
      const cat = String(camp.categoria || "").trim().toLowerCase();
      const pct = Number(camp.discount_pct) || 0;
      if (!cat || pct <= 0) return;
      const matching = (s.lines || []).filter((l) => {
        if (l.troca || Number(l.qtd) < 0) return false;
        return productCategoria(l.id).trim().toLowerCase() === cat;
      });
      if (!matching.length) return;
      const sub = matching.reduce((sum, l) => sum + lineTotal(l), 0);
      const d = Math.round(sub * pct) / 100;
      const label = (camp.name || "Campanha") + " −" + pct + "%";
      if (campFp && want == null) {
        hints.push(label + " (no " + camp.forma_pg + ": −" + money(d) + ")");
        return;
      }
      discount += d;
      labels.push(label + " −" + money(d));
    });
    return { discount, label: labels.join(" · "), hints };
  }

  function calcPromoForSession(s, formaPg) {
    let kitsDiscount = 0;
    const labels = [];
    PROMO_RULES.forEach((rule) => {
      const matching = s.lines.filter((l) => rule.productIds.includes(l.id) && !l.troca);
      if (!matching.length) return;
      const qty = matching.reduce((sum, l) => sum + (Number(l.qtd) || 0), 0);
      const sub = matching.reduce((sum, l) => sum + lineTotal(l), 0);
      if (rule.pct && qty >= (rule.minQty || 1)) {
        const d = (sub * rule.pct) / 100;
        kitsDiscount += d;
        labels.push(rule.label + " −" + money(d));
      } else if (rule.buy && rule.pay && qty >= rule.buy) {
        const freeUnits = Math.floor(qty / rule.buy) * (rule.buy - rule.pay);
        const avgPrice = sub / qty;
        const d = freeUnits * avgPrice;
        kitsDiscount += d;
        labels.push(rule.label + " −" + money(d));
      }
    });
    const camps = calcCampaignsForSession(s, formaPg === undefined ? null : formaPg);
    const discount = kitsDiscount + (camps.discount || 0);
    const allLabels = labels.concat(camps.label ? [camps.label] : []);
    if (camps.hints && camps.hints.length) allLabels.push(...camps.hints);
    return {
      discount,
      kitsDiscount,
      campaignsDiscount: camps.discount || 0,
      label: allLabels.join(" · ") || "",
      hints: camps.hints || [],
    };
  }

  function sessionPromoAmount(s) {
    return calcPromoForSession(s, null).discount;
  }

  async function loadCampaignsFromApi() {
    const api = window.AuthService && window.AuthService.api;
    if (!api) return;
    try {
      const data = await api("/api/pos/campaigns");
      if (data.status === "ok") liveCampaigns = data.campaigns || [];
    } catch (_) {
      liveCampaigns = [];
    }
  }

  function refreshCaixaDueForForma() {
    if (!activeFilaPedido) return;
    const fake = {
      lines: activeFilaPedido.lines || [],
      orderDisc: activeFilaPedido.orderDisc || { type: "val", value: 0 },
      orderAcr: activeFilaPedido.orderAcr || { type: "val", value: 0 },
    };
    const sub = (fake.lines || []).reduce((sum, l) => {
      if (l.troca || Number(l.qtd) < 0) return sum;
      return sum + (Number(l.qtd) || 0) * (Number(l.preco) || 0);
    }, 0);
    const disc = Number(activeFilaPedido.discount) || 0;
    const acr = Number(activeFilaPedido.surcharge) || 0;
    const kits = Number(activeFilaPedido.promo_kits) || 0;
    const camps = calcCampaignsForSession(fake, caixaFormaPg || "Dinheiro");
    caixaDue = Math.max(0, Math.round((sub - disc + acr - kits - (camps.discount || 0)) * 100) / 100);
    document.getElementById("caixa-due").textContent = money(caixaDue);
    const hintBits = [];
    if (camps.discount > 0) hintBits.push("Campanha −" + money(camps.discount));
    if (camps.label) hintBits.push(camps.label);
    document.getElementById("pay-hint").textContent =
      (caixaFormaPg || "Dinheiro") +
      " · a receber " +
      money(caixaDue) +
      (hintBits.length ? " · " + hintBits.join(" · ") : "");
  }

  function renderSessions() {
    const rail = document.getElementById("pos-sessions");
    if (!rail) return;
    const list = sessions
      .map((s) => {
        const n = s.lines.length;
        const total = sessionTotal(s);
        const isActive = s.id === activeSessionId;
        let statusLabel = "ativa";
        if (s.status === "suspended") statusLabel = "susp.";
        else if (s.status === "espera") statusLabel = "espera";
        const clientShort =
          s.status === "espera" && s.esperaLabel
            ? s.esperaLabel
            : s.client.nome.length > 10
              ? s.client.nome.slice(0, 9) + "…"
              : s.client.nome;
        const esperaCls = s.status === "espera" ? " espera" : "";
        const prioBadge =
          s.status === "espera" && s.esperaPriority >= 2
            ? '<span class="ss-priority">!</span>'
            : "";
        return `
      <button type="button" class="ss-btn ${isActive ? "active" : ""} ${s.status === "suspended" ? "suspended" : ""}${esperaCls}"
        data-session="${s.id}" title="${s.client.nome}${s.esperaLabel ? " · espera: " + s.esperaLabel : ""}">
        <strong class="ss-client">${clientShort}</strong>
        <span class="ss-meta">${n} it · ${money(total)}</span>
        <span class="ss-time">${relTime(s.updatedAt)}</span>
        <span class="ss-status">${statusLabel}</span>
        ${prioBadge}
        ${n > 0 && s.status === "suspended" ? `<span class="ss-badge">${n}</span>` : ""}
        ${s.status === "espera" ? '<span class="ss-espera-badge">espera</span>' : ""}
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
    const promo = sessionPromoAmount(s);
    return Math.max(0, sessionSubtotal(s) - sessionDiscAmount(s) + sessionAcrAmount(s) - promo);
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
    const sess = document.getElementById("caixa-ctx-session");
    if (sess) sess.hidden = ctx !== "session";
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

  async function applyCashMove() {
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
    const payload = {
      kind: cashMovePad.kind,
      value: val,
      reason,
      docType,
      docRef,
      terminal_id: (posContexto && posContexto.terminal && posContexto.terminal.id) || "",
      estabelecimento_id:
        (posContexto && posContexto.estabelecimento && posContexto.estabelecimento.id) || "",
    };
    const api = window.AuthService && window.AuthService.api;
    let saved = null;
    if (api) {
      try {
        const res = await api("/api/pos/caixa/movimentos", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        if (res.status === "ok") saved = res.movimento;
        else {
          document.getElementById("status-hint").textContent = res.message || "Falha ao gravar";
          return;
        }
      } catch (_) {
        document.getElementById("status-hint").textContent = "Falha de rede ao gravar movimento";
        return;
      }
    }
    cashMoves.unshift(
      saved || {
        id: Date.now(),
        kind: cashMovePad.kind,
        value: val,
        reason,
        docType,
        docRef,
        at: Date.now(),
      }
    );
    const label = cashMovePad.kind === "in" ? "Suprimento" : "Sangria";
    document.getElementById("status-hint").textContent =
      label + " " + money(val) + " · " + reason + (docRef ? " · doc " + docRef : "") + " · gravado";
    cashMovePad = null;
    setCaixaCtx("default");
    renderCashMoveLog();
    await loadCaixaSessao();
  }

  async function loadCashMovesFromApi() {
    const api = window.AuthService && window.AuthService.api;
    if (!api) return;
    const tid = (posContexto && posContexto.terminal && posContexto.terminal.id) || "";
    const qs = new URLSearchParams({ limit: "30" });
    if (tid) qs.set("terminal_id", tid);
    if (caixaSessao && caixaSessao.id) qs.set("sessao_id", caixaSessao.id);
    try {
      const data = await api("/api/pos/caixa/movimentos?" + qs.toString());
      if (data.status === "ok") {
        cashMoves = (data.movimentos || []).map((m) => ({
          ...m,
          at: m.at ? Date.parse(m.at) || m.at : Date.now(),
        }));
        renderCashMoveLog();
      }
    } catch (_) {}
  }

  let caixaSessao = null;
  let caixaResumo = null;
  let sessaoPad = null; // { mode: 'open'|'close', cents }

  function syncSessaoUI() {
    const label = document.getElementById("caixa-sessao-label");
    const btnOpen = document.getElementById("btn-abrir-caixa");
    const btnClose = document.getElementById("btn-fechar-caixa");
    if (!label) return;
    if (caixaSessao && caixaSessao.status === "aberta") {
      const esp = caixaResumo ? caixaResumo.esperado_dinheiro : caixaSessao.fundo_troco;
      label.textContent =
        "Sessão " +
        caixaSessao.id +
        " · fundo " +
        money(caixaSessao.fundo_troco || 0) +
        " · esperado " +
        money(esp || 0);
      if (btnOpen) btnOpen.hidden = true;
      if (btnClose) btnClose.hidden = false;
    } else {
      label.textContent = "Caixa fechado — abra com fundo de troco";
      if (btnOpen) btnOpen.hidden = false;
      if (btnClose) btnClose.hidden = true;
    }
  }

  async function loadCaixaSessao() {
    const api = window.AuthService && window.AuthService.api;
    if (!api) return;
    try {
      const data = await api("/api/pos/caixa/sessao");
      if (data.status === "ok") {
        caixaSessao = data.sessao || null;
        caixaResumo = data.resumo || null;
      }
    } catch (_) {
      caixaSessao = null;
      caixaResumo = null;
    }
    syncSessaoUI();
  }

  function openSessaoPad(mode) {
    setMode("caixa");
    if (numpad) closeNumpad();
    sessaoPad = { mode, cents: 0 };
    const title = document.getElementById("sessao-title");
    const sub = document.getElementById("sessao-sub");
    const label = document.getElementById("sessao-value-label");
    const resumoEl = document.getElementById("sessao-resumo");
    if (mode === "open") {
      title.textContent = "Abrir caixa";
      sub.textContent = "Informe o fundo de troco (dinheiro inicial)";
      label.textContent = "Fundo de troco";
      if (resumoEl) {
        resumoEl.hidden = true;
        resumoEl.innerHTML = "";
      }
    } else {
      title.textContent = "Fechar caixa";
      sub.textContent = "Conte o dinheiro físico na gaveta";
      label.textContent = "Dinheiro contado";
      if (resumoEl && caixaResumo) {
        const pg = Object.keys(caixaResumo.totais_pg || {})
          .map((k) => k + ": " + money(caixaResumo.totais_pg[k]))
          .join(" · ");
        resumoEl.hidden = false;
        resumoEl.innerHTML =
          "<p class='mode-note' style='margin:0'>" +
          "Vendas: " +
          (caixaResumo.vendas_count || 0) +
          " · total " +
          money(caixaResumo.vendas_total || 0) +
          (pg ? "<br>" + pg : "") +
          "<br>Fundo " +
          money(caixaResumo.fundo_troco || 0) +
          " + Dinheiro " +
          money(caixaResumo.dinheiro_vendas || 0) +
          " + Supr. " +
          money(caixaResumo.suprimentos || 0) +
          " − Sangria " +
          money(caixaResumo.sangrias || 0) +
          " = <strong>esperado " +
          money(caixaResumo.esperado_dinheiro || 0) +
          "</strong></p>";
      }
    }
    document.getElementById("sessao-display").textContent = money(0);
    setCaixaCtx("session");
  }

  function sessaoKey(k) {
    if (!sessaoPad) return;
    if (k === "bk") sessaoPad.cents = Math.floor((sessaoPad.cents || 0) / 10);
    else if (k === "00") sessaoPad.cents = Math.min((sessaoPad.cents || 0) * 100, 999999999);
    else if (/^\d$/.test(k))
      sessaoPad.cents = Math.min((sessaoPad.cents || 0) * 10 + Number(k), 999999999);
    document.getElementById("sessao-display").textContent = money((sessaoPad.cents || 0) / 100);
  }

  function cancelSessaoPad() {
    sessaoPad = null;
    setCaixaCtx("default");
  }

  async function applySessaoPad() {
    if (!sessaoPad) return;
    const api = window.AuthService && window.AuthService.api;
    if (!api) return;
    const val = (sessaoPad.cents || 0) / 100;
    if (sessaoPad.mode === "open") {
      const res = await api("/api/pos/caixa/sessao", {
        method: "POST",
        body: JSON.stringify({
          fundo_troco: val,
          terminal_id: (posContexto && posContexto.terminal && posContexto.terminal.id) || "",
          estabelecimento_id:
            (posContexto && posContexto.estabelecimento && posContexto.estabelecimento.id) || "",
        }),
      });
      if (res.status !== "ok") {
        document.getElementById("status-hint").textContent = res.message || "Falha ao abrir";
        return;
      }
      caixaSessao = res.sessao;
      caixaResumo = res.resumo;
      document.getElementById("status-hint").textContent =
        "Caixa aberto · fundo " + money(val);
    } else {
      const res = await api("/api/pos/caixa/sessao/fechar", {
        method: "POST",
        body: JSON.stringify({
          sessao_id: caixaSessao && caixaSessao.id,
          contado: val,
        }),
      });
      if (res.status !== "ok") {
        document.getElementById("status-hint").textContent = res.message || "Falha ao fechar";
        return;
      }
      const dif = (res.sessao && res.sessao.diferenca) || 0;
      document.getElementById("status-hint").textContent =
        "Caixa fechado · contado " +
        money(val) +
        " · esperado " +
        money((res.sessao && res.sessao.esperado) || 0) +
        " · Δ " +
        money(dif);
      caixaSessao = null;
      caixaResumo = null;
    }
    sessaoPad = null;
    setCaixaCtx("default");
    syncSessaoUI();
    await loadCashMovesFromApi();
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
      const chips = document.getElementById("weight-chips");
      if (chips) chips.hidden = numpad.kind !== "weight";
    } else {
      document.getElementById("caixa-numpad-title").textContent = numpad.title;
      document.getElementById("caixa-numpad-sub").textContent = numpad.sub;
      document.getElementById("caixa-numpad-display").textContent = formatDisplay(
        numpad.raw,
        numpad.allowDecimal
      );
    }
  }

  function applyWeightPreset(val) {
    if (!numpad || numpad.kind !== "weight") return;
    if (val === "balanca") {
      // Mock de balança: peso entre 0,320 e 2,480 kg
      const w = Math.round((0.32 + Math.random() * 2.16) * 1000) / 1000;
      numpad.raw = String(w);
      document.getElementById("status-hint").textContent =
        "Balança (mock) · " + String(w).replace(".", ",") + " kg";
    } else {
      numpad.raw = String(val);
    }
    syncNumpadUI();
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
        const line = s.lines[idx];
        if (!line.troca && !line.servico) {
          const p = SAMPLE.find((x) => x.id === line.id);
          if (p) {
            const gate = stockGate(p, Math.floor(val), s, { excludeIdx: idx });
            // wantAdd = full new qty because excludeIdx removes current line from cart sum
            if (!gate.ok) {
              applyStockGateFailure(p, gate);
              return;
            }
          }
        }
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
        const line = s.lines[idx];
        if (!line.troca) {
          const p = SAMPLE.find((x) => x.id === line.id);
          if (p) {
            const gate = stockGate(p, 1, s, { excludeIdx: idx });
            if (!gate.ok) {
              applyStockGateFailure(p, gate);
              return;
            }
          }
        }
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

  function syncTextPhrases() {
    const note = document.getElementById("note-phrases");
    const svc = document.getElementById("service-phrases");
    if (note) note.hidden = textEditorMode !== "note";
    if (svc) svc.hidden = textEditorMode !== "service";
  }

  function openNoteEditor() {
    const s = getSession();
    if (!s || s.selectedLine < 0 || !s.lines[s.selectedLine]) return;
    const line = s.lines[s.selectedLine];
    textEditorMode = line.servico ? "service" : "note";
    document.getElementById("text-title").textContent =
      textEditorMode === "service" ? "Descrição do serviço" : "Observação";
    document.getElementById("text-sub").textContent = line.nome;
    document.getElementById("text-editor").value =
      textEditorMode === "service" ? line.servicoDesc || line.obs || "" : line.obs || "";
    document.getElementById("text-editor").placeholder =
      textEditorMode === "service"
        ? "Descreva o serviço prestado…"
        : "Digite a observação…";
    syncTextPhrases();
    setSmartCtx("text", textEditorMode === "service" ? "Serviço" : "Observação");
    document.getElementById("text-editor").focus();
  }

  function openServiceEditor() {
    const s = getSession();
    if (!s || s.selectedLine < 0 || !s.lines[s.selectedLine]) return;
    textEditorMode = "service";
    const line = s.lines[s.selectedLine];
    document.getElementById("text-title").textContent = "Descrição do serviço";
    document.getElementById("text-sub").textContent = line.nome;
    document.getElementById("text-editor").value = line.servicoDesc || "";
    document.getElementById("text-editor").placeholder = "Descreva o serviço prestado…";
    syncTextPhrases();
    setSmartCtx("text", "Serviço");
    document.getElementById("text-editor").focus();
  }

  function confirmText() {
    const s = getSession();
    if (s && s.selectedLine >= 0 && s.lines[s.selectedLine]) {
      const val = (document.getElementById("text-editor").value || "").trim();
      if (textEditorMode === "service") {
        pushUndo("descrição serviço");
        s.lines[s.selectedLine].servicoDesc = val;
        s.lines[s.selectedLine].servico = true;
      } else {
        pushUndo("observação");
        s.lines[s.selectedLine].obs = val;
      }
      renderOrder();
    }
    textEditorMode = "note";
    syncTextPhrases();
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

  function similarProductsHtml(product) {
    if (!product.similares || !product.similares.length) return "";
    const items = product.similares
      .map((id) => SAMPLE.find((p) => p.id === id))
      .filter(Boolean);
    if (!items.length) return "";
    return (
      '<div class="similar-block"><h4>Sugestões similares</h4>' +
      items
        .map(
          (p) =>
            `<button type="button" class="similar-item" data-similar-id="${p.id}">
              <span>${p.nome}</span>
              <strong>${money(p.preco)}</strong>
              <em class="similar-act">Trocar</em>
            </button>`
        )
        .join("") +
      "</div>"
    );
  }

  function bindSimilarClicks(container, onPick) {
    container.querySelectorAll("[data-similar-id]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const p = SAMPLE.find((x) => x.id === Number(btn.dataset.similarId));
        if (p) onPick(p);
      });
    });
  }

  function openSimilarPanel(product) {
    const list = document.getElementById("similar-list");
    document.getElementById("similar-sub").textContent = product.nome + " — indisponível";
    list.innerHTML = similarProductsHtml(product) || '<p class="mode-note">Nenhuma alternativa cadastrada.</p>';
    bindSimilarClicks(list, (p) => {
      setSmartCtx("summary");
      addProduct(p.id, { skipRecall: false, fromSimilar: true });
    });
    setSmartCtx("similar");
  }

  function openPriceConsult(product) {
    pendingPriceProduct = product;
    document.getElementById("price-consult-name").textContent = product.nome;
    document.getElementById("price-consult-price").textContent = money(product.preco);
    const st = STOCK_LABELS[product.stockStatus || "local"] || STOCK_LABELS.local;
    const promiseLabel =
      (product.promise && product.promise.label) || st.long;
    const qtyBit =
      product.stockStatus === "local" && product.stock != null
        ? ` · ${product.stock} un.`
        : "";
    document.getElementById("price-consult-stock").innerHTML =
      `<span class="stock-badge ${st.cls}">${st.short}</span> · ${promiseLabel}${qtyBit}`;
    setSmartCtx("price");
  }

  function cartQtyForProduct(session, productId, opts) {
    opts = opts || {};
    if (!session) return 0;
    return (session.lines || []).reduce((sum, l) => {
      if (Number(l.id) !== Number(productId)) return sum;
      if (l.troca || l.servico) return sum;
      if (opts.excludeIdx != null && opts.excludeIdx === session.lines.indexOf(l)) return sum;
      const q = Number(l.qtd) || 0;
      return sum + (q > 0 ? q : 0);
    }, 0);
  }

  /**
   * Endurecimento estoque:
   * - serviço: ok
   * - só vende saldo local; branch/transit/none bloqueiam
   * - qty no carrinho não pode passar do stock local
   */
  function stockGate(product, wantAdd, session, opts) {
    opts = opts || {};
    if (!product) return { ok: false, message: "Produto inválido" };
    if (product.servico) return { ok: true };
    if (trainingMode) return { ok: true }; // treino não consome regra dura
    const st = product.stockStatus || "local";
    if (st !== "local") {
      const label =
        (product.promise && product.promise.label) ||
        (STOCK_LABELS[st] && STOCK_LABELS[st].long) ||
        "Indisponível nesta loja";
      return {
        ok: false,
        message: label,
        openSimilar: st === "none",
        openStock: st === "branch" || st === "transit",
      };
    }
    const stock = Number(product.stock);
    const max = Number.isFinite(stock) ? stock : 0;
    if (max <= 0) {
      return { ok: false, message: "Sem saldo nesta loja", openSimilar: true };
    }
    const inCart = cartQtyForProduct(session, product.id, { excludeIdx: opts.excludeIdx });
    const need = Number(wantAdd) || 0;
    if (inCart + need > max) {
      const restante = Math.max(0, max - inCart);
      return {
        ok: false,
        message:
          restante > 0
            ? "Só restam " + restante + " un. nesta loja"
            : "Saldo esgotado nesta loja (" + max + " un.)",
      };
    }
    return { ok: true, max: max };
  }

  function applyStockGateFailure(product, gate) {
    document.getElementById("status-hint").textContent = gate.message || "Estoque insuficiente";
    if (gate.openSimilar) openSimilarPanel(product);
    else if (gate.openStock) openStock(product);
  }

  function sessionHasTroca(s) {
    return !!(s && (s.lines || []).some((l) => l.troca || Number(l.qtd) < 0));
  }

  function syncExchangeAprovHint() {
    const hint = document.getElementById("exchange-aprov-hint");
    const s = getSession();
    if (!hint) return;
    if (s && s.trocaAprovacao) {
      hint.hidden = false;
      hint.textContent =
        "Autorizado por " +
        (s.trocaAprovacao.nome || s.trocaAprovacao.usuario) +
        (s.trocaAprovacao.motivo ? " · " + s.trocaAprovacao.motivo : "");
    } else {
      hint.hidden = true;
      hint.textContent = "";
    }
  }

  function openMgrAuthForExchange() {
    const err = document.getElementById("mgr-auth-error");
    if (err) {
      err.hidden = true;
      err.textContent = "";
    }
    const userEl = document.getElementById("mgr-user");
    const passEl = document.getElementById("mgr-pass");
    const motEl = document.getElementById("mgr-motivo");
    if (userEl && !userEl.value) userEl.value = "bruno";
    if (passEl) passEl.value = "";
    if (motEl) motEl.value = "";
    setSmartCtx("mgr-auth");
    if (passEl) passEl.focus();
  }

  async function applyMgrAuth() {
    const api = window.AuthService && window.AuthService.api;
    const err = document.getElementById("mgr-auth-error");
    if (!api) {
      if (err) {
        err.hidden = false;
        err.textContent = "Sem API de autenticação";
      }
      return;
    }
    const usuario = (document.getElementById("mgr-user").value || "").trim();
    const senha = document.getElementById("mgr-pass").value || "";
    const motivo = (document.getElementById("mgr-motivo").value || "").trim();
    const res = await api("/api/pos/autorizar-gerente", {
      method: "POST",
      body: JSON.stringify({ usuario, senha, motivo }),
    });
    if (!res || res.status !== "ok") {
      if (err) {
        err.hidden = false;
        err.textContent = (res && res.message) || "Não autorizado";
      }
      return;
    }
    const s = getSession();
    if (!s) return;
    s.trocaAprovacao = res.aprovacao;
    document.getElementById("status-hint").textContent =
      "Troca autorizada por " + (res.aprovacao.nome || res.aprovacao.usuario);
    openExchangePanelAfterAuth();
  }

  async function renderExchangeResults() {
    const q = (document.getElementById("exchange-search").value || "").trim();
    const box = document.getElementById("exchange-results");
    box.innerHTML = '<p class="mode-note">Buscando vendas…</p>';
    const api = window.AuthService && window.AuthService.api;
    let list = [];
    if (api) {
      try {
        const qs = new URLSearchParams({ limit: "30" });
        if (q) qs.set("q", q);
        const data = await api("/api/pos/vendas?" + qs.toString());
        if (data.status === "ok") list = data.vendas || [];
      } catch (_) {
        list = [];
      }
    }
    if (!list.length && pastSalesCache.length) {
      const digits = q.replace(/\D/g, "");
      list = pastSalesCache.filter((sale) => {
        if (!q) return true;
        return (
          String(sale.nfce).includes(digits || q) ||
          String(sale.cpf).replace(/\D/g, "").includes(digits) ||
          String(sale.client || "").toLowerCase().includes(q.toLowerCase())
        );
      });
    }
    pastSalesCache = list;
    if (!list.length) {
      box.innerHTML = '<p class="mode-note">Nenhuma venda encontrada.</p>';
      return;
    }
    box.innerHTML = list
      .map(
        (sale, i) => `
      <button type="button" class="exchange-sale" data-sale="${i}">
        <strong>NFC-e ${sale.nfce}</strong>
        <span>${sale.client} · ${sale.date}</span>
        <em>${money(sale.total)} · ${sale.lines.length} itens</em>
      </button>`
      )
      .join("");
    box.querySelectorAll("[data-sale]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const sale = list[Number(btn.dataset.sale)];
        if (sale) loadExchangeSale(sale);
      });
    });
  }

  function loadExchangeSale(sale) {
    const s = getSession();
    if (!s) return;
    if (!s.trocaAprovacao && !trainingMode) {
      openMgrAuthForExchange();
      document.getElementById("status-hint").textContent =
        "Peça a senha do gerente para carregar a troca";
      return;
    }
    pushUndo("troca/devolução");
    sale.lines.forEach((line) => {
      s.lines.push({
        id: line.id,
        nome: line.nome + " (troca)",
        preco: line.preco,
        qtd: -Math.abs(line.qtd),
        descPct: 0,
        troca: true,
        obs: "Troca NFC-e " + sale.nfce,
      });
    });
    if (s.trocaAprovacao) {
      s.trocaAprovacao = {
        ...s.trocaAprovacao,
        venda_ref: String(sale.nfce || sale.id || ""),
      };
    }
    s.selectedLine = s.lines.length - 1;
    setSmartCtx("summary");
    renderOrder();
    const who = s.trocaAprovacao
      ? " · aut. " + (s.trocaAprovacao.nome || s.trocaAprovacao.usuario)
      : "";
    document.getElementById("status-hint").textContent =
      "Troca carregada · NFC-e " + sale.nfce + " · " + sale.lines.length + " itens" + who;
  }

  function openExchangePanelAfterAuth() {
    document.getElementById("exchange-search").value = "";
    syncExchangeAprovHint();
    renderExchangeResults();
    setSmartCtx("exchange");
    document.getElementById("exchange-search").focus();
  }

  function openExchangePanel() {
    const s = getSession();
    if (trainingMode) {
      if (s && !s.trocaAprovacao) {
        s.trocaAprovacao = {
          user_id: "treino",
          usuario: "treino",
          nome: "TREINO",
          role: "gerente",
          at: new Date().toISOString(),
          motivo: "modo treinamento",
        };
      }
      openExchangePanelAfterAuth();
      return;
    }
    if (s && s.trocaAprovacao) {
      openExchangePanelAfterAuth();
      return;
    }
    openMgrAuthForExchange();
  }

  function findProductByCode(code) {
    const q = (code || "").toLowerCase().trim();
    if (!q) return null;
    return (
      SAMPLE.find(
        (p) =>
          String(p.id) === q ||
          (p.sku && p.sku.toLowerCase() === q) ||
          (p.ean && p.ean.includes(q.replace(/\D/g, ""))) ||
          p.nome.toLowerCase().includes(q)
      ) || null
    );
  }

  function parseCompositeBarcode(raw) {
    const s = (raw || "").trim();
    if (!s) return null;
    const patterns = [
      /^(\d+)\*([a-z0-9]+)$/i,
      /^([a-z0-9]+)\*(\d+)$/i,
      /^(\d+)x([a-z0-9]+)$/i,
    ];
    for (const re of patterns) {
      const m = s.match(re);
      if (m) {
        let qty;
        let code;
        if (/^\d+$/.test(m[1])) {
          qty = Number(m[1]);
          code = m[2];
        } else {
          qty = Number(m[2]);
          code = m[1];
        }
        const product = findProductByCode(String(code));
        if (product && qty > 0) return { product, qty };
      }
    }
    return null;
  }

  function handleSearchEnter() {
    const input = document.getElementById("prod-search");
    const raw = (input.value || "").trim();
    if (!raw) return;

    const composite = parseCompositeBarcode(raw);
    if (composite) {
      input.value = "";
      renderProducts();
      if (consultaMode) {
        openPriceConsult(composite.product);
        document.getElementById("status-hint").textContent =
          composite.qty + "× " + composite.product.nome + " (consulta)";
        return;
      }
      const s = getSession();
      if (!s) return;
      if (composite.product.variants) {
        openVariantPanel(composite.product);
        return;
      }
      if (composite.product.alertas && composite.product.alertas.includes("recall")) {
        pendingRecallProduct = composite.product;
        if (!confirm("RECALL: " + composite.product.nome + " — confirmar adição?")) {
          pendingRecallProduct = null;
          return;
        }
        pendingRecallProduct = null;
      }
      const gate = stockGate(composite.product, composite.qty, s);
      if (!gate.ok) {
        applyStockGateFailure(composite.product, gate);
        return;
      }
      pushUndo("adicionar item");
      const hit = s.lines.find((l) => l.id === composite.product.id && !l.peso && !l.variantKey && !l.troca);
      if (hit) hit.qtd += composite.qty;
      else
        s.lines.push({
          id: composite.product.id,
          nome: composite.product.nome,
          preco: composite.product.preco,
          qtd: composite.qty,
          descPct: 0,
        });
      s.selectedLine = s.lines.findIndex(
        (l) => l.id === composite.product.id && !l.peso && !l.variantKey && !l.troca
      );
      trackRecent(composite.product.id);
      renderOrder();
      document.getElementById("status-hint").textContent =
        composite.qty + "× " + composite.product.nome + " adicionado";
      return;
    }

    const list = filteredProducts();
    if (!list.length) {
      document.getElementById("status-hint").textContent = "Nenhum produto encontrado";
      return;
    }
    input.value = "";
    renderProducts();
    if (consultaMode) openPriceConsult(list[0]);
    else addProduct(list[0].id);
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
    document.getElementById("stock-body").innerHTML =
      stockMessageFor(product) + similarProductsHtml(product);
    bindSimilarClicks(document.getElementById("stock-body"), (p) => {
      setSmartCtx("summary");
      addProduct(p.id, { fromSimilar: true });
    });
    setSmartCtx("stock");
  }

  function openVariantPanel(product) {
    pendingVariant = product;
    variantPick = {
      cor: product.variants.cores[0] || "",
      tamanho: product.variants.tamanhos[0] || "",
    };
    document.getElementById("variant-sub").textContent =
      product.nome + " · " + money(variantPrice(product, variantPick.cor, variantPick.tamanho));
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
    document.getElementById("variant-sub").textContent =
      pendingVariant.nome +
      " · " +
      money(variantPrice(pendingVariant, variantPick.cor, variantPick.tamanho));
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
      preco: variantPrice(pendingVariant, variantPick.cor, variantPick.tamanho),
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

  function closeShowcase() {
    showcaseState = null;
    const el = document.getElementById("showcase");
    el.hidden = true;
    el.classList.remove("open");
  }

  function openShowcase(product) {
    if (!product) return;
    if (consultaMode) {
      openPriceConsult(product);
      return;
    }
    showcaseState = {
      product,
      fotoIdx: 0,
      cor: product.variants?.cores?.[0] || "",
      tamanho: product.variants?.tamanhos?.[0] || "",
    };
    const el = document.getElementById("showcase");
    el.hidden = false;
    el.classList.add("open");
    renderShowcase();
  }

  function renderShowcase() {
    if (!showcaseState) return;
    const p = showcaseState.product;
    const fotos = productPhotos(p);
    if (showcaseState.fotoIdx >= fotos.length) showcaseState.fotoIdx = 0;
    if (showcaseState.fotoIdx < 0) showcaseState.fotoIdx = fotos.length - 1;
    const img = fotos[showcaseState.fotoIdx] || FALLBACK_FOTO;
    document.getElementById("showcase-img").src = img;
    document.getElementById("showcase-img").alt = p.nome;
    document.getElementById("showcase-name").textContent = p.nome;
    document.getElementById("showcase-meta").textContent =
      (p.cat || "") +
      (p.subcat ? " · " + p.subcat : "") +
      " · SKU " +
      p.sku +
      (p.ean ? " · EAN " + p.ean : "");
    document.getElementById("showcase-desc").textContent =
      p.descricao || "Sem descrição detalhada neste mock.";
    const st = STOCK_LABELS[p.stockStatus || "local"] || STOCK_LABELS.local;
    document.getElementById("showcase-stock").innerHTML =
      stockBadgeHtml(p) +
      ` <span class="showcase-stock-text">${st.long || st.short}</span>` +
      (alertBadgesHtml(p) ? `<div class="showcase-alerts">${alertBadgesHtml(p)}</div>` : "");

    const price = p.variants
      ? variantPrice(p, showcaseState.cor, showcaseState.tamanho)
      : p.preco;
    document.getElementById("showcase-price").innerHTML =
      money(price) +
      (p.peso ? "<small>/kg</small>" : p.servico ? "<small>/hora</small>" : "");

    document.getElementById("showcase-dots").innerHTML = fotos
      .map(
        (_, i) =>
          `<button type="button" class="dot ${i === showcaseState.fotoIdx ? "active" : ""}" data-dot="${i}" aria-label="Foto ${i + 1}"></button>`
      )
      .join("");
    document.getElementById("showcase-prev").disabled = fotos.length < 2;
    document.getElementById("showcase-next").disabled = fotos.length < 2;

    const varBox = document.getElementById("showcase-variants");
    if (p.variants) {
      varBox.hidden = false;
      document.getElementById("showcase-cores").innerHTML = p.variants.cores
        .map(
          (c) =>
            `<button type="button" class="swatch ${c === showcaseState.cor ? "active" : ""}" data-scor="${c}">${c}</button>`
        )
        .join("");
      document.getElementById("showcase-tamanhos").innerHTML = p.variants.tamanhos
        .map(
          (t) =>
            `<button type="button" class="swatch size ${t === showcaseState.tamanho ? "active" : ""}" data-stam="${t}">${t}</button>`
        )
        .join("");
    } else {
      varBox.hidden = true;
    }
  }

  function showcaseAddToOrder() {
    if (!showcaseState) return;
    const p = showcaseState.product;
    closeShowcase();

    if (!consultaMode && p.alertas && p.alertas.includes("recall")) {
      if (!confirm("RECALL: " + p.nome + " — produto em recall. Confirmar adição?")) {
        return;
      }
    }

    if (p.variants) {
      const cor = showcaseState.cor || p.variants.cores[0];
      const tamanho = showcaseState.tamanho || p.variants.tamanhos[0];
      addLineToOrder({
        id: p.id,
        nome: p.nome + " (" + cor + " · " + tamanho + ")",
        preco: variantPrice(p, cor, tamanho),
        qtd: 1,
        descPct: 0,
        variantKey: cor + "|" + tamanho,
      });
      if (p.stockStatus === "none") openSimilarPanel(p);
      return;
    }

    addProduct(p.id, { forceAdd: true, skipRecall: true, fromShowcase: true });
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
    if (c.historico && c.historico.length) {
      parts.push("comprou " + c.historico[0].nome);
    }
    if (c.tamanhoUsual) parts.push("tam. usual " + c.tamanhoUsual);
    return parts.join(" · ") || "Cliente";
  }

  function renderClientHistory(c) {
    const el = document.getElementById("client-history");
    if (!el) return;
    const full = MOCK_CUSTOMERS.find((x) => x.id === c.id) || c;
    if (!full.historico || !full.historico.length) {
      el.hidden = true;
      el.innerHTML = "";
      return;
    }
    el.hidden = false;
    const sizeTip = full.tamanhoUsual
      ? `<p class="client-size-tip">Tamanho usual: <strong>${full.tamanhoUsual}</strong></p>`
      : "";
    el.innerHTML =
      sizeTip +
      '<ul class="client-hist-list">' +
      full.historico
        .slice(0, 3)
        .map((h) => `<li><span>${h.nome}</span><em>${h.quando}</em></li>`)
        .join("") +
      "</ul>";
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
    renderClientHistory(c);
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

  function productPhotos(p) {
    if (p.fotos && p.fotos.length) return p.fotos.slice();
    return [p.foto || FALLBACK_FOTO];
  }

  function variantPrice(product, cor, tam) {
    let price = Number(product.preco) || 0;
    if (!product.variants) return price;
    if (cor && product.variants.ajusteCor && product.variants.ajusteCor[cor] != null) {
      price += Number(product.variants.ajusteCor[cor]) || 0;
    }
    if (tam && product.variants.ajusteTam && product.variants.ajusteTam[tam] != null) {
      price += Number(product.variants.ajusteTam[tam]) || 0;
    }
    return Math.round(price * 100) / 100;
  }

  /** Catálogo do varejo = mix da empresa (API ou demo). */
  function catalogPool() {
    return SAMPLE.slice();
  }

  function initials(nome) {
    const parts = String(nome || "")
      .trim()
      .split(/\s+/)
      .filter(Boolean);
    if (!parts.length) return "?";
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }

  function mapApiProduct(p) {
    const id = Number(p.id);
    const pid = Number.isFinite(id) ? id : p.id;
    const unidade = String(p.unidade || "UN").trim().toUpperCase();
    const peso = !!p.peso || unidade === "KG";
    const stock = Number(p.stock);
    const stockNum = Number.isFinite(stock) ? stock : 0;
    let stockStatus = p.stockStatus || "local";
    if (!p.stockStatus && stockNum <= 0) stockStatus = "none";
    const foto = p.foto || FALLBACK_FOTO;
    const fotos = Array.isArray(p.fotos) && p.fotos.length ? p.fotos.slice() : [foto];
    let variants = p.variants || null;
    if (!variants && p.variacoes && typeof p.variacoes === "object") {
      const v = p.variacoes;
      if (v.cores || v.tamanhos || v.colors || v.sizes) {
        variants = {
          cores: v.cores || v.colors || [],
          tamanhos: v.tamanhos || v.sizes || [],
          ajusteCor: v.ajusteCor || {},
          ajusteTam: v.ajusteTam || {},
        };
      }
    }
    const skuRaw = p.sku != null && String(p.sku).trim() !== "" ? String(p.sku) : String(pid);
    const promise = p.promise && typeof p.promise === "object" ? p.promise : null;
    const promiseBranches = Array.isArray(p.promiseBranches) ? p.promiseBranches : [];
    return {
      id: pid,
      nome: p.nome || "Produto",
      preco: Number(p.preco) || 0,
      stock: stockNum,
      cat: p.categoria || p.cat || "Geral",
      subcat: p.sub_categoria || p.subcat || "",
      sku: skuRaw.padStart(6, "0").slice(-12),
      ean: p.codigo_barras || p.ean || "",
      descricao: p.descricao || "",
      foto,
      fotos,
      peso,
      servico: !!p.servico || String(p.categoria || "").toLowerCase() === "serviços",
      stockStatus,
      promise,
      promiseBranches,
      alertas: Array.isArray(p.alertas) ? p.alertas : [],
      similares: Array.isArray(p.similares) ? p.similares : [],
      variants,
      novo: !!p.novo,
      criadoEm: p.criadoEm || p.criado_em || "",
    };
  }

  function mapApiCustomer(p) {
    const docs = p.documents || [];
    const docCpf = docs.find((d) => String(d.document_type || "").toUpperCase() === "CPF");
    const docCnpj = docs.find((d) => String(d.document_type || "").toUpperCase() === "CNPJ");
    const contato =
      (p.contacts || []).find((c) => c.preferred) || (p.contacts || [])[0] || {};
    const nome = p.display_name || p.trade_name || p.legal_name || p.nome || "Cliente";
    return {
      id: String(p.id),
      nome,
      av: initials(nome),
      cpf: (docCpf && docCpf.document_number) || (docCnpj && docCnpj.document_number) || p.cpf || "",
      telefone: contato.phone || contato.mobile || p.telefone || "",
      hint: "",
      crediario: Number(p.crediario) || 0,
      ultimaCompra: p.ultimaCompra || null,
      historico: Array.isArray(p.historico) ? p.historico : [],
      tamanhoUsual: p.tamanhoUsual || "",
    };
  }

  function setDataSource(src, detail) {
    dataSource = src;
    const el = document.getElementById("status-data");
    if (!el) return;
    if (src === "api") {
      el.textContent = "Catálogo: API" + (detail ? " · " + detail : "");
    } else {
      el.textContent = "Catálogo: demo" + (detail ? " · " + detail : "");
    }
  }

  async function loadPosDataFromApi() {
    const api = window.AuthService && window.AuthService.api;
    if (!api) {
      setDataSource("demo", "sem AuthService");
      return;
    }
    try {
      const estabQ =
        (posContexto &&
          posContexto.estabelecimento &&
          (posContexto.estabelecimento.id || posContexto.estabelecimento_id)) ||
        "";
      const [prodRes, partRes] = await Promise.all([
        api("/api/pos/produtos" + (estabQ ? "?estabelecimento_id=" + encodeURIComponent(estabQ) : "")),
        api("/api/pos/parceiros?role=CUSTOMER"),
      ]);
      let nProd = 0;
      let nPart = 0;
      let estabUsed = prodRes && prodRes.estabelecimento_id;
      if (prodRes && prodRes.status === "ok" && Array.isArray(prodRes.produtos) && prodRes.produtos.length) {
        SAMPLE = prodRes.produtos.map(mapApiProduct);
        nProd = SAMPLE.length;
      }
      if (partRes && partRes.status === "ok") {
        const raw = partRes.parceiros || partRes.partners || [];
        if (Array.isArray(raw) && raw.length) {
          MOCK_CUSTOMERS = [CONSUMIDOR_FINAL].concat(raw.map(mapApiCustomer));
          nPart = raw.length;
        }
      }
      if (nProd || nPart) {
        setDataSource(
          "api",
          nProd + " prod" + (estabUsed ? " @ " + estabUsed : "") + " · " + nPart + " clientes"
        );
        document.getElementById("status-hint").textContent =
          "Varejo · catálogo da loja" +
          (estabUsed ? " (" + estabUsed + ")" : "") +
          " · toque no produto para o mostruário";
      } else {
        setDataSource("demo", "API vazia");
      }
    } catch (err) {
      console.warn("[POS] falha ao carregar API — usando demo", err);
      setDataSource("demo", "offline");
    }
  }

  function scoreRelevance(p, q) {
    if (!q) return 0;
    const nome = p.nome.toLowerCase();
    if (nome === q) return 100;
    if (nome.startsWith(q)) return 80;
    if (p.sku === q || String(p.id) === q) return 90;
    if (p.ean && p.ean.includes(q.replace(/\D/g, ""))) return 85;
    if (nome.includes(q)) return 50;
    if ((p.descricao || "").toLowerCase().includes(q)) return 20;
    return 0;
  }

  function priceInRange(preco, range) {
    if (!range) return true;
    if (range === "0-20") return preco <= 20;
    if (range === "20-50") return preco > 20 && preco <= 50;
    if (range === "50-100") return preco > 50 && preco <= 100;
    if (range === "100+") return preco > 100;
    return true;
  }

  function availMatch(p, avail) {
    if (!avail) return true;
    if (avail === "local") return p.stockStatus === "local";
    if (avail === "branch") return p.stockStatus === "branch";
    if (avail === "none") return p.stockStatus === "none";
    if (avail === "disponivel") return p.stockStatus !== "none";
    return true;
  }

  function filteredProducts() {
    const q = (document.getElementById("prod-search").value || "").toLowerCase().trim();
    let list = catalogPool();

    if (catalogTab === "favoritos") {
      list = list.filter((p) => favorites.includes(p.id));
    } else if (catalogTab === "ultimos") {
      list = recentIds.map((id) => SAMPLE.find((p) => p.id === id)).filter(Boolean);
      list = list.filter((p) => catalogPool().some((x) => x.id === p.id));
    }

    list = list.filter((p) => {
      if (cat && p.cat !== cat) return false;
      if (subcat && p.subcat !== subcat) return false;
      if (!priceInRange(p.preco, catalogPrice)) return false;
      if (!availMatch(p, catalogAvail)) return false;
      if (!q) return true;
      return scoreRelevance(p, q) > 0;
    });

    if (catalogSort === "preco-asc") {
      list = list.slice().sort((a, b) => a.preco - b.preco);
    } else if (catalogSort === "preco-desc") {
      list = list.slice().sort((a, b) => b.preco - a.preco);
    } else if (catalogSort === "novidades") {
      list = list.slice().sort((a, b) => String(b.criadoEm || "").localeCompare(String(a.criadoEm || "")));
    } else if (q) {
      list = list.slice().sort((a, b) => scoreRelevance(b, q) - scoreRelevance(a, q));
    }

    return list;
  }

  function renderCats() {
    const pool = catalogPool();
    const cats = ["", ...new Set(pool.map((p) => p.cat))];
    const counts = {};
    pool.forEach((p) => {
      counts[p.cat] = (counts[p.cat] || 0) + 1;
    });
    document.getElementById("prod-cats").innerHTML = cats
      .map((c) => {
        const label = c || "Todas";
        const count = c ? counts[c] || 0 : pool.length;
        const icon = c === "Moda" ? "👕" : c === "Hortifrúti" ? "🍌" : c === "Frios" ? "🧀" : c === "Limpeza" ? "✨" : c === "Serviços" ? "⏱" : c === "Mercearia" ? "🛒" : "▦";
        return `<button type="button" class="vitrine-cat ${c === cat ? "active" : ""}" data-cat="${c}" role="tab" aria-selected="${c === cat}">
          <span class="vitrine-cat-icon">${c ? icon : "▦"}</span>
          <span class="vitrine-cat-label">${label}</span>
          <span class="vitrine-cat-count">${count}</span>
        </button>`;
      })
      .join("");
    renderSubcats();
  }

  function renderSubcats() {
    const el = document.getElementById("prod-subcats");
    if (!cat) {
      el.hidden = true;
      el.innerHTML = "";
      subcat = "";
      return;
    }
    const subs = [
      ...new Set(
        catalogPool()
          .filter((p) => p.cat === cat && p.subcat)
          .map((p) => p.subcat)
      ),
    ];
    if (!subs.length) {
      el.hidden = true;
      el.innerHTML = "";
      subcat = "";
      return;
    }
    if (subcat && !subs.includes(subcat)) subcat = "";
    el.hidden = false;
    el.innerHTML =
      `<button type="button" class="vitrine-sub ${!subcat ? "active" : ""}" data-sub="">Todas</button>` +
      subs
        .map(
          (s) =>
            `<button type="button" class="vitrine-sub ${s === subcat ? "active" : ""}" data-sub="${s}">${s}</button>`
        )
        .join("");
  }

  function renderCatalogTabs() {
    document.querySelectorAll("#catalog-tabs button").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === catalogTab);
    });
  }

  function renderCatalogToolbar() {
    const q = (document.getElementById("prod-search").value || "").trim();
    const n = filteredProducts().length;
    const label = document.getElementById("catalog-result-label");
    if (q) label.textContent = n + (n === 1 ? " resultado" : " resultados") + " · fotos";
    else if (cat) label.textContent = (subcat || cat) + " · " + n + (n === 1 ? " item" : " itens");
    else label.textContent = "Mostruário · " + n + (n === 1 ? " item" : " itens");
    document.getElementById("catalog-sort").value = catalogSort;
    document.getElementById("catalog-price").value = catalogPrice;
    document.getElementById("catalog-avail").value = catalogAvail;
  }

  function stockBadgeHtml(p) {
    const st = STOCK_LABELS[p.stockStatus || "local"] || STOCK_LABELS.local;
    return `<span class="stock-badge ${st.cls}">${st.short}</span>`;
  }

  function alertBadgesHtml(p) {
    const bits = [];
    if (p.novo) bits.push('<span class="prod-alert alert-novo">Novo</span>');
    if (p.peso) bits.push('<span class="prod-alert alert-kg">KG</span>');
    if (p.servico) bits.push('<span class="prod-alert alert-svc">Serviço</span>');
    if (p.variants) bits.push('<span class="prod-alert alert-var">Variação</span>');
    if (p.alertas && p.alertas.length) {
      p.alertas.forEach((a) => {
        const cls = a === "recall" ? "alert-recall" : "alert-promo";
        const label = a === "recall" ? "Recall" : "Promo";
        bits.push(`<span class="prod-alert ${cls}">${label}</span>`);
      });
    }
    return bits.join("");
  }

  function colorSwatchStyle(name) {
    const map = {
      Branca: "#f8fafc",
      Preta: "#0f172a",
      Azul: "#2563eb",
      "Azul escuro": "#1e3a8a",
      Preto: "#111827",
    };
    if (map[name]) return map[name];
    let h = 0;
    for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) % 360;
    return "hsl(" + h + " 55% 45%)";
  }

  function cardVariantHtml(p) {
    if (!p.variants) return "";
    const cores = (p.variants.cores || []).slice(0, 5);
    const tams = (p.variants.tamanhos || []).slice(0, 6);
    return (
      '<div class="prod-var-grade">' +
      (cores.length
        ? '<div class="prod-var-cores">' +
          cores
            .map(
              (c) =>
                `<button type="button" class="prod-dot" title="${c}" data-quick-cor="${c}" data-id="${p.id}" style="background:${colorSwatchStyle(c)}"></button>`
            )
            .join("") +
          "</div>"
        : "") +
      (tams.length
        ? '<div class="prod-var-tams">' +
          tams
            .map(
              (t) =>
                `<button type="button" class="prod-size" data-quick-tam="${t}" data-id="${p.id}">${t}</button>`
            )
            .join("") +
          "</div>"
        : "") +
      "</div>"
    );
  }

  function openVariantPanelWithPick(product, pick) {
    openVariantPanel(product);
    if (pick && pick.cor) variantPick.cor = pick.cor;
    if (pick && pick.tamanho) variantPick.tamanho = pick.tamanho;
    renderVariantSwatches();
  }

  function renderProducts() {
    const list = filteredProducts();
    renderCatalogToolbar();
    document.getElementById("prod-grid").innerHTML = list
      .map((p) => {
        const fav = favorites.includes(p.id);
        const src = p.foto || FALLBACK_FOTO;
        const multi = productPhotos(p).length > 1;
        const unit = p.peso ? "/kg" : p.servico ? "/hora" : "";
        return `
      <div class="prod-card ${fav ? "fav" : ""}" data-id="${p.id}" role="button" tabindex="0" title="Abrir mostruário">
        <span class="prod-fav ${fav ? "on" : ""}" data-fav="${p.id}" title="Favorito">★</span>
        <div class="prod-alerts">${alertBadgesHtml(p)}</div>
        <div class="thumb">
          <img src="${src}" alt="" loading="lazy" onerror="this.onerror=null;this.src='${FALLBACK_FOTO}'">
          ${multi ? '<span class="prod-gallery-hint">galeria</span>' : ""}
          ${p.peso ? '<span class="prod-cap-hint">informe o peso</span>' : ""}
          ${p.servico ? '<span class="prod-cap-hint">serviço</span>' : ""}
        </div>
        <div class="name">${p.nome}</div>
        <div class="price">${money(p.preco)}${unit ? "<small>" + unit + "</small>" : ""}</div>
        ${cardVariantHtml(p)}
        ${stockBadgeHtml(p)}
      </div>`;
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
    const treino = s.queueStatus.training ? " · TREINO" : "";
    el.className = "queue-banner state-" + s.queueStatus.state + (s.queueStatus.training ? " training" : "");
    el.innerHTML =
      `<strong>Pedido #${s.queueStatus.orderNum} na fila${treino}</strong> · ${labels[s.queueStatus.state] || s.queueStatus.state}`;
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
    const promo = calcPromoForSession(s, null);
    const promoRow = document.getElementById("summary-promo-row");
    if (promo.discount > 0 || (promo.hints && promo.hints.length)) {
      promoRow.hidden = false;
      const lab = [promo.label, ...(promo.hints || [])].filter(Boolean).join(" · ");
      document.getElementById("summary-promo-label").textContent = lab || "Promo";
      document.getElementById("summary-promo").textContent =
        promo.discount > 0 ? "−" + money(promo.discount) : "no pgto";
    } else {
      promoRow.hidden = true;
    }
    document.getElementById("order-total").textContent = money(orderTotal());
    document.getElementById("btn-side-note").disabled = s.selectedLine < 0 || !s.lines[s.selectedLine];
    document.getElementById("btn-side-price").disabled = s.selectedLine < 0 || !s.lines[s.selectedLine];

    const tab = document.getElementById("troca-aprov-banner");
    if (tab) {
      if (sessionHasTroca(s) && s.trocaAprovacao) {
        tab.hidden = false;
        tab.textContent =
          "Troca autorizada · " +
          (s.trocaAprovacao.nome || s.trocaAprovacao.usuario) +
          (s.trocaAprovacao.venda_ref ? " · NFC-e " + s.trocaAprovacao.venda_ref : "");
      } else if (sessionHasTroca(s) && !s.trocaAprovacao) {
        tab.hidden = false;
        tab.textContent = "Troca sem aprovação — peça senha do gerente";
        tab.style.color = "#f87171";
        tab.style.borderColor = "rgba(248,113,113,.35)";
      } else {
        tab.hidden = true;
        tab.textContent = "";
        tab.style.color = "#4ade80";
        tab.style.borderColor = "rgba(74,222,128,.35)";
      }
    }

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
        const qtyLabel = l.peso
          ? String(l.qtd).replace(".", ",") + " kg"
          : l.servico
            ? String(l.qtd) + " h"
            : String(l.qtd);
        const note = l.obs ? `<span class="disc" title="${l.obs}">obs</span>` : "";
        const svcTag = l.servico ? '<span class="svc-tag">serviço</span>' : "";
        const svcDesc = l.servicoDesc
          ? `<div class="line-svc-desc">${l.servicoDesc}</div>`
          : "";
        const trocaTag = l.troca ? '<span class="troca-tag">troca</span>' : "";
        const negCls = l.qtd < 0 || l.troca ? " troca-line" : "";
        const unitPrice = l.peso ? "/kg" : l.servico ? "/h" : " un.";
        return `
      <div class="order-line${negCls} ${i === s.selectedLine ? "sel" : ""}" data-idx="${i}">
        <div class="title">${l.nome} ${note}${svcTag}${trocaTag}${svcDesc}</div>
        <div class="line-total">${money(lineTotal(l))}</div>
        <div class="meta">${money(l.preco)}${unitPrice}</div>
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
    if (line && line.id && !line.troca && !line.servico) {
      const p = SAMPLE.find((x) => x.id === Number(line.id));
      if (p) {
        const want = Number(line.qtd) > 0 ? Number(line.qtd) : 1;
        const gate = stockGate(p, want, s);
        if (!gate.ok) {
          applyStockGateFailure(p, gate);
          return;
        }
      }
    }
    pushUndo("adicionar item");
    s.lines.push(line);
    s.selectedLine = s.lines.length - 1;
    if (line.id) trackRecent(line.id);
    renderOrder();
  }

  function addProduct(id, opts) {
    opts = opts || {};
    const p = SAMPLE.find((x) => x.id === Number(id));
    if (!p) return;
    const s = getSession();
    if (!s) return;

    if (consultaMode && !opts.forceAdd) {
      openPriceConsult(p);
      return;
    }

    if (!opts.skipRecall && p.alertas && p.alertas.includes("recall")) {
      if (!confirm("RECALL: " + p.nome + " — produto em recall. Confirmar adição?")) {
        return;
      }
    }

    if (p.variants) {
      openVariantPanelWithPick(p, opts.variantPick || null);
      return;
    }

    if (p.peso) {
      const gate = stockGate(p, 1, s);
      if (!gate.ok) {
        applyStockGateFailure(p, gate);
        return;
      }
      const hit = s.lines.find((l) => l.id === p.id && !l.variantKey && l.peso);
      if (!hit) {
        pushUndo("adicionar item");
        s.lines.push({
          id: p.id,
          nome: p.nome,
          preco: p.preco,
          qtd: 0,
          peso: true,
          descPct: 0,
        });
      }
      s.selectedLine = s.lines.findIndex((l) => l.id === p.id && l.peso);
      trackRecent(p.id);
      renderOrder();
      openQtyPad(s.selectedLine);
      document.getElementById("status-hint").textContent =
        "Informe o peso em kg (atalhos ou balança mock)";
      return;
    }

    if (p.servico) {
      pushUndo("adicionar item");
      s.lines.push({
        id: p.id,
        nome: p.nome,
        preco: p.preco,
        qtd: 1,
        descPct: 0,
        servico: true,
        servicoDesc: "",
      });
      s.selectedLine = s.lines.length - 1;
      trackRecent(p.id);
      renderOrder();
      openServiceEditor();
      document.getElementById("status-hint").textContent =
        "Descreva o serviço antes de enviar ao caixa";
      return;
    }

    const hit = s.lines.find(
      (l) => l.id === p.id && !l.peso && !l.variantKey && !l.troca && !l.servico
    );
    const gate = stockGate(p, 1, s);
    if (!gate.ok) {
      applyStockGateFailure(p, gate);
      return;
    }
    pushUndo("adicionar item");
    if (hit) hit.qtd += 1;
    else s.lines.push({ id: p.id, nome: p.nome, preco: p.preco, qtd: 1, descPct: 0 });
    s.selectedLine = s.lines.findIndex(
      (l) => l.id === p.id && !l.peso && !l.variantKey && !l.troca && !l.servico
    );
    trackRecent(p.id);
    renderOrder();
  }

  /** @type {null | object} */
  let activeFilaPedido = null;
  /** @type {object[]} */
  let filaPedidos = [];
  let filaPollTimer = null;
  let pdvQueuePollTimer = null;
  let caixaFormaPg = "Dinheiro";

  function clearSessionAfterSend(s) {
    s.lines = [];
    s.selectedLine = -1;
    s.orderDisc = { type: "val", value: 0 };
    s.orderAcr = { type: "val", value: 0 };
    s.orderParc = null;
    undoStack = [];
    syncUndoBtn();
    renderOrder();
  }

  function buildFilaPayload(session) {
    const promo = calcPromoForSession(session, null);
    const estab =
      (posContexto && posContexto.estabelecimento && posContexto.estabelecimento.id) || "";
    const term = (posContexto && posContexto.terminal && posContexto.terminal.id) || "";
    return {
      sessionId: session.id,
      estabelecimento_id: estab,
      terminal_id: term,
      client: {
        id: session.client.id,
        nome: session.client.nome,
        av: session.client.av,
        cpf: session.client.cpf || "",
        hint: session.client.hint || "",
      },
      lines: session.lines.map((l) => ({
        id: l.id,
        nome: l.nome,
        preco: l.preco,
        qtd: l.qtd,
        peso: !!l.peso,
        servico: !!l.servico,
        troca: !!l.troca,
        variantKey: l.variantKey || "",
        obs: l.obs || "",
        servicoDesc: l.servicoDesc || "",
        descPct: l.descPct || 0,
        categoria: productCategoria(l.id),
        cat: productCategoria(l.id),
      })),
      subtotal: sessionSubtotal(session),
      discount: sessionDiscAmount(session),
      surcharge: sessionAcrAmount(session),
      promo: promo.discount || 0,
      promo_kits: promo.kitsDiscount || 0,
      total: sessionTotal(session),
      orderDisc: session.orderDisc,
      orderAcr: session.orderAcr,
      orderParc: session.orderParc,
      troca_aprovacao: session.trocaAprovacao || null,
    };
  }

  function renderFilaList(pedidos) {
    const list = document.getElementById("fila-list");
    if (!list) return;
    filaPedidos = pedidos || [];
    if (!filaPedidos.length) {
      list.innerHTML =
        '<div class="order-empty" style="padding:24px;text-align:center;color:var(--text-muted)">Fila vazia — aguarde pedidos do PDV</div>';
      return;
    }
    const activeId = activeFilaPedido && activeFilaPedido.id;
    list.innerHTML = filaPedidos
      .map((p) => {
        const treino = p.training ? " fila-training" : "";
        const active = p.id === activeId ? " active" : "";
        const n = (p.lines || []).length;
        const when = p.createdAt ? String(p.createdAt).replace("T", " ").slice(11, 16) : "";
        return `<div class="fila-item${treino}${active}" data-fila-id="${p.id}" data-order="${p.orderNum}">
          <div>
            <strong>Pedido #${p.orderNum} · ${(p.client && p.client.nome) || "Cliente"}</strong>
            <span>${p.pdvUser || "PDV"} · ${when || "agora"} · ${n} ${n === 1 ? "item" : "itens"} · ${p.state}</span>
          </div>
          <div class="val">${money(p.total || 0)}</div>
        </div>`;
      })
      .join("");
  }

  async function selectFilaPedido(pedido) {
    if (!pedido) return;
    activeFilaPedido = pedido;
    caixaDue = Number(pedido.total) || 0;
    cashReceived = 0;
    caixaFormaPg = caixaFormaPg || "Dinheiro";
    showNfceResult(null);
    document.getElementById("caixa-due").textContent = money(caixaDue);
    document.getElementById("btn-confirm-pay").disabled = false;
    document.getElementById("btn-confirm-pay").textContent = "Confirmar e emitir NFC-e";
    refreshCaixaDueForForma();
    renderFilaList(filaPedidos);
    document.querySelectorAll("#fila-list .fila-item").forEach((el) => {
      el.classList.toggle("active", el.dataset.filaId === pedido.id);
    });
    if (!pedido.training && pedido.state === "aguardando") {
      const updated = await updateFilaStatus(pedido.id, "pagamento");
      if (updated) {
        activeFilaPedido = updated;
        syncSessionQueueFromPedido(updated);
      }
    }
    document.getElementById("status-hint").textContent =
      "Caixa · Pedido #" + pedido.orderNum + " · " + money(caixaDue);
  }

  async function updateFilaStatus(id, state) {
    const api = window.AuthService && window.AuthService.api;
    if (!api || !id) return null;
    try {
      const res = await api("/api/pos/fila/" + encodeURIComponent(id), {
        method: "POST",
        body: JSON.stringify({ action: "status", state }),
      });
      if (res && res.status === "ok" && res.pedido) return res.pedido;
    } catch (err) {
      console.warn("[POS] update fila", err);
    }
    return null;
  }

  function syncSessionQueueFromPedido(pedido) {
    if (!pedido) return;
    sessions.forEach((s) => {
      if (s.queueStatus && (s.queueStatus.id === pedido.id || s.queueStatus.orderNum === pedido.orderNum)) {
        s.queueStatus.state = pedido.state;
        s.queueStatus.id = pedido.id;
        s.queueStatus.orderNum = pedido.orderNum;
      }
    });
    const cur = getSession();
    if (cur && cur.queueStatus && cur.queueStatus.id === pedido.id) renderQueueBanner();
  }

  async function refreshFilaCaixa() {
    const api = window.AuthService && window.AuthService.api;
    if (!api) {
      renderFilaList(filaPedidos);
      return;
    }
    try {
      const res = await api("/api/pos/fila?state=aguardando,pagamento");
      if (res && res.status === "ok" && Array.isArray(res.pedidos)) {
        renderFilaList(res.pedidos);
        if (activeFilaPedido) {
          const still = res.pedidos.find((p) => p.id === activeFilaPedido.id);
          if (still) activeFilaPedido = still;
          else {
            activeFilaPedido = null;
            document.getElementById("btn-confirm-pay").disabled = true;
          }
        }
      }
    } catch (err) {
      console.warn("[POS] refresh fila", err);
    }
  }

  function startFilaPolling() {
    stopFilaPolling();
    refreshFilaCaixa();
    filaPollTimer = setInterval(() => {
      if (mode === "caixa") refreshFilaCaixa();
    }, 5000);
  }

  function stopFilaPolling() {
    if (filaPollTimer) {
      clearInterval(filaPollTimer);
      filaPollTimer = null;
    }
  }

  function startPdvQueuePolling() {
    stopPdvQueuePolling();
    pdvQueuePollTimer = setInterval(async () => {
      const s = getSession();
      if (!s || !s.queueStatus || !s.queueStatus.id || s.queueStatus.training) return;
      if (s.queueStatus.state === "pago" || s.queueStatus.state === "cancelado") return;
      const api = window.AuthService && window.AuthService.api;
      if (!api) return;
      try {
        const res = await api("/api/pos/fila?id=" + encodeURIComponent(s.queueStatus.id));
        if (res && res.status === "ok" && res.pedido) {
          s.queueStatus.state = res.pedido.state;
          renderQueueBanner();
          const labels = { aguardando: "Aguardando", pagamento: "Em pagamento", pago: "Pago" };
          document.getElementById("status-hint").textContent =
            "Pedido #" + s.queueStatus.orderNum + " · " + (labels[s.queueStatus.state] || s.queueStatus.state);
        }
      } catch (_) {
        /* ignore */
      }
    }, 4000);
  }

  function stopPdvQueuePolling() {
    if (pdvQueuePollTimer) {
      clearInterval(pdvQueuePollTimer);
      pdvQueuePollTimer = null;
    }
  }

  function addToFilaLocal(pedido, isTraining) {
    const list = filaPedidos.slice();
    list.unshift(pedido);
    renderFilaList(list);
  }

  function startQueueMock(session) {
    const orderNum = nextOrderNum++;
    const pedido = {
      id: "local-" + orderNum,
      orderNum,
      state: "aguardando",
      training: false,
      createdAt: new Date().toISOString(),
      pdvUser: "PDV",
      client: session.client,
      lines: session.lines.slice(),
      total: sessionTotal(session),
    };
    session.queueStatus = { orderNum, state: "aguardando", id: pedido.id };
    renderQueueBanner();
    addToFilaLocal(pedido, false);

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
      pedido.state = states[step];
      renderQueueBanner();
      renderFilaList(filaPedidos.map((p) => (p.id === pedido.id ? pedido : p)));
      const labels = { aguardando: "Aguardando", pagamento: "Em pagamento", pago: "Pago" };
      document.getElementById("status-hint").textContent =
        "Pedido #" + orderNum + " · " + labels[session.queueStatus.state] + " (demo)";
    }, 4000);
  }

  async function sendToCashier() {
    const s = getSession();
    if (!s || !s.lines.length) return;
    const total = orderTotal();

    if (sessionHasTroca(s) && !s.trocaAprovacao && !trainingMode) {
      openMgrAuthForExchange();
      document.getElementById("status-hint").textContent =
        "Troca no pedido — aprovação do gerente obrigatória antes de enviar";
      return;
    }

    if (s.orderType === "orcamento") {
      document.getElementById("status-hint").textContent =
        "Orçamento salvo (local) · " + money(total);
      clearSessionAfterSend(s);
      return;
    }

    if (trainingMode) {
      const orderNum = nextOrderNum++;
      const pedido = {
        id: "treino-" + orderNum,
        orderNum,
        state: "aguardando",
        training: true,
        createdAt: new Date().toISOString(),
        pdvUser: "TREINO",
        client: s.client,
        lines: s.lines.slice(),
        total,
      };
      s.queueStatus = { orderNum, state: "aguardando", training: true, id: pedido.id };
      renderQueueBanner();
      addToFilaLocal(pedido, true);
      document.getElementById("status-hint").textContent =
        "Treino · Pedido #" + orderNum + " simulado · " + money(total);
      clearSessionAfterSend(s);
      return;
    }

    const api = window.AuthService && window.AuthService.api;
    if (api) {
      try {
        const res = await api("/api/pos/fila", {
          method: "POST",
          body: JSON.stringify(buildFilaPayload(s)),
        });
        if (res && res.status === "ok" && res.pedido) {
          const p = res.pedido;
          s.queueStatus = { orderNum: p.orderNum, state: p.state, id: p.id };
          renderQueueBanner();
          addToDailyGoal(total);
          document.getElementById("status-hint").textContent =
            "Pedido #" + p.orderNum + " na fila · Aguardando · " + money(total);
          if (mode === "caixa") refreshFilaCaixa();
          else startPdvQueuePolling();
          clearSessionAfterSend(s);
          return;
        }
        document.getElementById("status-hint").textContent =
          (res && res.message) || "Falha ao enviar — usando fila local";
      } catch (err) {
        console.warn("[POS] send fila", err);
        document.getElementById("status-hint").textContent =
          "API indisponível — fila local (demo)";
      }
    }

    startQueueMock(s);
    addToDailyGoal(total);
    document.getElementById("status-hint").textContent =
      "Pedido #" + s.queueStatus.orderNum + " na fila (demo) · " + money(total);
    clearSessionAfterSend(s);
  }

  function showNfceResult(res) {
    const box = document.getElementById("nfce-result");
    if (!box) return;
    if (!res) {
      box.hidden = true;
      box.innerHTML = "";
      return;
    }
    const nfce = res.nfce || {};
    const resultado = nfce.resultado || res.pedido?.nfce || {};
    const cStat = resultado.cStat || nfce.cStat || "";
    const xMotivo = resultado.xMotivo || nfce.xMotivo || res.aviso || "";
    const chave = nfce.chave || resultado.chave || "";
    const numero = nfce.numero || "";
    const ok = String(cStat) === "100" || String(resultado.status || "").toUpperCase() === "AUTORIZADA";
    box.hidden = false;
    box.className = "nfce-result " + (ok ? "ok" : "err");
    box.innerHTML =
      `<strong>${ok ? "NFC-e autorizada" : "Pagamento ok · NFC-e pendente/erro"}</strong>` +
      (numero ? `<div>Número: ${numero}</div>` : "") +
      (chave ? `<div class="nfce-chave">${chave}</div>` : "") +
      (cStat ? `<div>cStat ${cStat}${xMotivo ? " — " + xMotivo : ""}</div>` : xMotivo ? `<div>${xMotivo}</div>` : "") +
      (res.aviso && !xMotivo.includes(res.aviso) ? `<div class="nfce-aviso">${res.aviso}</div>` : "");
  }

  async function confirmCaixaPayment() {
    if (!activeFilaPedido) {
      document.getElementById("status-hint").textContent = "Selecione um pedido na fila";
      return;
    }
    const pedido = activeFilaPedido;
    const btn = document.getElementById("btn-confirm-pay");
    btn.disabled = true;
    const prevLabel = btn.textContent;
    btn.textContent = "Processando…";

    if (pedido.training || String(pedido.id).startsWith("local-") || String(pedido.id).startsWith("treino-")) {
      pedido.state = "pago";
      syncSessionQueueFromPedido(pedido);
      filaPedidos = filaPedidos.filter((p) => p.id !== pedido.id);
      renderFilaList(filaPedidos);
      activeFilaPedido = null;
      btn.textContent = prevLabel;
      showNfceResult({
        aviso: "Fila local/treino — NFC-e não emitida",
        nfce: { status: "DEMO", xMotivo: "Sem envio à SEFAZ no modo demo/treino" },
      });
      document.getElementById("status-hint").textContent =
        "Pagamento confirmado (demo) — Pedido #" + pedido.orderNum;
      return;
    }

    const api = window.AuthService && window.AuthService.api;
    if (!api) {
      btn.disabled = false;
      btn.textContent = prevLabel;
      document.getElementById("status-hint").textContent = "AuthService indisponível";
      return;
    }

    try {
      const res = await api("/api/pos/fila/" + encodeURIComponent(pedido.id), {
        method: "POST",
        body: JSON.stringify({
          action: "finalizar",
          forma_pg: caixaFormaPg || "Dinheiro",
          emitir_nfce: true,
          ambiente: 2,
        }),
      });
      btn.textContent = prevLabel;
      if (!res || res.status !== "ok") {
        btn.disabled = false;
        document.getElementById("status-hint").textContent =
          (res && res.message) || "Falha ao finalizar pedido";
        return;
      }
      syncSessionQueueFromPedido(res.pedido || { id: pedido.id, orderNum: pedido.orderNum, state: "pago" });
      activeFilaPedido = null;
      showNfceResult(res);
      await refreshFilaCaixa();
      const chave = (res.nfce && res.nfce.chave) || (res.pedido && res.pedido.nfce && res.pedido.nfce.chave) || "";
      document.getElementById("status-hint").textContent = chave
        ? "Pedido #" + pedido.orderNum + " pago · NFC-e " + chave.slice(0, 20) + "…"
        : "Pedido #" + pedido.orderNum + " pago" + (res.aviso ? " · " + res.aviso : "");
    } catch (err) {
      console.warn("[POS] finalizar", err);
      btn.disabled = false;
      btn.textContent = prevLabel;
      document.getElementById("status-hint").textContent = "Erro ao finalizar / emitir NFC-e";
    }
  }

  function convertToOrder() {
    const s = getSession();
    if (!s) return;
    s.orderType = "pedido";
    syncOrderTypeUI();
    document.getElementById("status-hint").textContent = "Orçamento convertido em pedido";
  }

  function renderAll() {
    renderCats();
    renderCatalogTabs();
    renderProducts();
    renderOrder();
    renderGoalStatus();
    syncTrainingUI();
    syncConsultaUI();
    const s = getSession();
    if (s) {
      document.getElementById("client-name").textContent = s.client.nome;
      document.getElementById("client-av").textContent = s.client.av;
      document.getElementById("client-hint").textContent = s.client.hint;
      const fullClient = MOCK_CUSTOMERS.find((c) => c.id === s.client.id) || s.client;
      renderClientHistory(fullClient);
    }
  }

  function setMode(next) {
    if (posContexto && posContexto.pode_trocar_modo === false) {
      const forced = posContexto.modo_sugerido || "pdv";
      if (next !== forced) next = forced;
    }
    mode = next;
    if (numpad && numpad.host === "side" && mode !== "pdv") closeNumpad();
    if (numpad && numpad.host === "caixa" && mode !== "caixa") closeNumpad();
    if (mode !== "pdv") setSmartCtx("summary");
    document.querySelectorAll(".pos-mode button").forEach((b) => {
      b.classList.toggle("active", b.dataset.mode === mode);
      const locked = posContexto && posContexto.pode_trocar_modo === false;
      b.disabled = !!locked && b.dataset.mode !== mode;
    });
    document.getElementById("view-pdv").classList.toggle("active", mode === "pdv");
    document.getElementById("view-caixa").classList.toggle("active", mode === "caixa");
    const term = posContexto && posContexto.terminal;
    const termLabel = term
      ? `${term.codigo || ""} · ${term.nome || ""}`.trim()
      : mode === "pdv"
        ? "Terminal PDV"
        : "Terminal Caixa";
    document.getElementById("top-mode-label").textContent = termLabel || (mode === "pdv" ? "Terminal PDV" : "Terminal Caixa");
    document.getElementById("status-mode").textContent =
      mode === "pdv" ? "Modo PDV" : "Modo Caixa";
    if (mode === "caixa") {
      startFilaPolling();
      stopPdvQueuePolling();
    } else {
      stopFilaPolling();
      startPdvQueuePolling();
    }
  }

  async function loadPosContexto() {
    const estabEl = document.getElementById("pos-estab");
    const termEl = document.getElementById("pos-terminal");
    try {
      const api = window.AuthService && window.AuthService.api;
      if (!api) throw new Error("no auth");
      const data = await api("/api/pos/contexto");
      if (data.status !== "ok") throw new Error(data.message || "contexto");
      posContexto = data;
      window.__posContexto = data;
    } catch {
      posContexto = {
        terminal: null,
        estabelecimento: null,
        modo_sugerido: "pdv",
        pode_trocar_modo: true,
        aviso: "Contexto local (sem API)",
      };
      window.__posContexto = posContexto;
    }

    const estab = posContexto.estabelecimento;
    const term = posContexto.terminal;
    if (estabEl) {
      estabEl.textContent = estab ? estab.nome || estab.id || "—" : "Sem loja";
      estabEl.title = estab
        ? `${estab.nome || ""} · ${estab.cidade || ""}/${estab.uf || ""} · ${estab.cnpj || ""}`.trim()
        : "Nenhum estabelecimento";
    }
    if (termEl) {
      termEl.textContent = term ? term.codigo || "—" : "Sem terminal";
      termEl.title = term
        ? `${term.codigo} · ${term.nome} · ${term.tipo}`
        : posContexto.aviso || "Sem terminal vinculado";
    }
    const store = document.getElementById("status-store");
    if (store) {
      store.textContent = estab
        ? `${estab.nome || estab.id}${term ? " · " + (term.codigo || "") : ""}`
        : "Varejo";
    }
    return posContexto;
  }

  function bindNumpadKeys(el) {
    el.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-k]");
      if (btn) numpadKey(btn.dataset.k);
    });
  }

  async function boot() {
    const user = (window.AuthService && window.AuthService.getUser()) || {};
    const name = user.nome || user.usuario || "Operador";
    document.getElementById("op-name").textContent = name;
    document.getElementById("status-user").textContent = name;

    createSession();
    document.getElementById("status-store").textContent = "Varejo";
    setDataSource("demo");
    await loadPosContexto();
    await loadPosDataFromApi();
    await loadCampaignsFromApi();
    await loadCashMovesFromApi();
    await loadCaixaSessao();
    renderClientResults();
    renderAll();
    setSmartCtx("summary");
    setCaixaCtx("default");
    setMode((posContexto && posContexto.modo_sugerido) || "pdv");
    syncUndoBtn();
    if (posContexto && posContexto.aviso) {
      document.getElementById("status-hint").textContent = posContexto.aviso;
    } else if (dataSource === "demo") {
      document.getElementById("status-hint").textContent =
        "Varejo · demo · toque no produto para o mostruário · bip (Enter) adiciona direto";
    } else {
      const estab = posContexto && posContexto.estabelecimento;
      const term = posContexto && posContexto.terminal;
      document.getElementById("status-hint").textContent =
        `${estab ? estab.nome : "Loja"} · ${term ? term.codigo : "sem terminal"} · API`;
    }

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

    document.getElementById("prod-cats").addEventListener("click", (e) => {
      const btn = e.target.closest(".vitrine-cat, .pos-cat");
      if (!btn) return;
      cat = btn.dataset.cat || "";
      subcat = "";
      renderCats();
      renderProducts();
    });

    document.getElementById("prod-subcats").addEventListener("click", (e) => {
      const btn = e.target.closest(".vitrine-sub");
      if (!btn) return;
      subcat = btn.dataset.sub || "";
      renderSubcats();
      renderProducts();
    });

    document.getElementById("catalog-sort").addEventListener("change", (e) => {
      catalogSort = e.target.value;
      renderProducts();
    });
    document.getElementById("catalog-price").addEventListener("change", (e) => {
      catalogPrice = e.target.value;
      renderProducts();
    });
    document.getElementById("catalog-avail").addEventListener("change", (e) => {
      catalogAvail = e.target.value;
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
    document.getElementById("prod-search").addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleSearchEnter();
      }
    });

    document.getElementById("btn-consulta").addEventListener("click", () => {
      consultaMode = !consultaMode;
      syncConsultaUI();
      document.getElementById("status-hint").textContent = consultaMode
        ? "Consulta de preço ativa — toque no produto para ver preço/estoque"
        : "Toque no produto para abrir o mostruário · bip (Enter) adiciona direto";
    });

    document.getElementById("btn-training").addEventListener("click", () => {
      setTrainingMode(!trainingMode);
    });

    document.getElementById("prod-grid").addEventListener("click", (e) => {
      const favBtn = e.target.closest("[data-fav]");
      if (favBtn) {
        e.stopPropagation();
        toggleFavorite(favBtn.dataset.fav);
        return;
      }
      const quickTam = e.target.closest("[data-quick-tam]");
      const quickCor = e.target.closest("[data-quick-cor]");
      if (quickTam || quickCor) {
        e.stopPropagation();
        const el = quickTam || quickCor;
        const p = SAMPLE.find((x) => x.id === Number(el.dataset.id));
        if (!p || !p.variants) return;
        openVariantPanelWithPick(p, {
          cor: quickCor ? quickCor.dataset.quickCor : p.variants.cores[0],
          tamanho: quickTam ? quickTam.dataset.quickTam : p.variants.tamanhos[0],
        });
        return;
      }
      const card = e.target.closest(".prod-card");
      if (card) {
        const p = SAMPLE.find((x) => x.id === Number(card.dataset.id));
        if (p) openShowcase(p);
      }
    });

    document.getElementById("prod-grid").addEventListener("keydown", (e) => {
      if (e.key !== "Enter" && e.key !== " ") return;
      const card = e.target.closest(".prod-card");
      if (!card || e.target.closest("button")) return;
      e.preventDefault();
      const p = SAMPLE.find((x) => x.id === Number(card.dataset.id));
      if (p) openShowcase(p);
    });

    document.getElementById("prod-grid").addEventListener("mousedown", (e) => {
      const card = e.target.closest(".prod-card");
      if (!card || e.target.closest("[data-fav], [data-quick-tam], [data-quick-cor]")) return;
      longPressTimer = setTimeout(() => toggleFavorite(card.dataset.id), 600);
    });
    document.getElementById("prod-grid").addEventListener("mouseup", () => clearTimeout(longPressTimer));
    document.getElementById("prod-grid").addEventListener("mouseleave", () => clearTimeout(longPressTimer));

    document.getElementById("showcase-close").addEventListener("click", closeShowcase);
    document.getElementById("showcase-backdrop").addEventListener("click", closeShowcase);
    document.getElementById("showcase-prev").addEventListener("click", () => {
      if (!showcaseState) return;
      showcaseState.fotoIdx -= 1;
      renderShowcase();
    });
    document.getElementById("showcase-next").addEventListener("click", () => {
      if (!showcaseState) return;
      showcaseState.fotoIdx += 1;
      renderShowcase();
    });
    document.getElementById("showcase-dots").addEventListener("click", (e) => {
      const dot = e.target.closest("[data-dot]");
      if (!dot || !showcaseState) return;
      showcaseState.fotoIdx = Number(dot.dataset.dot);
      renderShowcase();
    });
    document.getElementById("showcase-cores").addEventListener("click", (e) => {
      const btn = e.target.closest("[data-scor]");
      if (!btn || !showcaseState) return;
      showcaseState.cor = btn.dataset.scor;
      renderShowcase();
    });
    document.getElementById("showcase-tamanhos").addEventListener("click", (e) => {
      const btn = e.target.closest("[data-stam]");
      if (!btn || !showcaseState) return;
      showcaseState.tamanho = btn.dataset.stam;
      renderShowcase();
    });
    document.getElementById("showcase-add").addEventListener("click", showcaseAddToOrder);
    document.getElementById("showcase-consult").addEventListener("click", () => {
      if (!showcaseState) return;
      const p = showcaseState.product;
      closeShowcase();
      openPriceConsult(p);
    });
    let touchStartX = 0;
    const stage = document.querySelector(".showcase-stage");
    if (stage) {
      stage.addEventListener(
        "touchstart",
        (e) => {
          touchStartX = e.changedTouches[0].screenX;
        },
        { passive: true }
      );
      stage.addEventListener(
        "touchend",
        (e) => {
          if (!showcaseState) return;
          const dx = e.changedTouches[0].screenX - touchStartX;
          if (Math.abs(dx) < 40) return;
          showcaseState.fotoIdx += dx < 0 ? 1 : -1;
          renderShowcase();
        },
        { passive: true }
      );
    }

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
    document.getElementById("weight-chips")?.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-w]");
      if (btn) applyWeightPreset(btn.dataset.w);
    });
    document.getElementById("service-phrases")?.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-phrase]");
      if (btn) appendNotePhrase(btn.dataset.phrase);
    });

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
    document.getElementById("btn-espera").addEventListener("click", markEsperaSession);
    document.getElementById("btn-undo").addEventListener("click", undoLast);
    document.getElementById("btn-send-cashier").addEventListener("click", sendToCashier);
    document.getElementById("btn-convert-order").addEventListener("click", convertToOrder);
    document.getElementById("btn-exchange").addEventListener("click", openExchangePanel);
    document.getElementById("exchange-search").addEventListener("input", renderExchangeResults);
    document.getElementById("btn-exchange-back").addEventListener("click", () => setSmartCtx("summary"));
    document.getElementById("btn-mgr-cancel")?.addEventListener("click", () => setSmartCtx("summary"));
    document.getElementById("btn-mgr-ok")?.addEventListener("click", applyMgrAuth);
    document.getElementById("mgr-pass")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        applyMgrAuth();
      }
    });
    document.getElementById("btn-price-back").addEventListener("click", () => {
      pendingPriceProduct = null;
      setSmartCtx("summary");
    });
    document.getElementById("btn-price-add").addEventListener("click", () => {
      if (pendingPriceProduct) {
        addProduct(pendingPriceProduct.id, { forceAdd: true });
        pendingPriceProduct = null;
        setSmartCtx("summary");
      }
    });
    document.getElementById("btn-similar-back").addEventListener("click", () => setSmartCtx("summary"));

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
        const formaMap = {
          dinheiro: "Dinheiro",
          pix: "PIX",
          debito: "Debito",
          credito: "Credito",
          voucher: "Voucher",
        };
        caixaFormaPg = formaMap[kind] || "Dinheiro";
        showNfceResult(null);
        refreshCaixaDueForForma();
        if (kind === "dinheiro") {
          openPaymentPad();
          return;
        }
        if (cashMovePad) cancelCashMove();
        setCaixaCtx("default");
        document.getElementById("btn-confirm-pay").disabled = !activeFilaPedido;
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
    document.getElementById("btn-abrir-caixa")?.addEventListener("click", () => openSessaoPad("open"));
    document.getElementById("btn-fechar-caixa")?.addEventListener("click", async () => {
      await loadCaixaSessao();
      if (!caixaSessao) {
        document.getElementById("status-hint").textContent = "Nenhuma sessão aberta";
        return;
      }
      openSessaoPad("close");
    });
    document.getElementById("sessao-cancel")?.addEventListener("click", cancelSessaoPad);
    document.getElementById("sessao-apply")?.addEventListener("click", applySessaoPad);
    document.getElementById("sessao-keys")?.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-k]");
      if (btn && sessaoPad) sessaoKey(btn.dataset.k);
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
      confirmCaixaPayment();
    });

    renderCashMoveLog();
    document.getElementById("fila-list").addEventListener("click", (e) => {
      const item = e.target.closest(".fila-item[data-fila-id]");
      if (!item) return;
      const pedido = filaPedidos.find((p) => p.id === item.dataset.filaId);
      if (pedido) selectFilaPedido(pedido);
    });
    startPdvQueuePolling();

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        if (showcaseState) {
          e.preventDefault();
          closeShowcase();
          return;
        }
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
      if (showcaseState && (e.key === "ArrowLeft" || e.key === "ArrowRight")) {
        e.preventDefault();
        showcaseState.fotoIdx += e.key === "ArrowRight" ? 1 : -1;
        renderShowcase();
        return;
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
