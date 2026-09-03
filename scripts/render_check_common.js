// Módulo compartilhado dos checks de render (Node).
//
// check_render_ferias_node.js, check_render_rescisao_node.js,
// check_render_rh_dashboard_node.js e check_render_rh_workflow_node.js
// executam o código REAL das páginas (pages/folha.html e
// pages/rh_dashboard.html) com DOM stub; o boilerplate (leitura do HTML,
// helper check() com contador de falhas e o resumo final com exit code) vive
// aqui para não duplicar.
'use strict';

const fs = require('fs');
const path = require('path');

/** Lê uma página do projeto (raiz = scripts/..). Default: pages/folha.html. */
function leHtml(pagina) {
  const ROOT = path.join(__dirname, '..');
  return fs.readFileSync(path.join(ROOT, 'pages', pagina || 'folha.html'), 'utf8');
}

/**
 * Cria um checker com:
 *   check(nome, cond, extra) — imprime PASS/FAIL e acumula falhas;
 *   finalizar(msgOk)         — imprime o resumo e encerra (exit 0/1).
 */
function criaChecker() {
  let falhas = 0;
  function check(nome, cond, extra) {
    const ok = !!cond;
    console.log((ok ? 'PASS' : 'FAIL') + ' - ' + nome + (ok ? '' : ' :: ' + (extra || '')));
    if (!ok) falhas++;
  }
  function finalizar(msgOk) {
    console.log(falhas === 0 ? '\nRENDER OK — ' + msgOk : `\n${falhas} falha(s)`);
    process.exit(falhas === 0 ? 0 : 1);
  }
  return { check, finalizar };
}

module.exports = { leHtml, criaChecker };
