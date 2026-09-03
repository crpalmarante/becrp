#!/usr/bin/env node
// Verificação determinística do render do alerta de férias vencidas no RH
// Dashboard (pages/rh_dashboard.html) usando o CÓDIGO REAL da página.
//
// O card "Alertas de Contrato" lista os alertas_contrato do GET
// /api/rh/dashboard; cada linha tem um badge cuja classe depende do tipo:
//   a.tipo === 'Ferias vencidas' → badge-alerta (vermelho)
//   qualquer outro tipo          → badge-pendente (laranja)
// Este check executa exatamente a expressão renderizada (linha da tabela +
// estado vazio + CSS do badge) com DOM stub.
//
// Uso: node scripts/check_render_rh_dashboard_node.js
'use strict';
const { leHtml, criaChecker } = require('./render_check_common.js');

const html = leHtml('rh_dashboard.html');
const { check, finalizar } = criaChecker();

// 1) Expressão do badge na tabela de alertas (carregarDashboard)
const badgeExpr = html.match(/a\.tipo==='Ferias vencidas'\?'badge-alerta':'badge-pendente'/);
check('rh_dashboard.html contém a expressão do badge (a.tipo===\'Ferias vencidas\' → badge-alerta)',
      !!badgeExpr, 'padrão não encontrado');

if (badgeExpr) {
  const badgeDe = new Function('a', 'return ' + badgeExpr[0]);
  check('férias vencidas → classe badge-alerta',
        badgeDe({ tipo: 'Ferias vencidas' }) === 'badge-alerta',
        badgeDe({ tipo: 'Ferias vencidas' }));
  check('outro tipo (ex.: licença) → classe badge-pendente',
        badgeDe({ tipo: 'Licenca vencida' }) === 'badge-pendente',
        badgeDe({ tipo: 'Licenca vencida' }));
}

// 2) Bloco de render da tabela de alertas (nome, badge, data, dias) — o
// corpo do map fica em várias linhas, então o padrão ancora o início
// (alertas.map(a=>) e o fechamento real do template ('</tr>'\n).join('');)
// com [\s\S]*? no meio; se o template da linha mudar, atualize junto.
const linhaExpr = html.match(/ta\.innerHTML=alertas\.map\(a=>[\s\S]*?'<\/tr>'\s*\)\.join\(''\);/);
check('rh_dashboard.html renderiza a linha do alerta (nome, badge, data, dias)',
      !!linhaExpr, 'padrão não encontrado');

if (linhaExpr) {
  const ta = { innerHTML: '' };
  const alertas = [
    { nome: 'Ana', tipo: 'Ferias vencidas', data: '2028-02-01', dias: 90 },
    { nome: 'Bia', tipo: 'Licenca vencida', data: '', dias: 0 },
  ];
  const render = new Function('ta', 'alertas', linhaExpr[0]);
  render(ta, alertas);
  check('linha de férias vencidas contém badge-alerta e o tipo',
        ta.innerHTML.includes('badge-alerta') && ta.innerHTML.includes('Ferias vencidas'),
        ta.innerHTML);
  check('linha de outro tipo contém badge-pendente (sem badge-alerta duplicado)',
        ta.innerHTML.includes('badge-pendente')
        && (ta.innerHTML.match(/badge-alerta/g) || []).length === 1,
        ta.innerHTML);
  check('nome, data e dias renderizados (chaves da tela)',
        ta.innerHTML.includes('Ana') && ta.innerHTML.includes('Bia')
        && ta.innerHTML.includes('2028-02-01') && ta.innerHTML.includes('90'),
        ta.innerHTML);
}

// 3) Estado vazio: mensagem quando não há alertas pendentes
check('rh_dashboard.html trata lista vazia (Nenhum alerta pendente)',
      html.includes('Nenhum alerta pendente'));

// 4) CSS do badge-alerta (vermelho — mesma família do badge VENCIDA)
check('CSS .badge-alerta vermelho presente',
      html.includes('.badge-alerta') && html.includes('#c62828'));

finalizar('badge de férias vencidas do RH Dashboard conferido (código real da página)');
