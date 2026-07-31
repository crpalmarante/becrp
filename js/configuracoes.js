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

  async function loadEstabelecimentos() {
    const tbody = document.getElementById("estabs-tbody");
    if (!tbody) return;

    let lista = [];
    try {
      const token = localStorage.getItem("token") || localStorage.getItem("becrp_token");
      if (token) {
        const r = await fetch("/api/admin/empresas", {
          headers: { Authorization: "Bearer " + token },
        });
        if (r.ok) {
          const data = await r.json();
          lista = data.empresas || [];
        }
      }
    } catch {
      /* fallback static */
    }

    if (!lista.length) {
      try {
        const r = await fetch("../data/empresas.json");
        if (r.ok) {
          const map = await r.json();
          lista = Object.keys(map).map((id) => ({ id, ...map[id] }));
        }
      } catch {
        lista = [];
      }
    }

    if (!lista.length) {
      tbody.innerHTML =
        '<tr><td colspan="5">Nenhum estabelecimento. Use Gerenciar estabelecimentos.</td></tr>';
      return;
    }

    tbody.innerHTML = lista
      .map((e) => {
        const ativo = e.ativo !== false;
        return (
          `<tr>` +
          `<td>${esc(e.id || e.codigo || "—")}</td>` +
          `<td>${esc(e.nome || "—")}</td>` +
          `<td>${esc(e.cnpj || "—")}</td>` +
          `<td>${esc((e.cidade || "") + (e.uf ? "/" + e.uf : "") || "—")}</td>` +
          `<td><span class="cfg-badge ${ativo ? "on" : "off"}">${ativo ? "Ativo" : "Inativo"}</span></td>` +
          `</tr>`
        );
      })
      .join("");
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
      /* preview sidebar on toggle without full save */
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
