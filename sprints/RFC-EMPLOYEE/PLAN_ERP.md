# ERP COBOL — Plano de Projeto

> Documento vivo de planejamento do ERP 100% caseiro.
> Backend: **COBOL + Python + PostgreSQL** · Frontend: **HTML + CSS + JS puro**
> Zero dependências externas — tudo escrito por aqui.

---

## 1. Visão Geral

Sistema ERP (Enterprise Resource Planning) construído do zero, sem frameworks,
sem bibliotecas externas e sem CDN. O COBOL é o **motor de regras de negócio**
(chamado via `ctypes`), o Python é a **camada web e de orquestração**, e o
PostgreSQL é o **banco de dados único**.

**Módulo MVP:** Folha de Pagamento.

---

## 2. Stack Tecnológica

| Camada | Tecnologia | Observação |
|---|---|---|
| Frontend | HTML + CSS + JS puro (ES modules) | **Proibido**: Bootstrap, jQuery, React, Vue, qualquer CDN |
| Servidor web | Python stdlib (`http.server.ThreadingHTTPServer`) | Sem Flask, Django ou FastAPI |
| Driver de banco | `psycopg` (única dependência de runtime obrigatória) | Camada de acesso a dados é nossa |
| Geração de PDF | Biblioteca estática Python (ex.: reportlab/fpdf) | Formato de saída de holerites/relatórios (decisão 01/08/2026) |
| Motor de negócio | **GnuCOBOL** (`cobc -m` → `.so`) | Chamado via `ctypes` |
| Banco de dados | PostgreSQL | SQL puro + migrations próprias |
| Build de COBOL | GnuCOBOL + `gcc` | Ferramentas de build, não de runtime |

---

## 3. Decisões Registradas (Regras Permanentes)

1. **COBOL = motor de negócio** via `ctypes` (`.so` carregados uma única vez no
   startup — regra `libcob`: nunca dentro de handler de requisição, risco de `SIGSEGV`).
2. **Frontend 100% vanilla** — nada de Bootstrap, jQuery, React, Vue.js,
   Angular, CDNs ou bibliotecas externas. Design system, grid, componentes,
   ícones, router, validação e máscaras: **tudo escrito por nós**.
3. **Driver PostgreSQL**: `psycopg` como única dependência de runtime
   obrigatória, com camada de acesso a dados própria escrita por nós em cima.
   Biblioteca estática de geração de PDF é permitida para holerites/relatórios
   (decisão 01/08/2026 — ver RFC-015).
4. **Módulo MVP**: Folha de Pagamento.
5. **Começar do zero** — sem código COBOL legado.
6. **Nenhuma dependência externa** além de: PostgreSQL, GnuCOBOL, `gcc`, Python
   stdlib, `psycopg` e biblioteca estática de geração de PDF (decisão
   01/08/2026 — ver RFC-015). Nada de npm, pip install de frameworks, CDN, etc.

---

## 4. Arquitetura

```
┌──────────────────────────────────────────────────────┐
│  FRONTEND  HTML + CSS + JS puro (fetch API, SPA)     │
│  • design system próprio (CSS variables)             │
│  • hash router caseiro · ES modules · Web Components │
│  • ícones SVG próprios · máscaras/validação caseiras │
└───────────────────────┬──────────────────────────────┘
                        │ HTTP/JSON
┌───────────────────────▼──────────────────────────────┐
│  WEB LAYER  Python stdlib (ThreadingHTTPServer)      │
│  • rotas · sessões (cookie assinado c/ hmac)          │
│  • validação de entrada · orquestração · persistência │
└───────┬───────────────────────────────┬──────────────┘
        │ ctypes (startup, 1x)          │ psycopg + camada nossa
┌───────▼───────────────┐      ┌────────▼───────────────┐
│  COBOL (.so)          │      │  PostgreSQL            │
│  Núcleo financeiro:   │      │  employees, payroll,   │
│  INSS, IRRF, horas,   │      │  tax_tables, events…   │
│  férias, rescisão     │      │  (SQL puro + migrations│
└───────────────────────┘      │   próprias)            │
                              └─────────────────────────┘
```

