#!/usr/bin/env node
// Verificação determinística do render do badge VENCIDA e do toast de alerta
// (RFC-010 Decisão 4) usando o CÓDIGO REAL extraído de pages/folha.html.
//
// O browser-use (navegador real) não está disponível de forma confiável no
// ambiente de CI; este check executa exatamente as expressões que a página
// renderiza (linha do badge na tabela + chamada do toast) com DOM stub e
// dados equivalentes aos do seed do modo --browser.
//
// Uso: node scripts/check_render_ferias_node.js
'use strict';
const { leHtml, criaChecker } = require('./render_check_common.js');

const html = leHtml();
const { check, finalizar } = criaChecker();

// 1) Expressão do badge VENCIDA (linha da tabela de férias)
const badgeExpr = html.match(/\(f\.vencida\?'<span class="badge-vencida" title="Gozo apos o fim do periodo concessivo - salario em dobro">VENCIDA<\/span>':''\)/);
check('folha.html contém a expressão do badge VENCIDA (f.vencida → span.badge-vencida)',
      !!badgeExpr, 'padrão não encontrado');

if (badgeExpr) {
  // new Function com parâmetro explícito (mesma estratégia dos demais checks —
  // não depende do escopo léxico do chamador)
  const badgeDe = new Function('f', 'return ' + badgeExpr[0]);
  const htmlVencida = badgeDe({ vencida: true });
  check('badge presente quando f.vencida=true (contém badge-vencida e VENCIDA)',
        htmlVencida.includes('badge-vencida') && htmlVencida.includes('VENCIDA'), htmlVencida);
  check('tooltip do badge cita o fim do período concessivo e salário em dobro',
        htmlVencida.includes('Gozo apos o fim do periodo concessivo - salario em dobro'));

  const htmlNormal = badgeDe({ vencida: false });
  check('badge AUSENTE quando f.vencida=false (expressão vazia)',
        htmlNormal === '', htmlNormal);
}

// 2) Chamada do toast no incluir (calcularFerias)
const toastCall = html.match(/mostrarToast\(data\.vencida\?'ALERTA: ferias VENCIDAS registradas - salario em dobro!':'Ferias registradas!',data\.vencida\?'warning':'success'\);/);
check('folha.html contém o toast de alerta (ALERTA: ferias VENCIDAS + warning)',
      !!toastCall, 'padrão não encontrado');

if (toastCall) {
  const toasts = [];
  global.mostrarToast = (msg, tipo) => toasts.push([msg, tipo]);
  const avaliar = new Function('data', toastCall[0]);

  avaliar({ vencida: true });
  check('toast de vencida → mensagem ALERTA + tipo warning',
        toasts.length === 1 && toasts[0][0] === 'ALERTA: ferias VENCIDAS registradas - salario em dobro!' &&
        toasts[0][1] === 'warning', JSON.stringify(toasts));

  toasts.length = 0;  // assert auto-contido para o cenário normal
  avaliar({ vencida: false });
  check('toast normal → mensagem "Ferias registradas!" + tipo success',
        toasts.length === 1 && toasts[0][0] === 'Ferias registradas!' && toasts[0][1] === 'success',
        JSON.stringify(toasts));
}

// 3) Wrapper de autenticação (folha.html injeta X-Auth-Token nas chamadas)
check('folha.html injeta X-Auth-Token (wrapper de fetch)', html.includes("headers['X-Auth-Token']"));

// 3b) Comportamento REAL do wrapper: preserva headers/body e injeta o token
// apenas em URLs /api/ (o browser-use não está disponível no CI, então
// executamos o corpo do wrapper com stubs de window/localStorage).
// ATENÇÃO: os trechos extraídos abaixo são um snapshot do código da página —
// se o badge/toast/wrapper mudarem, atualize os padrões junto.
const wrapperStart = html.indexOf('(function(){\n  const orig = window.fetch;');
check('bloco do wrapper de fetch presente', wrapperStart !== -1, 'padrão não encontrado');
if (wrapperStart !== -1) {
  const wrapperEnd = html.indexOf('})();', wrapperStart) + 4;
  const wrapperSrc = html.slice(wrapperStart, wrapperEnd);

  const chamadas = [];
  const sandbox = {
    window: {},
    localStorage: { getItem: (k) => (k === 'auth_token' ? 'tok-test' : null) },
    console,
  };
  sandbox.window.fetch = (url, opts) => { chamadas.push([url, opts]); return 'OK'; };
  sandbox.window.AuthService = undefined;
  const fn = new Function('window', 'localStorage', wrapperSrc
      + '; return window.fetch;');
  const fetchWrapped = fn(sandbox.window, sandbox.localStorage);

  const r1 = fetchWrapped('/api/folha/ferias', { method: 'GET' });
  check('wrapper delega para o fetch original e retorna o resultado',
        r1 === 'OK' && chamadas.length === 1, JSON.stringify(chamadas));
  check('wrapper injeta X-Auth-Token em URLs /api/',
        chamadas[0][1].headers['X-Auth-Token'] === 'tok-test',
        JSON.stringify(chamadas[0][1]));

  const r2 = fetchWrapped('/api/folha/ferias/incluir', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: 'funcionario_id=1',
  });
  check('wrapper preserva Content-Type/form-urlencoded dos POSTs',
        chamadas[1][1].headers['Content-Type'] === 'application/x-www-form-urlencoded' &&
        chamadas[1][1].body === 'funcionario_id=1' &&
        chamadas[1][1].headers['X-Auth-Token'] === 'tok-test',
        JSON.stringify(chamadas[1][1]));

  const r3 = fetchWrapped('/pages/folha.html', { method: 'GET' });
  check('wrapper NÃO injeta token fora de /api/ (páginas/estáticos)',
        r3 === 'OK' && chamadas[2][1].headers === undefined,
        JSON.stringify(chamadas[2][1]));
}

finalizar('badge e toast conferidos (código real da página)');
