# Relatório Final — Módulo de Folha de Pagamento (RFC-001 a 016)

> **Estado: ✅ 16/16 RFCs fechados e aprovados** · CI: **23 ✅ / 0 ❌**
> Emissão: 11/08/2026 · Sprint `RFC-EMPLOYEE` · Fontes: `RFC-CHECKLIST-fechamento.md`,
> `RFC-MAPA-telas.md`, `RFC-MAPA-encadeamento.md`, cabeçalhos das RFCs em `rfcs/`,
> logs do `scripts/run_ci.py` e rastreabilidade registrada em cada RFC.

---

## 1. Resumo executivo

O módulo de folha de pagamento do ERP COBOL foi **implementado, validado e fechado**
por completo: os **16 RFCs** (RFC-001 conceitual + RFC-002…016 de implementação) estão
com status **✅ Implementado/Concluído** e **✅ Aprovado** (voto `crpalmarante`), sem
bloqueios de fechamento.

A entrega combina o **motor de cálculo em COBOL** (GnuCOBOL, `folha_pagamento.cbl`),
orquestração em **Python** (`cobol_bridge.py` + `server.py`) e **telas HTML/JS puro**
com validações determinísticas no CI: 14 smokes COBOL/RFC, 4 reviews de tela via HTTP,
5 checks de render **Node** (código real das páginas com DOM stub), 2 cenários visuais
`--browser` (passo 9) e trilha de auditoria em todas as transições (RFC-009/015).

Durante o fechamento foram corrigidos **dois bugs reais** encontrados nas revisões:
o **bug de gravação de rescisões** (2ª+ rescisão herdava valores da 1ª — §5) e o
**nome vazio** nas rescisões registradas pelo form (§6).

---

## 2. Os 16 RFCs do módulo

| RFC | Título | Status | Aprovação | Fechado? |
|---|---|---|---|---|
| RFC-001 | Conceitos gerais do sistema de Folha de Pagamento | ✅ Concluído (11/08/2026) — conceitual, sem código | ✅ Aprovado (11/08/2026) | ✅ |
| RFC-002 | Cadastro de Funcionário: o que cadastrar | ✅ Implementado (31/07/2026) | ✅ Aprovado (10/08/2026) | ✅ |
| RFC-003 | Processos de Admissão e Demissão (Rescisão) | ✅ Implementado (09/08/2026) | ✅ Aprovado (10/08/2026) | ✅ |
| RFC-004 | Conceito de Evento: proventos, descontos e sua aplicação | ✅ Implementado (10/08/2026) | ✅ Aprovado (10/08/2026) | ✅ |
| RFC-005 | Conceito de tabelas fiscais: INSS, IRRF e salário-família | ✅ Implementado (10/08/2026) | ✅ Aprovado (10/08/2026) | ✅ |
| RFC-006 | O processo mensal: do fechamento ao pagamento | ✅ Implementado (10/08/2026) | ✅ Aprovado (10/08/2026) | ✅ |
| RFC-007 | Conceito e conteúdo do holerite | ✅ Implementado (10/08/2026) | ✅ Aprovado (10/08/2026) | ✅ |
| RFC-008 | Cadastros mestres: Empresa, Departamentos e Cargos | ✅ Implementado (10/08/2026) | ✅ Aprovado (10/08/2026) | ✅ |
| RFC-009 | Usuários, papéis, autorização e trilha de auditoria | ✅ Implementado (11/08/2026) | ✅ Aprovado (11/08/2026) | ✅ |
| RFC-010 | Processo de férias: aquisição, gozo e pagamento | ✅ Implementado (10/08/2026) | ✅ Aprovado (10/08/2026) | ✅ |
| RFC-011 | Processo de 13º salário (gratificação natalina) | ✅ Implementado (10/08/2026) | ✅ Aprovado (10/08/2026) | ✅ |
| RFC-012 | Afastamentos, licenças e suspensões do vínculo | ✅ Implementado (11/08/2026) | ✅ Aprovado (11/08/2026) | ✅ |
| RFC-013 | Folha complementar: ajustes de competência fechada | ✅ Implementado (11/08/2026) | ✅ Aprovado (11/08/2026) | ✅ |
| RFC-014 | Encargos patronais: FGTS, INSS patronal, RAT e terceiros | ✅ Implementado (11/08/2026) | ✅ Aprovado (11/08/2026) | ✅ |
| RFC-015 | Relatórios gerenciais e fechamento da competência | ✅ Implementado (11/08/2026) | ✅ Aprovado (11/08/2026) | ✅ |
| RFC-016 | Movimentações contratuais: alterações com vigência | ✅ Implementado (09/08/2026) | ✅ Aprovado (10/08/2026) | ✅ |

