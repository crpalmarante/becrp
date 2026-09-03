# ERP COBOL — Folha de Pagamento

> ERP 100% caseiro, sem frameworks, sem bibliotecas externas e sem CDN.
> Backend: **COBOL + Python + PostgreSQL** · Frontend: **HTML + CSS + JS puro**
> COBOL é o **motor de regras de negócio** (chamado via `ctypes`); Python orquestra; PostgreSQL é o banco único.

Módulo MVP: **Folha de Pagamento** (INSS/IRRF progressivos, horas extras, faltas, fechamento por competência).

---

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend | HTML + CSS + JS puro (ES modules) — design system próprio, zero CDN |
| Servidor web | Python stdlib (`http.server.ThreadingHTTPServer`) |
| Motor de negócio | **GnuCOBOL** (`cobc -m` → `.so`) via `ctypes` |
| Banco de dados | PostgreSQL (SQL puro + migrations próprias) |
| Driver | `psycopg` (única dependência de runtime obrigatória; nos testes de integração, `psycopg2`) |

Regra crítica: os `.so` COBOL são carregados **uma única vez no startup**
(`libcob.cob_init`) — nunca por requisição (risco de `SIGSEGV`).

---

## Estrutura do projeto

```
erp_cobol/
├── README.md          # este documento
├── PLAN_ERP.md        # plano do projeto (visão, arquitetura, decisões, testes, CI)
├── rfcs/              # RFCs 001–016 (conceitos, folha, holerite, tabelas fiscais, …)
├── RFC-COMISSION/     # RFCs do módulo de comissões (001–008: política, PDV, dados, telas, apuração)
├── docs-tecnicos/     # exemplos e diagramas (EXEMPLO-competencia.md, holerite, encargos, …)
├── cobol/             # fontes .cbl + .cpy e .so compilados (PAYCALC, CALCEVENT, TAXCALC)
├── db/                # migrations SQL (002…018: cadastros, usuários, permissões, folha, tabelas fiscais, holerite, comissões do PDV — product_categories/products/commission_rules/pos_sales/commission_global_rules)
├── tests/             # unittest (COBOL ctypes + integração Postgres) + runner + helper
└── web/ core/ static/ # (planejados) servidor HTTP · orquestração Python · frontend
```

Documentação de referência:

- **`PLAN_ERP.md`** — plano de projeto, arquitetura, decisões registradas e a seção **7. Testes**
  (inclui o workflow de CI de referência na **7.5**).
- **`rfcs/RFC-001…016`** — especificações técnicas do domínio (RFC-005 tabelas fiscais,
  RFC-006 processamento, RFC-007 holerite, RFC-009 usuários/papéis/auditoria, …).
- **`RFC-COMISSION/RFC-001…008`** — módulo de comissões de vendas: política e reflexos
  (001), apuração no PDV por produto/categoria/taxa padrão (002), modelo de dados com a
  migration db/016 (003), tela de categorias e regras por categoria (004), apuração das
  vendas do PDV com detalhe por venda (005), a tela de produtos e regras por produto (006),
  a tela de taxa padrão do funcionário (007) e a tela de taxa padrão GLOBAL da empresa (008,
  nova tabela `commission_global_rules` — db/018).
- **`docs-tecnicos/`** — exemplo numérico completo de competência, template de holerite
  imprimível, relatório de encargos, diagramas Mermaid, o mapa de telas × RFCs
  (`RFC-MAPA-telas.md`) e o **`RELATORIO-FINAL-folha.md`** — fechamento consolidado dos
  16 RFCs, validações do CI e bugs corrigidos (11/08/2026).

---

## Como rodar os testes

A suíte inteira (COBOL + integração Postgres) roda com **um comando**:

```bash
bash tests/run_all.sh            # build incremental + suíte completa
bash tests/run_all.sh --rebuild  # força a recompilação dos .so COBOL
```

O runner (`tests/run_all.sh`) faz:

1. **Build incremental do COBOL** — recompila `taxcalc.so`, `calcevent.so` e `paycalc.so`
   (`cobc -m`) apenas quando um `.so` falta ou a fonte `.cbl` é mais nova. Sem `cobc` e com
   build pendente → falha com a instrução de compilação manual.
2. **`unittest discover`** — descobre os 8 arquivos de teste em `tests/` e propaga o
   exit code (adequado para CI).

### Requisitos

| Ferramenta | Necessária para | Opcional? |
|---|---|---|
| `python3` (stdlib) | rodar a suíte | — |
| `cobc` (GnuCOBOL) | compilar os `.so` (quando faltam/desatualizam) | ✅ se os `.so` já existirem — num clone novo (`.so` são gitignored) é obrigatório na 1ª execução |
| `psycopg2` | testes de integração Postgres | ✅ sem ele, a parte de integração pula |
| Binários do PG (`initdb`/`pg_ctl`) **ou** `ERP_TEST_DATABASE_URL` | backend dos testes de integração | ✅ sem ambos, pula graciosamente |

> Os testes de integração **pulam graciosamente** quando falta ambiente (psycopg2,
> binários do PG ou URL) — nunca falham por falta de dependência.

