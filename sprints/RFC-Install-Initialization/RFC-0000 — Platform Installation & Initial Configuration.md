# RFC-0000 — Platform Installation & Initial Configuration

| Field    | Value                                         |
| -------- | --------------------------------------------- |
| RFC      | RFC-0000                                      |
| Title    | Platform Installation & Initial Configuration |
| Status   | Done (MVP)                                    |
| Version  | 1.0                                           |
| Category | Platform Foundation                           |
| Priority | Critical                                      |
| Author   | Business Platform Team                        |

---

## Platform Philosophy

> **Simple is always better than complex.**
> Simples é sempre melhor do que complexo.

Design systems that are easy to understand, easy to maintain, easy to extend, and easy to use.
Avoid unnecessary abstractions. Prefer explicit behavior over hidden magic.
Every feature should solve a real business problem.
Performance and maintainability always come first.

---

# 1. Purpose

This document defines the complete functional process for installing, initializing and configuring the Business Platform.

This RFC is the foundation of the entire platform.

Every Business Instance shall be created following the rules defined in this document.

All future RFCs assume that the platform has already been initialized according to RFC-0000.

---

# 2. Scope

This RFC defines:

* Platform installation
* Business Instance creation
* Platform initialization
* Administrator creation
* Localization
* First Login
* Organization creation
* Company creation
* Branch creation
* Warehouse creation
* User initialization
* Module installation
* Business Setup
* Platform validation
* Production activation

---

# 3. Guiding Principles

The installation experience shall always follow these principles.

## 3.1 Business First

The platform speaks the language of business.

Technical implementation details are hidden from the administrator.

---

## 3.2 Wizard Driven

Every initial configuration must be guided.

The administrator should never be presented with an empty system.

---

## 3.3 Progressive Configuration

Only the information required for the current step shall be requested.

---

## 3.4 Modular

Only installed modules require configuration.

---

## 3.5 Recoverable

The installation wizard may be interrupted and resumed at any time.

---

## 3.6 Simple

Every decision must respect the platform principle:

> **Simple is always better than complex.**

---

# 4. Installation Lifecycle

The complete installation process follows the sequence below.

```text
Platform Installation

↓

Business Instance Creation

↓

Platform Initialization

↓

Administrator Creation

↓

Localization

↓

First Login

↓

Organization Setup

↓

Company Setup

↓

Business Structure

↓

Module Installation

↓

Business Setup

↓

Platform Validation

↓

Go Live
```

---

# 5. Platform Installation

The platform software is installed on the operating system.

At this stage no business information exists.

Installed components include:

* COBOL Runtime
* Python Services
* BusinessUI
* Configuration Framework
* Module Registry
* Analytics Services
* Document Storage
* Logging Services

The platform is now capable of creating Business Instances.

---

# 6. Business Instance Creation

The first execution shall always verify whether a Business Instance already exists.

If no Business Instance exists, the Initial Configuration Wizard shall be started automatically.

The administrator shall provide:

* Business Instance Name
* Optional Description

Example:

Business Instance

Business Name

Example Retail

Instance Identifier

example_retail

Description

Production Environment

Business Instance names shall be unique.

---

# 7. Platform Administrator

The platform requires one initial administrator.

Required information:

* Full Name
* Login Email
* Password
* Password Confirmation

The first administrator automatically receives Platform Administrator privileges.

---

# 8. Localization

Localization defines the default behavior of the platform.

Required information:

* Country
* Language
* Time Zone
* Currency

Example

Country

Brazil

Language

Português (Brasil)

Timezone

America/Sao_Paulo

Currency

BRL

Localization may be modified later by authorized administrators.

---

# 9. Platform Initialization

After confirmation, the platform initializes the Business Instance.

Initialization includes:

* Create transactional repository
* Create platform configuration
* Create administrator account
* Initialize services
* Register localization
* Create analytics repository
* Initialize document storage
* Register default parameters

The administrator shall be presented with installation progress.

Example

Initializing Platform...

✓ Repository

✓ Configuration

✓ Administrator

✓ Localization

✓ Services

✓ Analytics

✓ Documents

Platform Ready

---

# 10. First Login

After initialization, the administrator is redirected to the authentication screen.

Only the previously created administrator may authenticate.

Upon successful authentication, the Business Setup Wizard starts automatically.

---

# 11. Business Setup

At this point the platform exists.

Business information does not.

The administrator is guided through business configuration.

Business Setup includes:

* Organization
* Company
* Branch
* Warehouse
* Users
* Modules

Business Setup may be paused and resumed.

---

# 12. Organization

The first Organization represents the legal owner of the Business Instance.

Required information:

* Organization Name
* Legal Name
* Tax Identifier
* Primary Address

One Business Instance must contain at least one Organization.

---

# 13. Company

An Organization may contain one or more Companies.

The first Company is mandatory.

Typical information:

