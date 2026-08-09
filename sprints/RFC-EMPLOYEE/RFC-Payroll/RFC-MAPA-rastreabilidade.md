# Mapa de Rastreabilidade — Série RFC-Payroll (Módulo de Folha de Pagamento)

> Liga cada **conceito do módulo de folha de pagamento** (série RFC-Payroll) ao
> documento correspondente da série e aos **RFCs do projeto central** (`rfcs/`)
> e às **migrations SQL** (`db/`) que os materializam. Complementa o
> `docs-tecnicos/RFC-MAPA-encadeamento.md` (que cobre apenas os RFCs 001–016
> do projeto central) e o mapa da série irmã
> (`RFC-COMISSION/RFC-MAPA-rastreabilidade.md`).
> Fontes: cabeçalhos e seções de `RFC-Payroll/`, `rfcs/`, `db/` e `PLAN_ERP.md`.

---

## 1. A série RFC-Payroll em uma linha

```
RFC-Payroll/001 (contabilização da folha — modelo de dados e funcionalidades)
        │  estende hr.salary.rule/hr.payslip; consome o apurado de comissões pelo evento 7
        ▼
RFC-Payroll/002 (fluxos de contabilização — geração do lançamento por regra/categoria e estorno)
        │  usa a mecânica do módulo `account` (account.move/account.move.line, reversed_entry_id)
        ▼
RFC-Payroll/003 (contabilização da comissão — evento 7 como regra mapeada)
        │  reutiliza a mecânica de 001/002 — sem models/migrations próprios
        ▼
RFC-Payroll/004 (detalhamento contábil por venda de origem no lançamento da comissão)
        │  camada analítica de ligação (único model próprio) — razão permanece consolidado por regra
        ▼
   lançamento contábil no módulo `account` da plataforma — SEM migration própria
```

| RFC | Tema | Depende de | Impacta |
|---|---|---|---|
| **RFC-Payroll/001** | Contabilização automática da folha: modelo de dados e funcionalidades — contas nas regras salariais, diário/contas padrão no contracheque, lançamento automático e estorno | RFC-006 (projeto — processamento), RFC-007 (projeto — holerite); módulos `eh_hr_payroll` + `account` (plataforma) | RFC-007 (projeto — vínculos do lançamento no holerite); RFC-COMISSION/001 (comissão contabilizada como evento 7); RFC-Payroll/002 (fluxos); RFC-Payroll/003 (comissão — evento 7); RFC-Payroll/004 (detalhamento por venda de origem); RFC-Payroll/005+ (evoluções: centro de custo, rateio) |
| **RFC-Payroll/002** | Fluxos de contabilização: geração do lançamento (movimento por regra por categoria) e algoritmo de estorno no cancelamento | RFC-Payroll/001; RFC-006, 007 (projeto); módulos `eh_hr_payroll` + `account` (plataforma) | RFC-007 (projeto — vínculos do lançamento/estorno no holerite); RFC-COMISSION/001 (comissão contabilizada como evento 7); RFC-Payroll/003 (comissão — evento 7); RFC-Payroll/004 (detalhamento por venda de origem); RFC-Payroll/005+ (evoluções) |
| **RFC-Payroll/003** | Contabilização automática da comissão (evento 7): regra de comissão mapeada com par de contas | RFC-Payroll/001, 002; RFC-COMISSION/001 (política), RFC-COMISSION/005 (apuração); RFC-004, 006 (projeto); módulos `eh_hr_payroll` + `account` (plataforma) | RFC-007 (projeto — holerite), RFC-015 (projeto — relatórios); RFC-COMISSION/001 (comissão contabilizada); RFC-Payroll/004 (detalhamento por venda de origem); RFC-Payroll/005+ (evoluções) |
| **RFC-Payroll/004** | Detalhamento contábil por venda de origem no lançamento da comissão (evento 7): camada analítica de ligação entre a linha do razão e a venda de origem | RFC-Payroll/001, 002, 003; RFC-COMISSION/005 (detalhe analítico); RFC-015 (projeto — relatório); módulos `eh_hr_payroll` + `account` (plataforma) | RFC-015 (projeto — relatório integrado ao lançamento); RFC-COMISSION/005 (detalhe consumido pelo lançamento); RFC-Payroll/005+ (evoluções) |

---

## 2. Tabela de Rastreabilidade por Conceito

### 2.1 Conceitos de negócio