### O que a suíte cobre

| Família | Arquivos | Valida |
|---|---|---|
| **COBOL via ctypes** | `test_ctypes_taxcalc.py` · `test_ctypes_calcevent.py` · `test_ctypes_paycalc.py` | INSS/IRRF progressivos (RFC-005), eventos da folha (RFC-004), resultado completo com proventos/descontos/bases/líquido (RFC-007) |
| **Integração Postgres** | `test_permissions_integration.py` · `test_state_machine_integration.py` · `test_runs_lines_integration.py` · `test_tax_tables_integration.py` · `test_stubs_integration.py` · `test_commission_rules_integration.py` · `test_payroll_accounting_integration.py` · `test_commission_accounting_integration.py` · `test_commission_detail_accounting_integration.py` | Matriz de permissões ação×papel (011), máquina de estados do RFC-006 (010), execução/resultado da folha (012), tabelas fiscais por competência (013), holerite por funcionário/execução (014), módulo de comissões do PDV (016/017), contabilização da folha (RFC-Payroll 001–002), contabilização da comissão — evento 7 (RFC-Payroll/003), detalhamento por venda de origem no lançamento (RFC-Payroll/004) |

### Os dois modos de backend de integração

O helper `tests/pg_bootstrap.py` provê o PostgreSQL dos testes de integração em
**dois modos** — `test_backend_available()` decide qual (e se) a suíte pode rodar.

**Modo 1 — Bootstrap de cluster local (desenvolvimento)**

Sem `ERP_TEST_DATABASE_URL`, o helper encontra `initdb`/`pg_ctl` (env `PG_BINDIR` →
`/usr/lib/postgresql/<v>/bin` → `pg_config --bindir`), cria um cluster **temporário e
descartável** em `/tmp/erp_pg_test_*` (porta livre) e aplica as migrations na ordem do
projeto (`002 → 009 → 011`, `+ 010`, `+ 012`, `+ 013`, `+ 014`). Ao final, `stop()` derruba o
cluster e remove o diretório.

```bash
bash tests/run_all.sh   # usa os binários locais do PostgreSQL automaticamente
```

**Modo 2 — Reuso de banco existente via URL (CI)**

Com `ERP_TEST_DATABASE_URL` definida (URL libpq, ex.:
`postgresql://user:pass@host:5432/db`), **nenhum cluster é criado**: o helper conecta
no banco da URL, **reseta o schema `public`** (`DROP SCHEMA IF EXISTS public CASCADE`
+ `CREATE SCHEMA public`) e aplica as migrations nele. O banco **deve ser dedicado e
descartável** (contrato da env) — todas as classes da suíte compartilham a mesma URL e
as migrations não são idempotentes, então o reset por `start()` torna a suíte
re-executável. Nesse modo `stop()` é **no-op** (o banco não é derrubado).

```bash
ERP_TEST_DATABASE_URL=postgresql://user:pass@host:5432/erp_ci_test bash tests/run_all.sh
```

> 💡 CI sem binários locais do PostgreSQL funciona: basta a URL do banco
> dedicado/descartável. Workflow GitHub Actions de referência em **PLAN_ERP.md §7.5**.

### Rodando uma suíte isolada

```bash
python3 -m unittest tests.test_permissions_integration -v     # integração específica
python3 -m unittest tests.test_ctypes_paycalc -v              # ctypes COBOL específico
```

### CI E2E do ERP (`scripts/run_ci.py`)

O pipeline de CI do módulo é **`scripts/run_ci.py`** — build COBOL → seed → smokes
RFC → reviews de tela via HTTP → checks de render Node → restauração do seed:

```bash
python3 scripts/run_ci.py             # suíte completa
python3 scripts/run_ci.py --no-build  # pula a recompilação do COBOL
python3 scripts/run_ci.py --browser   # adiciona o passo 9 (cenários visuais)
```

O **passo 9 (opcional, `--browser`)** sobe os mesmos cenários usados com
browser-use para conferência visual em navegador real e valida o seed via HTTP
antes de encerrar (com restauração dos dados):

| Cenário | Porta | Seed validado | GET |
|---|---|---|---|
| `cenario_complementar_browser.py` | 8141 | 4 complementares nos estados C/V/F/P (aba Complementar, RFC-013) | `/api/folha/complementares` |
| `cenario_rescisao_browser.py` | 8142 | 2 rescisões — 1 com `ferias_venc_dobro=True` (EM DOBRO) + 1 normal (aba Rescisão, RFC-003) | `/api/folha/rescisoes` |

O render visual dos badges (VENCIDA/EM DOBRO), toasts e gating de botões fica
coberto de forma determinística pelos **checks de render Node** (passo 7, com
DOM stub); o `--browser` garante que o **seed** dos cenários continua consistente
no CI. Para conferência visual manual, rode o cenário diretamente e deixe o
servidor vivo (Ctrl+C restaura os dados). Detalhes do pipeline e do passo 9 em
**`docs-tecnicos/RFC-CHECKLIST-fechamento.md`** (§ "Como rodar o CI (run_ci.py)").

---

*Última atualização: 11/08/2026*
