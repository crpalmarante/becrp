#!/usr/bin/env node
// Verificação determinística do render do workflow no RH Dashboard
// (pages/rh_dashboard.html) usando o CÓDIGO REAL da página.
//
// O workflow global tem três pontos sensíveis à role do usuário:
//   1) setWorkflowRole(role, name) — troca a role simulada (select do header),
//      atualiza o rótulo #wf-current-role e re-renderiza os steppers;
//   2) gating de botões — for (const [targetCode, tdef] of Object.entries(...))
//      com if (allowedRoles.includes(currentUserRole)); o botão só existe para
//      roles permitidas (tdef.roles);
//   3) histórico — history.forEach(h => ...) renderiza cada entrada com o
//      badge .wf-role-badge contendo h.user_role, e a transição envia
//      params.set('user_role', currentUserRole) para a API.
// Este check executa exatamente esses trechos com DOM/stubs globais.
//
// Uso: node scripts/check_render_rh_workflow_node.js
'use strict';
const { leHtml, criaChecker } = require('./render_check_common.js');

const html = leHtml('rh_dashboard.html');
const { check, finalizar } = criaChecker();

// 1) Header estático: rótulo da função atual + select de simulação (5 roles)
check('header tem o rótulo #wf-current-role com default "rh"',
      html.includes('id="wf-current-role">rh<'));
check('select de simulação oferece as 5 roles (employee/manager/rh/financial/admin)',
      ['employee', 'manager', 'rh', 'financial', 'admin']
        .every(r => html.includes('value="' + r + '"'))
      && html.includes('value="rh" selected'));

// 2) CSS do badge de role (azul — mesma família do wf-stepper)
check('CSS .wf-role-badge presente (fundo #e3f2fd / texto #1565c0)',
      html.includes('.wf-role-badge') && html.includes('#e3f2fd') && html.includes('#1565c0'));

// 3) Default da role no JS
check('default JS de currentUserRole = admin',
      html.includes("let currentUserRole = 'admin';"));

// 4) setWorkflowRole: função real (atualiza role, rótulo e re-render)
const setFn = html.match(/function setWorkflowRole\(role, name\) \{([\s\S]*?)\n\}/);
check('setWorkflowRole(role, name) presente (código real extraído)',
      !!setFn, 'padrão não encontrado');

if (setFn) {
  const wfRoleEl = { textContent: '' };
  const steppers = [{}, {}, {}];
  let renders = 0;
  global.currentUserRole = 'admin';
  global.currentUserName = 'Admin';
  global.document = {
    getElementById: (id) => (id === 'wf-current-role' ? wfRoleEl : null),
    querySelectorAll: () => steppers,
  };
  global.renderWorkflow = () => { renders++; };
  const setRole = new Function('role', 'name', setFn[1]);
  setRole('financial', 'Financeiro');
  check('setWorkflowRole atualiza currentUserRole',
        global.currentUserRole === 'financial', global.currentUserRole);
  check('setWorkflowRole atualiza currentUserName (fallback para role)',
        global.currentUserName === 'Financeiro', global.currentUserName);
  check('setWorkflowRole atualiza o rótulo #wf-current-role',
        wfRoleEl.textContent === 'financial', wfRoleEl.textContent);
  check('setWorkflowRole re-renderiza todos os steppers (renderWorkflow)',
        renders === steppers.length, String(renders));
  delete global.document;
  delete global.renderWorkflow;
  delete global.currentUserRole;
  delete global.currentUserName;
}