| Conceito | RFC-Payroll | RFC do projeto | Migration |
|---|---|---|---|
| Regra salarial com **par de contas** (`debit_account_id`/`credit_account_id`) | 001 §2, §3.1, §4.1 | RFC-004 (eventos/proventos/descontos — catálogo de regras) | db/010 (seed `payroll_events`) — contas configuradas na plataforma |
| **Lançamento por categoria** (cada regra com linha equilibrada) | 001 §2, §3.1, §4.3, §6 | RFC-004 (categorias de eventos) | — (módulo `account` — `account.move.line`) |
| **Par padrão (fallback)** despesas com salários / salários a pagar | 001 §2, §3.2, §4.2, §5.1 | RFC-007 (holerite — proventos por evento) | db/014 (`payroll_stubs`) — par configurado na plataforma |
| **Lançamento contábil equilibrado** (débito = crédito) | 001 §2, §3.3, §4.3 | — | — (módulo `account` da plataforma — `account.move` tipo *entry*) |
| **Estorno** vinculado ao contracheque e associado ao original | 001 §2, §3.4, §4.3, §5.3 | — | — (módulo `account` — `reversed_entry_id`) |
| **Vínculos somente leitura** do lançamento e do estorno no contracheque | 001 §3.2, §4.2 | RFC-007 (holerite — exibição) | — |
| **Um lançamento por contracheque** (idempotência — sem relançamento) | 001 §8 decisão 5 | — (regra do próprio módulo) | — |
| Campos contábeis em `hr.payslip` (`journal_id`, `move_id`, `move_reversal_id`) | 001 §4.2 | RFC-007 (holerite) | db/014 (`payroll_stubs`) · db/015 (`payroll_entries`) |

### 2.2 Fluxos e integração com o núcleo da folha

| Conceito | RFC-Payroll | RFC do projeto | Migration |
|---|---|---|---|
| **Geração do lançamento** (movimento por regra por categoria) | 002 §3 | RFC-006 (processamento — confirmação) · RFC-007 (holerite) | db/012 (`payroll_runs`/`payroll_lines`) · db/014 (`payroll_stubs`) · db/015 (`payroll_entries`) |
| **Estorno no cancelamento** (reversão do lançamento efetuado / cancelamento do rascunho) | 002 §4 | RFC-006 (estados do processamento) | — (mecânica `account` — `reversed_entry_id`) |
| Confirmação do contracheque → **lançamento automático** | 001 §3.3, §4.2, §5.1 · 002 §3.3 | RFC-006 (processamento — confirmação) · RFC-007 (holerite) | db/012 (`payroll_runs`/`payroll_lines`) · db/014 (`payroll_stubs`) · db/015 (`payroll_entries`) |
| Botão **"Lançar no diário"** (retrofit pós-confirmação) | 001 §3.3, §4.2, §5.2 | RFC-006 (processamento) · RFC-007 (holerite) | db/012 · db/014 (consistência do lançamento) |
| Cancelamento do contracheque → **estorno** | 001 §3.4, §4.3, §5.3 | RFC-006 (estados do processamento) | db/012 (`status`) |
| Impostos a recolher (INSS/IRRF) no lançamento | 001 §6 (exemplo) | RFC-005 (tabelas fiscais — INSS/IRRF) | db/013 (`tax_tables`) |

### 2.3 Integração com a série irmã (comissões)

| Conceito | RFC-Payroll | RFC do projeto / série | Migration |
|---|---|---|---|
| Comissão apurada no PDV entra pelo **evento 7** | 003 §3 · 001 §7 | RFC-COMISSION/001 §5 (apuração) · RFC-COMISSION/005 (settlements) · RFC-004 §3.1 (evento 7) | db/010 (seed evento 7) · db/016/017/018 (módulo de comissões) |
| **Contabilização da comissão** (regra de comissão mapeada com par de contas) | 003 §4/§5/§6 | RFC-COMISSION/001 (política) · RFC-COMISSION/002 (PDV) | — (mesma mecânica do RFC-Payroll/001/002 — sem migration própria) |
| **Rastreabilidade por venda de origem no lançamento contábil da comissão** (materializada no **004** — camada analítica de ligação; o razão permanece **consolidado por regra**, decisão 5 do 003) | 004 §3/§4/§5 · 003 §7 (evolução) · 003 §8 decisão 5 | RFC-COMISSION/005 §7 (`commission_details` por funcionário × competência — consulta para conferência do holerite) · RFC-015 (projeto) §2.1 (relatório por venda de origem) | `commission_move_line_detail` (camada analítica do módulo — sem migration própria) sobre db/017 (`commission_details`) |
| **Comissão negativa** (devoluções superam vendas — valor líquido apurado) | 003 §2/§8 decisão 4 | RFC-COMISSION/001 §4 regra 6 | db/017 (`commission_settlements`) |

---

## 3. Conceitos que apontam para MÚLTIPLOS lugares (não-óbvios)

- **O contracheque é o ponto de encontro**: o RFC-007 (projeto) o materializa em
  `db/014` (`payroll_stubs`) e `db/015` (`payroll_entries`); o RFC-Payroll/001
  **estende o modelo da plataforma** (`hr.payslip`) com diário, contas padrão e
  vínculos do lançamento — sem criar tabela própria.
