/*=========================================================
  brand.js — marca dinâmica (nome da organização via API)

  Fonte: GET /api/organizacao/nome (autenticado).
  Substitui "BECRP" hardcoded por:
    prioridade 1: nome_fantasia da matriz (ex.: "COMERCIAL FABIELI")
    fallback:     nome da organização
  Se a API falhar, mantém o texto existente (BECRP) — degradação segura.

  Uso: <script src="../js/brand.js"></script> (funciona standalone;
  aproveita window.AuthService se carregado).
=========================================================*/
(function () {
  var TOKEN_KEY = "auth_token";

  function getToken() {
    try {
      if (window.AuthService && typeof window.AuthService.getToken === "function") {
        return window.AuthService.getToken();
      }
    } catch (e) { /* ignore */ }
    return localStorage.getItem(TOKEN_KEY) || "";
  }

  function applyBrand(nome) {
    if (!nome) return;

    // <title> — troca apenas a marca, preservando o sufixo "— Página"
    if (document.title && document.title.indexOf(nome) === -1) {
      document.title = document.title.replace(/BECRP|FiscalBrasil/g, nome);
    }

    // Elementos de marca — mantém ícones/logos, troca só o texto
    var sel = ".brand-text, .topbar-title, .hub-brand h1, .brand h1";
    document.querySelectorAll(sel).forEach(function (el) {
      var txt = (el.textContent || "").trim();
      if (txt === "BECRP" || txt === "FiscalBrasil") el.textContent = nome;
    });
  }

  function fetchBrand() {
    var token = getToken();
    if (!token) return;
    var headers = { "X-Auth-Token": token, "Content-Type": "application/json" };
    fetch("/api/organizacao/nome", { headers: headers })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (data && data.status === "ok") {
          var nome = data.empresa || data.organizacao || "";
          if (nome) applyBrand(nome);
        }
      })
      .catch(function () { /* degradação silenciosa */ });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fetchBrand);
  } else {
    fetchBrand();
  }
})();