// 5) Gating de botões por role: só mostra transição se currentUserRole ∈ tdef.roles
const loopExpr = html.match(/for \(const \[targetCode, tdef\] of Object\.entries\(transitions\)\) \{[\s\S]*?btns \+= '<\/div>';/);
check('loop de transições com gating por role presente (código real extraído)',
      !!loopExpr, 'padrão não encontrado');

if (loopExpr) {
  global.currentUserRole = 'rh';
  global.statusMap = { aprovado: { color: '#2e7d32', icon: 'OK' } };
  global.module = 'rescisao';
  global.recordId = 5;
  global.hasButtons = false;
  global.btns = '<div style="display:flex;gap:6px;flex-wrap:wrap;margin:6px 0;">';
  const renderBtns = new Function('transitions', loopExpr[0]);
  renderBtns({ aprovado: { roles: ['rh', 'admin'], label: 'Aprovar' } });
  check('role permitida → botão renderizado (label + execWorkflowTransition)',
        global.hasButtons === true
        && global.btns.includes('Aprovar')
        && global.btns.includes('execWorkflowTransition')
        && global.btns.includes("'aprovado'") && global.btns.includes(",5,"),
        global.btns);

  global.currentUserRole = 'employee'; // fora de tdef.roles
  global.hasButtons = false;
  global.btns = '<div style="display:flex;gap:6px;flex-wrap:wrap;margin:6px 0;">';
  renderBtns({ aprovado: { roles: ['rh', 'admin'], label: 'Aprovar' } });
  check('role não permitida → sem botão (hasButtons false)',
        global.hasButtons === false && !global.btns.includes('Aprovar'),
        global.btns);
  delete global.currentUserRole;
  delete global.statusMap;
  delete global.module;
  delete global.recordId;
  delete global.hasButtons;
  delete global.btns;
}

// 6) Expressão do badge de role no histórico (h.user_role)
const badgeExpr = html.match(/'<span class="wf-role-badge">'\+h\.user_role\+'<\/span>'/);
check('expressão do badge de role presente no histórico',
      !!badgeExpr, 'padrão não encontrado');

if (badgeExpr) {
  const badgeDe = new Function('h', 'return ' + badgeExpr[0]);
  check('badge de role renderiza o user_role do registro',
        badgeDe({ user_role: 'rh' }) === '<span class="wf-role-badge">rh</span>',
        badgeDe({ user_role: 'rh' }));
}

// 7) Bloco real do histórico: history.forEach com timestamp, transição, badge e nome
const histExpr = html.match(/history\.forEach\(h => \{[\s\S]*?h\.user_name\+'<\/span><\/div>';[\s\S]*?\n\s*\}\);/);
check('histórico renderiza cada entrada com o badge de role (código real extraído)',
      !!histExpr, 'padrão não encontrado');

if (histExpr) {
  global.statusMap = {
    rascunho: { icon: 'R', label: 'Rascunho' },
    aprovado: { icon: 'A', label: 'Aprovado' },
    concluido: { icon: 'C', label: 'Concluido' },
  };
  global.html = '';
  const renderHist = new Function('history', histExpr[0]);
  renderHist([
    { timestamp: '2026-08-01 10:00', from_status: 'rascunho', to_status: 'aprovado', user_role: 'rh', user_name: 'Maria' },
    { timestamp: '2026-08-02 11:00', from_status: 'aprovado', to_status: 'concluido', user_role: 'admin', user_name: 'Joao' },
  ]);
  check('cada entrada do histórico tem badge com o user_role (2 entradas → 2 badges)',
        (global.html.match(/wf-role-badge/g) || []).length === 2
        && global.html.includes('>rh<') && global.html.includes('>admin<'),
        global.html);
  check('histórico renderiza timestamp, usuário e transição (from → to)',
        global.html.includes('2026-08-01') && global.html.includes('Maria')
        && global.html.includes('Rascunho') && global.html.includes('Aprovado'),
        global.html);
  delete global.statusMap;
  delete global.html;
}

// 8) Estado vazio do histórico: sem registros, nenhum bloco .wf-history aparece
const histEmpty = html.match(/if \(history\.length > 0\) \{[\s\S]*?html \+= '<\/div>';[\s\S]*?\n\s*\}/);
check('bloco condicional do histórico (history.length > 0) presente (código real extraído)',
      !!histEmpty, 'padrão não encontrado');

if (histEmpty) {
  global.statusMap = {
    rascunho: { icon: 'R', label: 'Rascunho' },
    aprovado: { icon: 'A', label: 'Aprovado' },
  };
  global.html = '';
  const renderHistEmpty = new Function('history', histEmpty[0]);
  renderHistEmpty([]);
  check('histórico vazio → nenhum .wf-history renderizado',
        global.html === '' && !global.html.includes('wf-history'),
        global.html || '(vazio)');
  delete global.statusMap;
  delete global.html;
}

// 9) execWorkflowTransition envia a role atual para a API (badge ↔ API)
const paramsExpr = html.match(/params\.set\('user_name', currentUserName\);\s*params\.set\('user_role', currentUserRole\);/);
check('transição envia user_name e user_role (código real extraído)',
      !!paramsExpr, 'padrão não encontrado');

if (paramsExpr) {
  const captured = {};
  const params = { set: (k, v) => { captured[k] = v; } };
  global.currentUserName = 'Maria';
  global.currentUserRole = 'rh';
  new Function('params', paramsExpr[0])(params);
  check('params.user_role = currentUserRole (mesma role do badge)',
        captured.user_role === 'rh' && captured.user_name === 'Maria',
        JSON.stringify(captured));
  delete global.currentUserName;
  delete global.currentUserRole;
}

finalizar('workflow do RH Dashboard (role/histórico) conferido (código real da página)');