### 4.1 Regra crítica do `ctypes` + COBOL

- O runtime `libcob` deve ser inicializado **uma única vez** no startup do app
  (`libcob.cob_init(0, None)`).
- Os `.so` ficam carregados em memória durante toda a vida do processo.
- Nunca carregar/descarregar `.so` por requisição (corrupção de memória).
- Mapear `PIC` clauses (especialmente `COMP-3`/decimais) para tipos `ctypes`
  com precisão — usar structs intermediárias para evitar perda de precisão.
- Processamento pesado (folha com muitos funcionários) → **subprocess isolado**
  (decisão pendente — recomendação: híbrido).

### 4.2 Interface COBOL (exemplo)

```cobol
PROGRAM-ID. PAYCALC.
DATA DIVISION.
LINKAGE SECTION.
  01 LK-SALARIO    PIC 9(8)V99.
  01 LK-DEPEND     PIC 9(2).
  01 LK-INSS       PIC 9(8)V99.
  01 LK-IRRF       PIC 9(8)V99.
PROCEDURE DIVISION USING LK-SALARIO LK-DEPEND LK-INSS LK-IRRF.
    *> regras fiscais do Brasil aqui
    GOBACK.
```

```bash
cobc -m -o payroll.so payroll.cbl
```

```python
from ctypes import CDLL, c_double, c_int, byref
libcob = CDLL("libcob.so.4")
libcob.cob_init(0, None)          # UMA vez, no startup
pay = CDLL("./payroll.so")
# ... chamadas com structs mapeadas
```

---

## 5. Frontend 100% Caseiro

| Componente | O que fazemos | Substitui |
|---|---|---|
| Design system | CSS puro com variáveis (cores, espaçamento, tipografia); tema claro/escuro | Bootstrap |
| Grid/layout | Sistema de grid e componentes próprios (tabelas, cards, modais, tabs, toasts) | Bootstrap UI |
| Roteamento | Hash router feito à mão | Vue Router / React Router |
| Componentização | ES modules nativos + Web Components (custom elements) | React / Vue |
| Ícones | SVGs inline próprios (lib interna de ícones) | FontAwesome / Material |
| Requisições | `fetch` nativo + camada de API nossa | Axios |
| Estado/reatividade | Micro-framework reativo (~100 linhas, Proxy + observables) | Vue / React |
| Formulários | Validação própria + máscaras caseiras (CPF/CNPJ/data/moeda) | jQuery validate, inputmask |
| Datas/números | `Intl` nativo (pt-BR) + helpers nossos | moment.js, dayjs |
| Zero CDN | Todos os assets servidos pelo nosso servidor | qualquer CDN |

---

## 6. Estrutura do Projeto

```
erp_cobol/
├── PLAN_ERP.md        # este documento
├── web/               # servidor HTTP, rotas, sessão, estáticos
├── core/              # lógica de aplicação Python (orquestração)
├── cobol/             # fontes .cbl + .so compilados (PAYCALC, TAXCALC…)
├── db/                # SQL puro, migrations (002…018), seed de tabelas fiscais
├── RFC-COMISSION/     # RFCs do módulo de comissões (001–008)
├── static/            # HTML / CSS / JS (100% nosso)
├── tests/             # unittest (COBOL ctypes + integração Postgres) + runner
└── README.md
```

---

## 7. Testes

### 7.1 Suíte completa — um comando só

```bash
bash tests/run_all.sh            # build incremental + suíte completa (COBOL + integração)
bash tests/run_all.sh --rebuild  # força a recompilação dos .so COBOL
```

O runner (`tests/run_all.sh`, `set -euo pipefail`) faz:

1. **Build incremental do COBOL** — recompila `taxcalc.so`, `calcevent.so` e `paycalc.so`
   (`cobc -m`; `PAYCALC` chama os outros via `COB_LIBRARY_PATH`) apenas quando um `.so`
   falta ou a fonte `.cbl` é mais nova. `--rebuild` força a recompilação. Sem `cobc` e com
   build pendente → falha com a instrução de compilação manual.
