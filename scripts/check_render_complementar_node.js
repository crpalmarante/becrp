#!/usr/bin/env node
// Verificação determinística do render da aba Complementar (RFC-013) usando
// o CÓDIGO REAL extraído de pages/folha.html.
//
// Mesmo padrão do check_render_ferias_node.js / check_render_rescisao_node.js:
// executa exatamente as expressões que a página renderiza — badges de situação
// (badgeComp), gating dos botões por estado (Validar/Fechar/Pagar/Holerite/
// Excluir), destaque vermelho de diferença negativa e o hook da aba no
// ativarAba — com DOM stub e dados equivalentes aos do seed do smoke.
//
// Uso: node scripts/check_render_complementar_node.js
'use strict';
const { leHtml, criaChecker } = require('./render_check_common.js');

const html = leHtml();
const { check, finalizar } = criaChecker();

// 1) badgeComp — badges de situação por estado (C/V/F/P)
// Captura o mapa REAL da página (const map={C:...,V:...,F:...,P:...}) e o
// retorno da função badgeComp; executa com os 4 estados e um desconhecido.
const mapBadge = html.match(/const map=\{C:'<span class="badge">CALCULADA<\/span>',V:'<span class="badge" style="background:#1565c0;">VALIDADA<\/span>',F:'<span class="badge" style="background:#6a1b9a;">FECHADA<\/span>',P:'<span class="badge" style="background:#2e7d32;">PAGA<\/span>'\}/);
check('folha.html contém o mapa de badges badgeComp (C/V/F/P com cores)',
      !!mapBadge, 'padrão não encontrado');

if (mapBadge) {
  const retBadge = html.match(/return map\[s\]\|\|'<span class="badge">'\+s\+'<\/span>';/);
  check('badgeComp devolve fallback para estado desconhecido', !!retBadge);
  // Corpo: mapa real + return real da página; o retorno é o próprio retBadge
  // (para estado desconhecido cai no fallback com o texto cru).
  const corpo = mapBadge[0] + '; ' + (retBadge ? retBadge[0] : "return map[s] || '';");
  const fn = new Function('s', corpo);
  const badges = {
    C: fn('C'),
    V: fn('V'),
    F: fn('F'),
    P: fn('P'),
  };
  check('badge CALCULADA renderiza para situação C', badges.C.includes('CALCULADA') && badges.C.includes('badge'));
  check('badge VALIDADA renderiza para situação V (com cor própria)',
        badges.V.includes('VALIDADA') && badges.V.includes('#1565c0'));
  check('badge FECHADA renderiza para situação F (com cor própria)',
        badges.F.includes('FECHADA') && badges.F.includes('#6a1b9a'));
  check('badge PAGA renderiza para situação P (com cor própria)',
        badges.P.includes('PAGA') && badges.P.includes('#2e7d32'));
  check('estado desconhecido cai no fallback com o texto cru', fn('X').includes('X'));
}

// 2) Gating dos botões por estado (carregarComplementares) — cada situação
// expõe exatamente as ações previstas no fluxo RFC-013 (C→V→F→P).
// Captura o trecho real (const s + const acoes + os ifs de push) e o executa
// como função de x — avalia o gating exatamente como o browser faria.
const acoesSrc = html.match(/const s=x\.situacao\|\|'C';[\s\S]*?Excluir<\/button>'\);}/);
check('folha.html contém a montagem de ações por estado (const s + acoes.push)',
      !!acoesSrc, 'padrão não encontrado');

if (acoesSrc) {
  const monta = new Function('x', acoesSrc[0] + '; return acoes.join(" ");');
  const c = monta({ id: 1, situacao: 'C' });
  check('C: botões Validar + Holerite + Excluir (sem Fechar/Pagar)',
        c.includes('Validar') && c.includes('Holerite') && c.includes('Excluir') &&
        !c.includes('Fechar') && !c.includes('Pagar'), c);
  const v = monta({ id: 2, situacao: 'V' });
  check('V: botões Fechar + Holerite + Excluir (sem Validar/Pagar)',
        v.includes('Fechar') && v.includes('Holerite') && v.includes('Excluir') &&
        !v.includes('Validar') && !v.includes('Pagar'), v);
  const f = monta({ id: 3, situacao: 'F' });
  check('F: botões Pagar + Holerite + Excluir (sem Validar/Fechar)',
        f.includes('Pagar') && f.includes('Holerite') && f.includes('Excluir') &&
        !f.includes('Validar') && !f.includes('Fechar'), f);
  const p = monta({ id: 4, situacao: 'P' });
  check('P: botões Holerite apenas (complementar paga é imutável — sem Excluir)',
        p.includes('Holerite') && !p.includes('Excluir') && !p.includes('Pagar'), p);
}

// 3) Destaque vermelho para diferença negativa (valor contra o funcionário)
const negExpr = html.match(/\(parseFloat\(x\.valor\)<0\?'<span style="color:#c62828;">':''\)\+fmt\(x\.valor\)\+\(parseFloat\(x\.valor\)<0\?'<\/span>':''\)/);
check('folha.html contém a expressão de cor vermelha para valor negativo',
      !!negExpr, 'padrão não encontrado');

if (negExpr) {
  // fmt global é definido pela página; o check usa um stub equivalente
  const fmt = (v) => String(v);
  const render = new Function('fmt', 'x', 'return ' + negExpr[0]);
  const neg = render(fmt, { valor: -200 });
  check('valor negativo renderiza em vermelho (#c62828)', neg.includes('#c62828'), neg);
  const pos = render(fmt, { valor: 500 });
  check('valor positivo renderiza SEM cor de destaque', !pos.includes('#c62828'), pos);
}

// 4) Hook da aba no ativarAba + linha do motivo com tooltip + toast de erro
check('ativarAba dispara carregarComplementares para aba-complementar',
      html.includes("if(id==='aba-complementar'){carregarComplementares()}"));
check('tabela renderiza motivo com tooltip (title) e colunas Operador/Aprovador',
      html.includes("String(x.motivo||'').replace(/\"/g,'&quot;')") &&
      html.includes("x.operador||'-'") && html.includes("x.aprovador||'-'"));
check('erro de carregamento mostra toast de erro',
      html.includes("mostrarToast('Erro ao carregar complementares','error')"));

// 5) Coluna do holerite: a tabela sempre oferece o botão Holerite (Regra 5)
check('tabela oferece o botão Holerite para toda linha',
      html.includes("acoes.push('<button class=\"btn btn-sm\" onclick=\"verHoleriteComplementar('+x.id+')\">Holerite</button>')"));

finalizar('badges de situação e gating de botões da aba Complementar conferidos (código real da página)');