### O que cada RFC entrega (resumo)

| Grupo | RFCs | Entrega |
|---|---|---|
| **Fundação** | 001, 002, 008, 016 | Mapa conceitual do módulo; cadastro de funcionário (CPF/PIS/CBO, obrigatórios, máscaras, dependentes com `sal_familia`/IRRF); cadastros mestres (empresa, departamentos, cargos); movimentações contratuais (cargo/departamento/salário) com **vigência** e bloqueio retroativo sobre competências fechadas |
| **Regras & cálculo** | 004, 005, 006 | Eventos proventos/descontos; tabelas fiscais **por competência** (INSS progressivo, IRRF, **salário-família** com teto e valor por dependente); processamento mensal completo (abrir → calcular → validar → concluir → fechar → pagar) |
| **Produtos da folha** | 007, 010, 011, 013 | Holerite (geração, conteúdo, valores e encargos **fora** do holerite); férias (aquisição/gozo/pagamento, **vencidas em dobro** com badge VENCIDA e toast); 13º (1ª parcela sem INSS/IRRF, 2ª/única com descontos); folha **complementar** (competência fechada, motivo obrigatório, limite legal 70%, fluxo C→V→F→P) |
| **Relações de trabalho** | 003, 012 | Rescisão (verbas do acerto, aviso prévio, férias **EM DOBRO**, 13º prop., FGTS+multa, prazo de pagamento, acerto imutável após pagamento); afastamentos/licenças (pró-rata por dias, situação do vínculo, suspensão do aquisitivo >30 dias) |
| **Governança** | 009, 014, 015 | Trilha de auditoria append-only (quando/quem/ação/antes/depois/tabelas) com **separação de funções** (Aprovador ≠ Operador, Tesouraria ≠ Aprovador); encargos patronais (FGTS, INSS 20%, RAT/SAT, terceiros — Simples Nacional unificado DAS); relatório de encargos + **anexo de auditoria** no fechamento |

---

## 3. Cobertura por tela

Ver detalhes em **`RFC-MAPA-telas.md`**. Resumo das páginas que materializam o módulo:

| Tela | RFC(s) | Destaques |
|---|---|---|
| `funcionarios.html` | 002, 003, 016 | Máscaras CPF/CNPJ/PIS/CBO/telefone/moeda, validação de dígito do CPF, exame admissional vencido bloqueia admissão, histórico salarial/movimentações com vigência |
| `folha.html` | 003, 005, 006, 007, 009–014 | Abas Processar, Holerites, Férias (badge VENCIDA), 13º, Rescisão (badge EM DOBRO), Afastamentos, Complementar (C/V/F/P), Contábil, Config, Auditoria |
| `eventos.html` / `estrutura_salarial.html` | 004, 006 | Catálogo de eventos e composição por cargo com simulação |
| `departamentos-cargos.html` / `empresa-folha.html` | 008, 014 | Mestres + CNAE/regime tributário → RAT/SAT |
| `rh_dashboard.html` | 009, 010, 012 | KPIs, **alerta de férias vencidas**, aprovações de licenças/despesas e workflow com gating por role |

---

## 4. Validações do CI — `scripts/run_ci.py`

O pipeline completo de CI do módulo (**9 passos**) roda com um comando e encerra com
restauração do seed. Última execução: **CI: 23 ✅ / 0 ❌**.

### 4.1 Etapas

1. **Build COBOL** — recompila `cobol/programs/*.cbl → cobol/bin/*` (incremental; `--force-build`
   recompila os **49 programas** do zero, como num checkout limpo do GitHub Actions)
