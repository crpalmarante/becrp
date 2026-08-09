/* =========================================================
   masks.js — máscaras de CPF, CNPJ, CEP e telefone/celular
   ---------------------------------------------------------
   Auto-aplicado: inputs cujo id/name contenha cpf, cnpj, cep,
   telefone, celular, fone ou tel. Use data-mask="cpf|cnpj|cep|
   tel|doc" para forçar (útil para campos genéricos como
   "documento principal" — "doc" escolhe CPF/CNPJ pela
   quantidade de dígitos).
   Sem dependências; expõe window.Mascaras.
========================================================= */
(function () {
  "use strict";

  function soDigitos(v) {
    return String(v == null ? "" : v).replace(/\D/g, "");
  }

  function fmtCPF(v) {
    var d = soDigitos(v).slice(0, 11);
    if (d.length > 9) {
      return d.slice(0, 3) + "." + d.slice(3, 6) + "." + d.slice(6, 9) + "-" + d.slice(9);
    }
    if (d.length > 6) {
      return d.slice(0, 3) + "." + d.slice(3, 6) + "." + d.slice(6);
    }
    if (d.length > 3) {
      return d.slice(0, 3) + "." + d.slice(3);
    }
    return d;
  }

  function fmtCNPJ(v) {
    var d = soDigitos(v).slice(0, 14);
    if (d.length > 12) {
      return d.slice(0, 2) + "." + d.slice(2, 5) + "." + d.slice(5, 8) + "/" + d.slice(8, 12) + "-" + d.slice(12);
    }
    if (d.length > 8) {
      return d.slice(0, 2) + "." + d.slice(2, 5) + "." + d.slice(5, 8) + "/" + d.slice(8);
    }
    if (d.length > 5) {
      return d.slice(0, 2) + "." + d.slice(2, 5) + "." + d.slice(5);
    }
    if (d.length > 2) {
      return d.slice(0, 2) + "." + d.slice(2);
    }
    return d;
  }

  function fmtCEP(v) {
    var d = soDigitos(v).slice(0, 8);
    return d.length > 5 ? d.slice(0, 5) + "-" + d.slice(5) : d;
  }

  function fmtTel(v) {
    var d = soDigitos(v).slice(0, 11);
    if (d.length === 11) {
      return "(" + d.slice(0, 2) + ") " + d.slice(2, 7) + "-" + d.slice(7);
    }
    if (d.length > 6) {
      return "(" + d.slice(0, 2) + ") " + d.slice(2, 6) + "-" + d.slice(6);
    }
    if (d.length > 2) {
      return "(" + d.slice(0, 2) + ") " + d.slice(2);
    }
    return d;
  }

  /* "doc": CPF enquanto houver <= 11 dígitos, CNPJ a partir daí. */
  function fmtDoc(v) {
    var d = soDigitos(v);
    return d.length > 11 ? fmtCNPJ(v) : fmtCPF(v);
  }

  /* Moeda (padrão maskMoney): cada dígito digitado vira centavos.
     "1500" -> "R$ 15,00" | "150000" -> "R$ 1.500,00" */
  function fmtMoeda(v) {
    var d = soDigitos(v).slice(0, 12);
    if (!d.length) return "";
    var reais = parseInt(d.slice(0, -2) || "0", 10);
    var cent = parseInt(d.slice(-2) || "0", 10);
    var mil = String(reais).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return "R$ " + mil + "," + (cent < 10 ? "0" : "") + cent;
  }

  /* Limpa o valor mascarado para número com ponto (formato do backend):
     "R$ 1.500,00" -> "1500.00" | "1500.00" -> "1500.00" (idempotente). */
  function limparMoeda(v) {
    var d = soDigitos(v);
    if (!d.length) return "";
    var reais = parseInt(d.slice(0, -2) || "0", 10);
    var cent = parseInt(d.slice(-2) || "0", 10);
    return reais + "." + (cent < 10 ? "0" : "") + cent;
  }

  /* Dígitos verificadores — retorna true (válido), false (inválido) ou
     null (incompleto). Rejeita sequências repetidas (000...0, 111...1). */
  function validarCPF(v) {
    var d = soDigitos(v);
    if (d.length !== 11) return null;
    if (/^(\d)\1{10}$/.test(d)) return false;
    var soma = 0, i, resto;
    for (i = 0; i < 9; i++) soma += parseInt(d.charAt(i), 10) * (10 - i);
    resto = (soma * 10) % 11;
    var dv1 = resto === 10 ? 0 : resto;
    soma = 0;
    for (i = 0; i < 10; i++) soma += parseInt(d.charAt(i), 10) * (11 - i);
    resto = (soma * 10) % 11;
    var dv2 = resto === 10 ? 0 : resto;
    return parseInt(d.charAt(9), 10) === dv1 && parseInt(d.charAt(10), 10) === dv2;
  }

  function validarCNPJ(v) {
    var d = soDigitos(v);
    if (d.length !== 14) return null;
    if (/^(\d)\1{13}$/.test(d)) return false;
    var pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    var soma = 0, i, resto;
    for (i = 0; i < 12; i++) soma += parseInt(d.charAt(i), 10) * pesos[i];
    resto = soma % 11;
    var dv1 = resto < 2 ? 0 : 11 - resto;
    pesos.unshift(6);
    soma = 0;
    for (i = 0; i < 13; i++) soma += parseInt(d.charAt(i), 10) * pesos[i];
    resto = soma % 11;
    var dv2 = resto < 2 ? 0 : 11 - resto;
    return parseInt(d.charAt(12), 10) === dv1 && parseInt(d.charAt(13), 10) === dv2;
  }

  function validarDoc(v) {
    var d = soDigitos(v);
    if (d.length === 11) return validarCPF(d);
    if (d.length === 14) return validarCNPJ(d);
    return null;
  }

  var MASCARA = { cpf: fmtCPF, cnpj: fmtCNPJ, cep: fmtCEP, tel: fmtTel, doc: fmtDoc, moeda: fmtMoeda };
  var MAXLEN = { cpf: 14, cnpj: 18, cep: 9, tel: 15, doc: 18 };
  /* moeda: sem maxlength (o limite de 12 dígitos já está no fmtMoeda;
     o valor formatado "R$ 9.999.999.999,99" tem 19 caracteres). */

  var CLS_INV = "mask-invalido";
  var COR_INV = "#e53935";
  function limparAviso(el) {
    el.classList.remove(CLS_INV);
    el.removeAttribute("title");
    el.style.borderColor = "";
    el.style.boxShadow = "";
  }
  function marcarInvalido(el, msg) {
    el.classList.add(CLS_INV);
    el.title = msg;
    el.style.borderColor = COR_INV;
    el.style.boxShadow = "0 0 0 1px " + COR_INV;
  }

  function tipoDoCampo(el) {
    var mask = (el.getAttribute("data-mask") || "").toLowerCase();
    if (mask && MASCARA[mask]) return mask;
    var k = ((el.id || "") + " " + (el.name || "")).toLowerCase();
    if (k.indexOf("salario") !== -1 || k.indexOf("preco") !== -1 ||
        k.indexOf("preço") !== -1 || k.indexOf("valor") !== -1 ||
        k.indexOf("pensao") !== -1 || k.indexOf("vr") !== -1 ||
        k.indexOf("desconto") !== -1 || k.indexOf("plano-saude") !== -1) return "moeda";
    if (k.indexOf("cnpj") !== -1) return "cnpj";
    if (k.indexOf("cpf") !== -1) return "cpf";
    if (k.indexOf("cep") !== -1) return "cep";
    if (k.indexOf("telefone") !== -1 || k.indexOf("celular") !== -1 ||
        k.indexOf("fone") !== -1 || k.indexOf("tel") !== -1) return "tel";
    return null;
  }

  function onInput(e) {
    var el = e.target;
    el.value = MASCARA[el.dataset.maskTipo](el.value);
    limparAviso(el);
  }

  function onBlur(e) {
    var el = e.target;
    var t = el.dataset.maskTipo;
    var d = soDigitos(el.value);
    if (d) el.value = MASCARA[t](el.value);
    if (t === "cpf" || t === "cnpj" || t === "doc") {
      var r = t === "cpf" ? validarCPF(el.value)
            : t === "cnpj" ? validarCNPJ(el.value)
            : validarDoc(el.value);
      if (r === false) {
        var nome = t === "doc" ? (soDigitos(el.value).length > 11 ? "CNPJ" : "CPF") : t.toUpperCase();
        marcarInvalido(el, nome + " inválido");
      } else {
        limparAviso(el);
      }
    } else {
      limparAviso(el);
    }
  }

  function onFocus(e) {
    var el = e.target;
    var d = soDigitos(el.value);
    if (d) el.value = MASCARA[el.dataset.maskTipo](el.value);
  }

  function aplicar(el) {
    var t = tipoDoCampo(el);
    if (!t || el.dataset.maskTipo) return;
    el.dataset.maskTipo = t;
    if (MAXLEN[t]) el.setAttribute("maxlength", String(MAXLEN[t]));
    el.addEventListener("input", onInput);
    el.addEventListener("blur", onBlur);
    el.addEventListener("focus", onFocus);
    if (el.value) el.value = MASCARA[t](el.value);
  }

  function scan() {
    var els = document.querySelectorAll('input[type="text"], input:not([type])');
    for (var i = 0; i < els.length; i++) aplicar(els[i]);
  }

  var _timer = null;
  function scanDebounced() {
    if (_timer) return;
    _timer = setTimeout(function () {
      _timer = null;
      scan();
    }, 80);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scan);
  } else {
    scan();
  }

  /* Campos criados dinamicamente (ex.: f-cad-* do faturamento). */
  if (typeof MutationObserver !== "undefined") {
    new MutationObserver(scanDebounced).observe(document.documentElement, {
      childList: true,
      subtree: true,
    });
  }

  window.Mascaras = {
    soDigitos: soDigitos,
    onlyDigits: soDigitos,
    fmtCPF: fmtCPF,
    fmtCNPJ: fmtCNPJ,
    fmtCEP: fmtCEP,
    fmtTel: fmtTel,
    fmtDoc: fmtDoc,
    fmtMoeda: fmtMoeda,
    limparMoeda: limparMoeda,
    validarCPF: validarCPF,
    validarCNPJ: validarCNPJ,
    validarDoc: validarDoc,
    aplicar: function (id) {
      var el = document.getElementById(id);
      if (el) aplicar(el);
    },
    aplicarEl: aplicar,
    scan: scan,
  };
  if (typeof window.onlyDigits === "undefined") window.onlyDigits = soDigitos;
})();