2. **`unittest discover`** — `python3 -m unittest discover -s tests -p "test_*.py" -v`
   descobre os 9 arquivos de teste (ignora o helper `pg_bootstrap.py`). O exit code do
   unittest propaga pelo `set -e` — adequado para CI.

### 7.2 As duas famílias de teste

| Família | Arquivos | Valida |
|---|---|---|
| **COBOL via ctypes** (requer os `.so`) | `test_ctypes_taxcalc.py` · `test_ctypes_calcevent.py` · `test_ctypes_paycalc.py` | INSS/IRRF progressivos (RFC-005), eventos da folha (RFC-004), resultado completo com proventos, descontos, bases, INSS, IRRF e líquido (RFC-007) |
| **Integração Postgres** (cluster temporário ou URL de CI) | `test_stubs_integration.py` · `test_permissions_integration.py` · `test_state_machine_integration.py` · `test_runs_lines_integration.py` · `test_tax_tables_integration.py` · `test_commission_rules_integration.py` · `test_payroll_accounting_integration.py` · `test_commission_accounting_integration.py` · `test_commission_detail_accounting_integration.py` | Documento do holerite com snapshot/imutabilidade (014, RFC-007), matriz de permissões ação×papel §3.1 (011), máquina de estados do RFC-006 (010), execução e resultado da folha (012), tabelas fiscais por competência (013), módulo de comissões do PDV com precedência e apuração (016/017), contabilização da folha (RFC-Payroll 001–002), contabilização da comissão — evento 7 (RFC-Payroll/003), detalhamento por venda de origem no lançamento (RFC-Payroll/004) |

### 7.3 Infraestrutura de integração — `tests/pg_bootstrap.py`

Helper compartilhado que provê o **backend PostgreSQL** dos testes de integração em **dois
modos** — bootstrap de um cluster local efêmero (desenvolvimento) ou reuso de um banco
existente via URL (CI). `test_backend_available()` decide se a suíte pode rodar.

**Modo padrão — bootstrap de cluster local** (sem `ERP_TEST_DATABASE_URL`):

- `find_pgbindir()` — localiza `initdb`/`pg_ctl`: env `PG_BINDIR` →
  `/usr/lib/postgresql/<v>/bin` → `pg_config --bindir`.
- `free_port()` — porta TCP livre (o cluster temporário não conflita com nada).
- `TempCluster(db_name, migrations)` — `initdb -A trust --no-locale` + `pg_ctl` em
  diretório efêmero (`/tmp/erp_pg_test_*`), cria o banco e aplica as migrations **na ordem
  do projeto**: `002 → 009 → 011` (permissões), `+ 010` (máquina de estados),
  `+ 012` (runs/lines), `+ 013` (tabelas fiscais), `+ 016/017` (comissões —
  quando o teste da família as declara em `MIGRATIONS`).
- `connect()` — nova conexão psycopg2 com `client_encoding="UTF8"` (as migrations contêm
  `—`, `§`, `✅`, `→`) e `autocommit` definido **pós-conexão** (não é opção de DSN do
  psycopg2).
- `stop()` — derruba o cluster e remove o diretório; **idempotente** (seguro repetir).

**Modo CI — reuso de banco existente** (`ERP_TEST_DATABASE_URL`):

Quando a env var aponta para uma URL libpq (ex.: `postgresql://user:pass@host:5432/db`),
**nenhum cluster é criado**:

- `start()` conecta **no banco da URL**, **reseta o schema `public`**
  (`DROP SCHEMA IF EXISTS public CASCADE` + `CREATE SCHEMA public`) e aplica as migrations
  nele. Como **todas as classes da suíte compartilham a MESMA URL** (`db_name` é ignorado
  nesse modo) e as migrations **não são idempotentes**, o reset por `start()` torna cada
  classe independente e a suíte **re-executável** com uma única URL — o banco DEVE ser
  dedicado e descartável (o contrato da env); se a URL estiver errada ou sem privilégio de
  CREATE, falha ruidosa com `RuntimeError` e dica de diagnóstico.
