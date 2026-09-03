#!/usr/bin/env node
// Verificação determinística do render do badge EM DOBRO e do toast de alerta
// da aba Rescisão (RFC-003 — férias vencidas pagas em dobro) usando o CÓDIGO
// REAL extraído de pages/folha.html.
//
// Mesmo padrão do check_render_ferias_node.js: executa exatamente as
// expressões que a página renderiza (badge na tabela de rescisões + toast ao
// registrar + lógica do badge do resumo + span estático inicial) com DOM stub.
//
// Uso: node scripts/check_render_rescisao_node.js
'use strict';
const { leHtml, criaChecker } = require('./render_check_common.js');

const html = leHtml();
const { check, finalizar } = criaChecker();

// 1) Expressão do badge EM DOBRO na tabela de rescisões (carregarRescisoes)
const badgeExpr = html.match(/\(res\.ferias_venc_dobro\?'<span class="badge-vencida" title="Ferias vencidas pagas em dobro">EM DOBRO<\/span>':''\)/);
check('folha.html contém a expressão do badge EM DOBRO na tabela (res.ferias_venc_dobro → span)',
      !!badgeExpr, 'padrão não encontrado');

if (badgeExpr) {
  // new Function com parâmetro explícito (mesma estratégia das seções 2/3 —
  // evita dependência do escopo léxico, que o eval strict-mode não enxerga)
  const badgeDe = new Function('res', 'return ' + badgeExpr[0]);
  const htmlDobro = badgeDe({ ferias_venc_dobro: true });
  check('badge presente quando res.ferias_venc_dobro=true (contém badge-vencida e EM DOBRO)',
        htmlDobro.includes('badge-vencida') && htmlDobro.includes('EM DOBRO'), htmlDobro);
  check('tooltip do badge da tabela cita férias vencidas pagas em dobro',
        htmlDobro.includes('Ferias vencidas pagas em dobro'));

  const htmlNormal = badgeDe({ ferias_venc_dobro: false });
  check('badge AUSENTE quando res.ferias_venc_dobro=false (expressão vazia)',
        htmlNormal === '', htmlNormal);
}

// 2) Toast ao registrar rescisão com vencidas (calcularRescisao) — o else fica
// na linha seguinte no HTML, então o padrão permite whitespace (\s*) entre eles
const toastCall = html.match(/if\(data\.ferias_venc_dobro\) mostrarToast\('ALERTA: ferias vencidas em DOBRO na rescisao!','warning'\);\s*else mostrarToast\('Rescisao registrada!','success'\);/);
check('folha.html contém o toast de alerta (ALERTA: ferias vencidas em DOBRO + warning)',
      !!toastCall, 'padrão não encontrado');

if (toastCall) {
  const toasts = [];
  global.mostrarToast = (msg, tipo) => toasts.push([msg, tipo]);
  const avaliar = new Function('data', toastCall[0]);

  avaliar({ ferias_venc_dobro: true });
  check('toast de vencidas → mensagem ALERTA + tipo warning',
        toasts.length === 1 && toasts[0][0] === 'ALERTA: ferias vencidas em DOBRO na rescisao!' &&
        toasts[0][1] === 'warning', JSON.stringify(toasts));

  toasts.length = 0;  // assert auto-contido para o cenário normal
  avaliar({ ferias_venc_dobro: false });
  check('toast normal → mensagem "Rescisao registrada!" + tipo success',
        toasts.length === 1 && toasts[0][0] === 'Rescisao registrada!' && toasts[0][1] === 'success',
        JSON.stringify(toasts));
}

// 3) Lógica do badge do resumo (rescisao-ferias-dobro): display inline-block/none
const sumExpr = html.match(/dbl\.style\.display=data\.ferias_venc_dobro\?'inline-block':'none';/);
check('folha.html contém a lógica do badge do resumo (display conforme ferias_venc_dobro)',
      !!sumExpr, 'padrão não encontrado');

if (sumExpr) {
  const mostrarResumo = new Function('dbl', 'data', sumExpr[0]);
  let dbl = { style: {} };
  mostrarResumo(dbl, { ferias_venc_dobro: true });
  check('resumo: badge visível (inline-block) quando há vencidas', dbl.style.display === 'inline-block', dbl.style.display);

  dbl = { style: {} };
  mostrarResumo(dbl, { ferias_venc_dobro: false });
  check('resumo: badge oculto (none) quando não há vencidas', dbl.style.display === 'none', dbl.style.display);
}

// 4) Span estático inicial do resumo: escondido por padrão e com o texto EM DOBRO
const spanEstatico = html.match(/<span id="rescisao-ferias-dobro" class="badge-vencida" style="display:none;" title="Ferias vencidas \(periodo concessivo estourado\) pagas em dobro - apenas o salario">EM DOBRO<\/span>/);
check('resumo: span #rescisao-ferias-dobro existe, inicia display:none e com texto EM DOBRO',
      !!spanEstatico, 'padrão não encontrado');

finalizar('badge EM DOBRO e toast conferidos (código real da página)');