2. **Seed** — admin `bruno/123456` (token fixo) + departamento/cargo/funcionário ativos
3. **Smokes RFC + jsonio** — 14 scripts com backup/restauração própria
4. **review_tela_folha** — fluxo HTTP completo da tela Processar Folha + Holerites
5. **review_tela_funcionarios** — máscaras CPF/moeda
6. **review_tela_ferias_decimo** — abas Férias e 13º com guarda do portal (role funcionario)
7. **Checks de render Node** — 5 scripts executam o código real das páginas com DOM stub
8. **review_tela_rh_dashboard** — KPIs, férias vencidas, aprovações e workflow
9. **`--browser` (opcional)** — sobe os cenários visuais e valida o seed via HTTP

### 4.2 Smokes COBOL/RFC (passo 3)

| Smoke | Cobre | Checks |
|---|---|---|
| `smoke_jsonio` | Concorrência e integridade do JSON (8 writers + 2 readers) | 8 ✅ |
| `smoke_rfc002_cobol` | CRUD COBOL de funcionário/depto/cargo/dependentes (CPF duplicado, inativação) | ✅ |
| `smoke_rfc003_rescisao` | Cálculo do acerto, validações, pagamento/exclusão, desligar/reativar + **regressão do bug de gravação** (§8) + **nome derivado** (§8b) | 52 ✅ |
| `smoke_rfc003_bloqueios` | Bloqueios de admissão/demissão (exame, vínculo) | 12 ✅ |
| `smoke_rfc004_eventos` | Catálogo e composição de eventos | 25 ✅ |
| `smoke_rfc005_tabelas` | Tabelas INSS/IRRF/salário-família por competência | 24 ✅ |
| `smoke_rfc006_folha` | Processamento mensal (estados e valores) | 29 ✅ |
| `smoke_rfc007_holerite` | Geração/conteúdo do holerite | 56 ✅ |
| `smoke_rfc008_empresa` | Empresa/departamentos/cargos | 24 ✅ |
| `smoke_rfc010_011_ferias_decimo` | Férias (vencidas em dobro) e 13º | 19 ✅ |
| `smoke_rfc012_afastamentos` | Licenças, situação do vínculo e pró-rata | 54 ✅ |
| `smoke_rfc013_complementar` | Folha complementar C→V→F→P e limites | 51 ✅ |
| `smoke_rfc014_encargos` | FGTS/INSS patronal/RAT/terceiros + contabilização | 25 ✅ |
| `smoke_rfc009_auditoria` | Trilha de auditoria e separação de funções | 84 ✅ |

### 4.3 Reviews de tela via HTTP (passos 4–6, 8)

| Review | Escopo | Resultado |
|---|---|---|
| `review_tela_folha` | Processar Folha + Holerites (fluxo HTTP completo) | 41 ✅ / 0 ❌ |
| `review_tela_funcionarios` | Máscaras CPF/CNPJ/PIS/CBO/telefone/moeda | ✅ |
| `review_tela_ferias_decimo` | Abas Férias/13º (badge VENCIDA, portal) | ✅ |
| `review_tela_rh_dashboard` | KPIs, alerta de vencidas, aprovações, workflow | ✅ |

### 4.4 Checks de render Node (passo 7)

Executam o **código real das páginas** com DOM stub (sem servidor): badges, toasts,
wrapper de autenticação e gating de botões. Com `node` instalado rodam sempre; na
ausência, o passo é pulado com aviso (não conta no resumo):

| Check | Valida |
|---|---|
| `check_render_ferias_node.js` | Badge **VENCIDA** + toast de alerta (férias) |
| `check_render_rescisao_node.js` | Badge **EM DOBRO** + toast ao registrar rescisão |
| `check_render_rh_dashboard_node.js` | Badge-alerta de férias vencidas no RH Dashboard |
| `check_render_rh_workflow_node.js` | Workflow: badges de role/histórico + gating por role |
| `check_render_complementar_node.js` | Aba Complementar: badges C/V/F/P + gating dos botões |

### 4.5 Cenários visuais `--browser` (passo 9)

| Cenário | Porta | Seed validado | GET |
|---|---|---|---|
| `cenario_complementar_browser.py` | 8141 | 4 complementares nos estados C/V/F/P | `/api/folha/complementares` |
| `cenario_rescisao_browser.py` | 8142 | 2 rescisões — 1 `ferias_venc_dobro=True` (EM DOBRO) + 1 normal | `/api/folha/rescisoes` |

Os mesmos cenários servem à conferência visual com **browser-use** (badge EM DOBRO,
botões por estado e toast confirmados em navegador real).