- `stop()` vira **no-op** — o banco compartilhado do CI não é derrubado nem removido.
- `test_backend_available()` — `True` se há backend: URL definida **OU** binários locais
  (CI sem binários do PostgreSQL funciona). É o que os testes usam no **skip gracioso**.

```bash
# CI: sem binários locais do PostgreSQL — só a URL do banco dedicado/descartável
ERP_TEST_DATABASE_URL=postgresql://user:pass@host:5432/erp_ci_test bash tests/run_all.sh
```

Regras de uso dos testes de integração (padrão do projeto):

- `addClassCleanup(cluster.stop)` registrado **antes** de `cluster.start()` — se o
  bootstrap falhar, o cluster não vaza (no modo externo o `stop()` é no-op por contrato).
- Sem `psycopg2` nem backend (nem URL, nem binários) → **skip gracioso** via
  `test_backend_available()` (nunca falha por falta de ambiente).
- Suíte isolada: `python3 -m unittest tests.test_permissions_integration -v` (idem para
  `test_state_machine_integration`, `test_runs_lines_integration`,
  `test_tax_tables_integration` e os `test_ctypes_*`).

### 7.4 Por que o `discover` não usa `-t .`

O `discover` do Python 3.12 exige `__init__.py` no diretório de busca quando o top-level
difere do start dir — e `tests/` é namespace package (sem `__init__.py`), o que estoura
"Start directory is not importable". Com `-s tests` sozinho, o diretório entra no
`sys.path`, os módulos importam como `test_*` e os testes de integração caem no fallback
`from pg_bootstrap import ...`.

### 7.5 CI — GitHub Actions com `ERP_TEST_DATABASE_URL`

O runner foi desenhado para CI: o exit code do unittest propaga pelo `set -e`
(7.1), os testes de integração usam um banco externo via URL sem exigir
binários locais do PostgreSQL (7.3) e a suíte é **re-executável** contra a
mesma URL (o reset de schema do `start()` torna cada classe independente).

Workflow de referência (`.github/workflows/test.yml`):

```yaml
name: test

on:
  push:
  pull_request:
  workflow_dispatch:   # execução manual (Actions tab)

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      # Banco DEDICADO e descartável do job — contrato da ERP_TEST_DATABASE_URL
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: erp_ci_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U postgres -d erp_ci_test"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"   # comportamento do discover documentado em 7.4
      - name: Instala GnuCOBOL (build dos .so via cobc)
        run: sudo apt-get update && sudo apt-get install -y gnucobol
      - name: Instala psycopg2
        run: python -m pip install psycopg2-binary
      - name: Roda a suíte completa contra o banco do serviço
        env:
          # .so são gitignored: o build incremental do run_all.sh compila
          # taxcalc/calcevent/paycalc automaticamente na 1ª execução
          ERP_TEST_DATABASE_URL: postgresql://postgres:postgres@localhost:5432/erp_ci_test
        run: bash tests/run_all.sh
```

Pontos de atenção:

- **`cobc` é obrigatório no CI** — os `.so` estão no `.gitignore`; como o
  checkout não os traz, o build incremental do `run_all.sh` dispara sozinho na
  1ª execução (equivalente a `--rebuild`). Sem `cobc`, o runner falha com a
  instrução de compilação manual. Pacote apt: `gnucobol` (em distros antigas,
  `gnucobol4`/`open-cobol`).
- **A URL dispensa binários locais do PG no runner** — o service container
  entrega apenas o servidor; o modo CI do `pg_bootstrap` (7.3) nem tenta
  `initdb`/`pg_ctl` e o `stop()` é no-op.
- **Banco dedicado/descartável por job** — a suíte reseta o schema `public` a
  cada `start()`; o banco do serviço é criado e destruído junto com o job, então
  não há risco para dados reais.
- **Health check antes do runner** — `pg_isready` evita que as migrations
  corram antes de o servidor aceitar conexões (o modo externo não tem o poll do
  bootstrap).

---

## 8. Módulo MVP — Folha de Pagamento

### 8.1 Cadastros
- Funcionários (salário, admissão, dependentes, cargo, departamento)
- Departamentos e cargos
- Eventos de proventos e descontos (salário base, horas extras, adicional,
  INSS, IRRF, faltas, vale-transporte, etc.)