- **Sem migration própria**: o RFC-Payroll/001 **não adiciona arquivo em `db/`**
  (RFC-Payroll/001 §4 — modelo de dados sobre modelos da plataforma; decisão 1 —
  "sem modelos próprios", estende `hr.salary.rule`/`hr.payslip` e depende de
  `eh_hr_payroll` + `account`). As migrations listadas no **mapa §4** são as do
  **núcleo** que sustentam os dados que o módulo contabiliza.
- **Evento 7 (Comissão/Vendas)** conecta as duas séries: definido no RFC-004 do
  projeto (§3.1) e seedado na `db/010`; apurado pela RFC-COMISSION (db/016–018);
  a **contabilização** dele como regra mapeada está **especificada e aprovada**
  no **RFC-Payroll/003** (evolução declarada no RFC-Payroll/001 §7, agora
  materializada) e o **detalhamento por venda de origem** no lançamento é
  especificado no **RFC-Payroll/004**.
- **Única exceção a "sem models próprios"** (decisão 1 do RFC-Payroll/001): a
  camada analítica de ligação do **RFC-Payroll/004**
  (`commission_move_line_detail` — linha do razão × venda de origem) é o único
  modelo próprio do módulo — justificada porque `account.move.line` não
  referencia vendas do PDV; a contabilização de base (001/002/003) segue sem
  models/migrations próprios.

---

## 4. Migrations envolvidas (ordem de aplicação)

```
db/010 (payroll_periods/payroll_events — evento 7, proventos/descontos)
   → db/012 (payroll_runs/payroll_lines — resultado do processamento)
   → db/013 (tax_tables — tabelas INSS/IRRF do RFC-005)
   → db/014 (payroll_stubs — holerite) → db/015 (payroll_entries — corpo)
   → db/016/db/017/db/018 (módulo de comissões — apurado do evento 7)
```

> O RFC-Payroll/001 **não adiciona migration** à cadeia acima: a contabilização
> é feita no módulo `account` da plataforma (`account.move`/`account.move.line`),
> estendendo `hr.salary.rule` e `hr.payslip` (decisão 1 do RFC). As migrations
> do núcleo são a fonte dos valores contabilizados.

---

## 5. Cobertura atual e pendências

| Item | Status |
|---|---|
| RFC-Payroll/001 (contabilização automática da folha) | ✅ **aprovado** (v1.2.0) — módulo de plataforma com **modelo de dados** formalizado (§4) e **decisões da §8 aprovadas** (✅ 05/08/2026); sem models/migrations próprios |
| RFC-Payroll/002 (fluxos de contabilização) | ✅ **aprovado** (v1.1.0) — algoritmo de geração do lançamento e algoritmo de estorno sobre a mecânica `account`; **decisões da §8 aprovadas** (✅ 05/08/2026) |
| RFC-Payroll/003 (contabilização da comissão — evento 7) | ✅ **aprovado** (v1.0.0) — comissão como regra mapeada com par de contas; reutiliza a mecânica de 001/002; **decisões da §8 aprovadas** (✅ 05/08/2026); sem models/migrations próprios |
| RFC-Payroll/004 (detalhamento contábil por venda de origem no lançamento) | ✅ **aprovado** (v1.1.0) — camada analítica de ligação entre a linha da comissão no razão e a venda de origem (`commission_move_line_detail`, único model próprio da série); razão permanece consolidado por regra; **decisões da §8 aprovadas** (✅ 05/08/2026) |
| RFC-Payroll/README.md (propósito + convenção de numeração) | ✅ criado |
| RFC-Payroll/RFC-MAPA-rastreabilidade.md (este documento) | ✅ criado — liga a série aos RFCs do projeto central |
| Testes de integração do modelo de dados | ✅ `tests/test_payroll_accounting_integration.py` (11 casos — SQL puro simulando o modelo do RFC-001 §4 no cluster PostgreSQL: par de contas da regra, fallback e bloqueio, geração por regra/categoria com equilíbrio, idempotência, estorno postado/rascunho com `reversed_entry_id`/`move_reversal_id`), `tests/test_commission_accounting_integration.py` (8 casos — RFC-003: regra do evento 7 mapeada com par de contas 3.1.03/2.1.04 no lançamento, exemplo equilibrado 16.400, consolidação por regra, fallback/bloqueio e estorno do par da comissão) e `tests/test_commission_detail_accounting_integration.py` (10 casos — RFC-004: camada analítica de ligação `commission_move_line_detail` — razão consolidado preservado, ligações por venda de origem, invariante 5 da denormalização, geração validada/bloqueio, idempotência UNIQUE, escopo restrito à comissão, estorno herdado postado/rascunho e relatório integrado venda → lançamento) — validação da adoção no ambiente Odoo permanece pendente |
| Seção da série no mapa central (`docs-tecnicos/RFC-MAPA-encadeamento.md`) | ⏳ pendente — sugerida quando a série for adotada (mesmo padrão da RFC-COMISSION) |

---

*Mapa gerado em 05/08/2026 a partir dos cabeçalhos/seções de `RFC-Payroll/`,
`rfcs/` e `db/`.*