---

## 5. 🐛 Bug crítico corrigido — gravação de rescisões (RFC-003)

Encontrado durante a revisão visual do cenário de rescisão (11/08/2026):

**Sintoma** — a 2ª+ rescisão gravava os valores do acerto da **1ª** (saldo, férias,
13º, FGTS, líquido), enquanto só id/motivo/situação saíam corretos.

**Causa raiz** — o parágrafo `gravar-rescisao` do `folha_pagamento.cbl` faz um loop de
`READ` no arquivo para calcular o próximo id; cada `READ` **sobrescreve os campos
calculados `re-*`** com o último registro lido. Os smokes antigos não pegavam porque
criavam a 1ª rescisão ou conferiam apenas o id.

**Correção** — backup `ws-re-backup` do registro calculado ao final de
`calcular-rescisao` + restauração antes do `WRITE` (movido para a WORKING-STORAGE
conforme review). **Coberto pela seção 8 do `smoke_rfc003_rescisao.py`** (11 checks de
regressão: 2 rescisões em sequência com valores distintos — `venc=30` e `venc=0` —
confirmando que a 2ª não herda nada).

**Verificação visual** — browser-use na aba Rescisão: linha 1 (João) com badge
**EM DOBRO** e `9.000,00` em vencidas em dobro; linha 2 (Ana, sem vencidas) **sem**
badge e com valores próprios. CI completo recompilado: **24 ✅ / 0 ❌** na época,
**23 ✅ / 0 ❌** na versão atual (o passo 9 `--browser` só roda sob demanda).

---

## 6. Bug menor corrigido — nome vazio na rescisão registrada pelo form

O `calcularRescisao()` da tela **não envia `nome`** e o server não derivava: rescisões
registradas pelo form exibiam **"#id"** na coluna Funcionario. Correção em
`cobol_bridge.rescisao_incluir`: quando o nome não vem, busca no funcionário e grava
(cobre server e callers diretos). Validado via API e coberto pela **seção 8b** do
`smoke_rfc003_rescisao.py` ("rescisão sem nome criada" + "nome derivado do funcionário
na gravação").

---

## 7. Destaques de governança (RFC-009 / RFC-015)

- **Trilha de auditoria append-only** (`folha_auditoria.py`): lançamento, cálculo,
  mudança de estado, cadastros e tabelas — com versão das tabelas fiscais usadas no
  cálculo (reprodução da competência).
- **Separação de funções**: validação/fechamento exigem **Aprovador ≠ Operador**;
  registro de pagamento exige **Tesouraria ≠ Aprovador**.
- **Relatório de fechamento** (RFC-015): relatório de encargos HTML imprimível/PDF com
  **anexo da trilha de auditoria** da competência.

---

## 8. Artefatos e documentação do fechamento

| Artefato | Local |
|---|---|
| Checklist de fechamento (status + aprovação + bloqueios) | `docs-tecnicos/RFC-CHECKLIST-fechamento.md` |
| Mapa de rastreabilidade telas × RFCs | `docs-tecnicos/RFC-MAPA-telas.md` |
| Mapa de encadeamento (dependências entre RFCs) | `docs-tecnicos/RFC-MAPA-encadeamento.md` |
| Pipeline de CI (9 passos, passo 9 `--browser`) | `scripts/run_ci.py` (docstring + § "Como rodar o CI") |
| README do sprint (unittest + CI E2E + passo 9) | `sprints/RFC-EMPLOYEE/README.md` |
| Exemplos e diagramas (competência, holerite, encargos, fechamento) | `docs-tecnicos/` |

---

## 9. Conclusão

O módulo de folha está **funcionalmente completo e fechado** (16/16 RFCs aprovados),
com o motor de cálculo em COBOL, telas com máscaras/validações e um **CI determinístico**
que combina smokes de regras, reviews de tela via HTTP, checks de render Node com o
código real das páginas e cenários visuais opcionais. Os dois bugs encontrados nas
revisões (gravação de rescisões e nome derivado) foram corrigidos e **cobertos por
checks de regressão** para não voltarem.

**Próximos passos possíveis** (fora do escopo deste fechamento): revisão de
compatibilidade com o SEFIP/eSocial, integração bancária do pagamento da folha e
validação das tabelas fiscais 2026/2027 nos pontos de corte.