### 8.2 Cálculo
- **Python orquestra** → **COBOL calcula** (INSS progressivo, IRRF por faixas
  com dedução por dependente)
- Tabelas oficiais versionadas por competência (`tax_tables`)

### 8.3 Saídas
- Holerite em **HTML imprimível** (CSS print) **ou PDF** — PDF gerado por
  biblioteca estática própria (decisão 01/08/2026, ver RFC-015); zero serviço
  externo e zero CDN
- Relatórios: folha consolidada por departamento, total de encargos

### 8.4 Modelo de dados inicial (PostgreSQL)
- `employees` · `departments` · `positions`
- `payroll_periods` (competências)
- `payroll_events` (proventos/descontos)
- `payroll_runs` (processamento da folha) · `payroll_lines` (resultado por funcionário)
- `payroll_stubs` (holerite — documento por funcionário/execução, RFC-007)
- `payroll_entries` (detalhamento por evento do holerite, RFC-007 §2.2/§2.3)
- `tax_tables` (INSS/IRRF por competência)
- `product_categories` · `products` · `commission_rules` (módulo de comissões do PDV,
  migration 016 — RFC-COMISSION/RFC-003; regras funcionário × produto/categoria × taxa
  com precedência produto → categoria → taxa padrão)
- `pos_sales` · `pos_sale_items` · `commission_details` · `commission_settlements`
  (apuração das vendas do PDV, detalhe da comissão por venda e congelamento do apurado,
  migration 017 — RFC-COMISSION/RFC-005; estorno por status, detalhe imutável)
- `commission_global_rules` (taxa padrão GLOBAL da empresa — fallback final da precedência,
  migration 018 — RFC-COMISSION/RFC-008; uma única regra ATIVA por empresa)

---

## 9. Fases de Implementação

| Fase | Descrição | Entregável |
|---|---|---|
| **0 — Ambiente** | GnuCOBOL + PostgreSQL + esqueleto + hello world ctypes COBOL↔Python | Repo rodando, `.so` compilado e chamado pelo Python |
| **1 — Web** | Servidor Python, rotas, sessão, estáticos servidos | Navegador abre o app, login básico |
| **2 — Cadastros** | CRUD funcionários/departamentos/cargos no Postgres | Telas funcionais com persistência |
| **3 — Núcleo COBOL** | Cálculo INSS/IRRF puro em `.so`, testável isoladamente | `payroll.so` com testes |
| **4 — Folha** | Processamento mensal completo + holerite HTML | Folha de um período real calculada |
| **5 — Relatórios** | Consolidações por departamento + fechamento | Relatórios exportáveis (HTML/print) |
| **6 — Comissões** | Módulo de comissões do PDV: categorias/produtos/regras (db/016) + apuração das vendas (db/017) + taxa padrão GLOBAL (db/018) | Comissão apurada alimentando o evento 7 da folha (RFC-COMISSION 001–008) |

---

## 10. Riscos e Mitigação

| Risco | Mitigação |
|---|---|
| Crash de COBOL via ctypes derruba o worker | Worker pool; batch pesado em subprocess isolado |
| Perda de precisão em decimais (COMP-3) | Structs intermediárias + testes de arredondamento |
| SEGFAULT por recarregar `.so` | Regra `libcob` no startup (ver 4.1) |
| Escopo da folha crescer demais | MVP enxuto (INSS/IRRF/horas), ampliar depois |
| Vários módulos no mesmo processo | Separação clara `web/core/cobol/db` |

---

## 11. Decisões Pendentes

1. **Processamento pesado da folha** (recomendação: híbrido ctypes + subprocess)
   — aguardando confirmação.
2. **SPA vs. formulários clássicos multi-página** — as seções 4 e 5 assumem
   **SPA** (hash router, micro-framework reativo, Web Components, fetch API)
   como **recomendação**, mas essa escolha ainda não foi confirmada. Alternativa:
   formulários clássicos multi-página (mais simples, menos JS caseiro).

---

*Última atualização: 05/08/2026*