* Company Name
* Legal Name
* Tax Registration
* Address
* Fiscal Information

---

# 14. Branches

Each Company may define one or more Branches.

Branches inherit Company configuration unless explicitly overridden.

---

# 15. Warehouses

Warehouses are optional.

The administrator may:

* create immediately;
* postpone creation.

Modules requiring Warehouses shall notify the administrator before activation.

---

# 16. Users

The platform recommends creating operational users before production.

Typical roles include:

* Administrator
* Supervisor
* Manager
* Operator

Additional roles are defined by installed modules.

---

# 17. Module Installation

The Module Manager presents all available business modules.

Examples:

* Party
* Sales
* Purchase
* Inventory
* POS
* Delivery
* Finance
* Manufacturing
* HR
* CRM

The administrator selects desired modules.

Dependencies are resolved automatically.

---

# 18. Module Setup

Each installed module owns its own Setup Wizard.

Examples:

Sales

* Order Types
* Price Lists

Inventory

* Warehouses
* Locations

Delivery

* Delivery Zones
* Drivers

Finance

* Chart of Accounts
* Journals

Each module is responsible for its own business configuration.

---

# 19. Platform Validation

Before entering production, the platform validates configuration.

Example checklist:

✓ Business Instance

✓ Administrator

✓ Organization

✓ Company

✓ Localization

✓ Users

✓ Modules

⚠ Warehouse Missing

⚠ Delivery Zone Missing

Configuration issues shall include direct navigation to the required setup.

---

# 20. Go Live

The Business Platform enters Production Mode when all mandatory validations are satisfied.

The Dashboard becomes available.

Normal business operations may begin.

---

# 21. Business Instance Lifecycle

Every Business Instance follows the lifecycle below.

```text
Created

↓

Initializing

↓

Configured

↓

Operational

↓

Maintenance

↓

Backup

↓

Restore

↓

Archived
```

---

# 22. Business Rules

Rule 1

A Business Instance shall exist before any business operation.

Rule 2

Business Setup shall always be wizard-driven.

Rule 3

No module may bypass Platform Initialization.

Rule 4

Business modules are independent.

Rule 5

Every installed module owns its own Setup Wizard.

Rule 6

Platform validation is mandatory before Production Mode.

---

# 23. Future Extensions

This RFC shall be expanded as the platform evolves.

Future revisions may include:

* Cloud Deployment
* Multi-Instance Management
* High Availability
* Cluster Installation
* Distributed Services
* Automated Provisioning
* Business Templates
* Marketplace Integration

---

# 25. Implementation Notes (MVP)

Implemented as `platform_setup.py` + endpoints `/api/platform/setup*` + `pages/setup-wizard.html`, backed by `data/platform_setup.json`.

Open gaps against this RFC:

* §18 / Rule 5 — per-module Setup Wizards: **implemented (MVP)** — module setup registry in `app_registry.py` (`SETUP_DESCRIPTORS`, `data/module_setup.json`, `/api/apps/setup` + `/api/apps/setup/done`), badge "Configurar" in the main menu, and the Business Setup "modules" step chains the installed modules (gated on required setups).
* §9 — "Register default parameters": **implemented** — `data/parametros.json` via `platform_setup.register_default_parameters()` + `/api/system/parameters`.
* §9 — Logging Services: **implemented** — `data/logs/system_log.json` (append-only, capped) via `platform_setup.log_event()` + `/api/system/log`.
* §17 — automatic module dependency resolution: **implemented** — `depends_on` per app (`app_registry`), `resolve_dependencies()` transitive closure on package/custom/`set_app`, surfaced as `missing_dependencies` in the catalog.
* §21 — Lifecycle beyond `operational` (Maintenance, Backup, Restore, Archived): **implemented (MVP)** — `platform_setup.py` (flags `maintenance`/`archived` no estado; `enter/exit_maintenance`, `archive/unarchive_instance`, `create_backup`/`restore_backup` com índice `data/backups/_index.json`, `list_backups`, `lifecycle_guard`) + endpoints `/api/system/maintenance`, `/api/system/archive`, `/api/system/backup` (POST) e `/api/system/lifecycle`, `/api/system/backup` (GET); `lifecycle_guard` em `server.py do_POST/do_PUT` (403/503 em `maintenance`/`archived`, whitelist de leitura `GET /api/system/*`, `/api/auth/*`, `/api/platform/setup`); `status()` expõe `lifecycle`. `enter_maintenance` só em produção (`go_live`).
  * **Pendente (retomar)**: lógica testada por unidade em `/tmp` (10 cenários OK), mas as rotas HTTP (`do_GET`/`do_POST`) do §21 **não** foram exercitadas end-to-end com o servidor real subido. Fazer smoke test HTTP dos endpoints `/api/system/maintenance|archive|backup|lifecycle` antes de considerar fechado.
* **Módulo Vendas (B2B)** — `pages/vendas.html` + `POST /api/vendas/b2b`: **CRUD implementado e smoke-testado via HTTP real** — `create` (id/numero sequenciais PV/S), `update`, `status`, `aprovar`, `faturar` (gera `dados/faturas_venda.json` `FV` + marca pedido `faturado` + baixa estoque via `inventory_apply_sale` quando há `estabelecimento_id`) e `delete`; `GET /api/vendas/b2b` e `GET /api/vendas/b2b/faturas`. Formulário com header e linhas editáveis (datalist de produtos via `/api/admin/produtos`). Ciclo: rascunho → pendente → aprovado → faturado (cancelado/bloqueado). Smoke: servidor real em `/tmp`, login admin, ciclo completo OK.
  * **Listas de preço no pedido (MVP)**: `GET /api/vendas/b2b/catalog` (autenticado, sem exigir admin) entrega listas ativas (`id`/`name`/`items`) + produtos (`id`/`nome`/`preco` base). No formulário, `lista_precos` virou `<select>` (persiste `lista_precos_id` + nome); ao escolher produto na linha ou clicar "Aplicar preços da lista", o preço é resolvido no cliente (item da lista → senão preço base). Smoke: catálogo OK autenticado, bloqueio sem token, persistência de `lista_precos_id` OK.
  * **Clientes B2B no pedido (MVP)**: `GET /api/vendas/b2b/clientes` (autenticado, sem exigir admin) lista clientes ativos de `data/contatos.json` (`tipo=cliente`) com razão social, CNPJ, IE, cidade/UF e endereço de cobrança composto. No formulário, `razao_social` tem autocomplete (`datalist`); ao escolher, preenche CNPJ/IE/cidade/UF/endereço e grava `cliente_id`/`cliente_nome`. Smoke: 3 clientes retornados, bloqueio sem token.
  * **Relatório de Vendas em tela (MVP)**: view "Análise de Vendas" com formulário de filtros (período de/até, tipo, status, vendedor, UF) — sem impressão em papel. Resultado em tela: KPIs (receita, nº documentos, ticket médio, impostos) + quebras por status, vendedor, UF e top 10 produtos. Cálculo client-side sobre `pedidos_b2b.json`; lógica validada em node com dados reais.
  * **Regras de workflow/validação (encerramento do módulo)**: mapa de transições `_B2B_FLOW` em `server.py` — rascunho → pendente → aprovado → faturado; cancelado/bloqueado terminais (bloqueado retorna a pendente; faturado/cancelado não saem). Validações: `update` bloqueado para faturado/cancelado/bloqueado ("edição bloqueada"); `delete` bloqueado para faturado; `aprovar` exige rascunho/pendente + itens; `faturar` exige aprovado; pedido B2B (não-cotação) exige CNPJ de 14 dígitos para confirmar/aprovar (`_b2b_cnpj_valido`). Frontend: modo somente-leitura quando faturado/cancelado/bloqueado (inputs `disabled`, sem botões Salvar/Confirmar/Aprovar/Fatura/Cancelar), desbloqueio não salva antes (evita "edição bloqueada"), botão Excluir (com confirmação; oculto em faturado). Testes: 19 cenários de unidade + smoke HTTP real (19 ok) cobrindo transições válidas/inválidas, bloqueio de edição/exclusão e exigência de CNPJ.
  * **Visualizações do módulo (Kanban, Calendário, Pivot, Gráfico)**: novo grupo de menu "Visualizações" em `pages/vendas.html` com (a) **Kanban** — colunas por status (rascunho/pendente/aprovado/faturado/bloqueado/cancelado), cartões clicáveis (abrem o Form) e drag & drop que altera status via `POST /api/vendas/b2b` (cliente valida a transição com o mesmo mapa `FLOW` do backend e destaca apenas colunas válidas; servidor permanece como autoridade). (b) **Calendário** — grid mensal (semana inicia segunda) agrupando pedidos/cotações por data de emissão, chips por status com navegação mês anterior/próximo/hoje e filtro por tipo. (c) **Pivot** — tabela dinâmica client-side: linhas (vendedor/cliente/UF/tipo) × colunas (status/mês/tipo) × valor (total R$/quantidade de itens/nº docs) com totais de linha e coluna. (d) **Gráfico** — barras de "Receita por status" e "Receita por mês" adicionadas à view Análise de Vendas (junto aos filtros e tabelas já existentes). Re-render automático da view ativa no `refreshFromServer`. Validação: `node --check` + 20 asserções em harness node com DOM stub (colunas/42 células do mês/agregação pivot/totais/mapeamento FLOW).

---

# 24. Final Statement

RFC-0000 establishes the functional foundation of the Business Platform.

Every Business Instance shall begin its lifecycle according to this document.

Every future RFC assumes compliance with RFC-0000.

This document is the constitutional reference for platform installation and initial configuration.

> **Simple is always better than complex.**
