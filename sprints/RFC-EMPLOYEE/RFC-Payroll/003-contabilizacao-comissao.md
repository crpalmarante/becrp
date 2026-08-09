# RFC-Payroll/003 — Contabilização Automática da Comissão (Evento 7)

| Campo | Valor |
|---|---|
| **Título** | Contabilização automática da comissão (evento 7): regra de comissão mapeada com par de contas |
| **Autor** | crpalmarante |
| **Status** | ✅ Aprovado |
| **Data** | 05/08/2026 |
| **Versão** | 1.0.0 |
| **Área** | Integração contábil — Folha (comissão) |
| **Depende de** | RFC-Payroll/001 (modelo de dados e funcionalidades), RFC-Payroll/002 (fluxos de contabilização); RFC-COMISSION/001 (política), RFC-COMISSION/005 (apuração das vendas); RFC-004 (projeto — evento 7), RFC-006 (projeto — processamento); módulos `eh_hr_payroll` + `account` (plataforma) |
| **Impacta** | RFC-007 (projeto — holerite, comissão exibida e contabilizada), RFC-015 (projeto — relatórios), RFC-COMISSION/001 (política — comissão contabilizada), RFC-Payroll/004 (detalhamento contábil por venda de origem no lançamento), RFC-Payroll/005+ (evoluções: centro de custo, rateio) |

> **Natureza deste documento:** especifica a **contabilização automática da
> comissão de vendas** apurada no PDV — a **evolução declarada** no
> RFC-Payroll/001 §7 e no RFC-Payroll/002 §6/§7. A comissão entra na folha pelo
> **evento 7 (Comissão/Vendas)** e é contabilizada como **regra mapeada com par
> de contas**, usando **exatamente a mesma mecânica** do RFC-Payroll/001 (§4 —
> modelo de dados) e do RFC-Payroll/002 (§3/§4 — geração e estorno), **sem
> models nem migrations próprios**.

---

## 1. Objetivo

1. **Contabilizar a comissão** apurada no PDV (RFC-COMISSION/005) quando ela
   entra na folha pelo **evento 7** (Comissão/Vendas — RFC-004 do projeto §3.1);
2. **Reutilizar a mecânica da série**: a regra de comissão é uma **regra
   salarial mapeada** com **par de contas** (`debit_account_id`/
   `credit_account_id`), contabilizada pelo algoritmo de **geração** do
   RFC-Payroll/002 §3 e **estornada** no cancelamento (RFC-Payroll/002 §4);
3. Garantir que **despesa com comissão** e **comissão a pagar** caiam nas
   contas escolhidas, com o **lançamento equilibrado** (débito = crédito) e o
   **histórico rastreável** até a venda de origem.

## 2. Conceito

| Conceito | Definição |
|---|---|
| **Regra de comissão mapeada** | Regra salarial do **evento 7** com `debit_account_id` (ex.: despesa com comissões) e `credit_account_id` (ex.: comissões a pagar) definidas. |
| **Evento 7 (Comissão/Vendas)** | Evento de provento do catálogo (RFC-004 do projeto §3.1, seed `db/010`) alimentado pelo apurado do PDV (RFC-COMISSION/005, `db/017`). |
| **Valor da comissão** | Apurado por competência no PDV (congelado em `commission_settlements` — RFC-COMISSION/005 §3.5) e lançado no contracheque como evento 7. |
| **Mesma mecânica** | A contabilização da comissão usa os algoritmos do RFC-Payroll/002: **movimento por regra por categoria**, equilíbrio, idempotência e estorno — sem código novo de contabilização. |
| **Comissão negativa** | Devoluções/cancelamentos que superam as vendas do período (RFC-COMISSION/001 §4 regra 6): o valor líquido apurado entra no evento 7 e é contabilizado como o valor do contracheque. |

## 3. Origem do Valor — do PDV ao contracheque

1. O PDV **apura** a comissão por competência (RFC-COMISSION/005 — `pos_sales`,
   `pos_sale_items`, `commission_details`; congelada em
   `commission_settlements`);
2. O apurado entra na folha pelo **evento 7** (RFC-COMISSION/001 §5 regra 4) no
   processamento da competência (RFC-006 do projeto — `db/012` `payroll_lines`);
3. O **contracheque** (RFC-007 do projeto — `db/014`/`db/015`) exibe a comissão
   como provento do evento 7;
4. O módulo de contabilização trata a regra do evento 7 como **regra mapeada**
   — mesma mecânica de qualquer outra regra salarial (§4).

## 4. Modelo de Dados — a comissão como regra mapeada

**Não há campos novos**: a comissão usa os campos do RFC-Payroll/001 §4.1
(`debit_account_id`/`credit_account_id` na regra salarial do evento 7) e o
fallback do RFC-Payroll/001 §4.2 (par padrão do contracheque).

| Elemento | Valor | Descrição |
|---|---|---|
| Regra do evento 7 (`hr.salary.rule`) | mapeada | `debit_account_id` = despesa com comissões (ex.: 3.1.03); `credit_account_id` = comissões a pagar (ex.: 2.1.04) |
| Categoria da regra | Despesa (provento variável) | Agrupa a linha da comissão no lançamento por categoria (RFC-002 §3.3) |
| Fallback (§4.2 do RFC-001) | aplicado | Regra de comissão **sem par** usa o par padrão do contracheque; sem nenhum, **bloqueia** a geração (invariante §4.4) |
| Lançamento (`account.move`) | tipo *entry* | Mesma mecânica do RFC-Payroll/002 §3 |

> **Invariantes herdados** (RFC-Payroll/001 §4.4): par da regra, fallback,
> equilíbrio, idempotência (um `move_id` por contracheque) e estorno vinculado
> (`reversed_entry_id`/`move_reversal_id`).

## 5. Algoritmos — herdados do RFC-Payroll/002

A contabilização da comissão **não tem algoritmo próprio**:

- **Geração** — o contracheque confirmado (com a regra do evento 7) gera o
  lançamento pelo algoritmo do RFC-Payroll/002 §3: a regra de comissão
  contribui com seu **par de linhas débito/crédito**, agrupado por categoria,
  com validação de equilíbrio e `action_post` automático;
- **Estorno** — o cancelamento do contracheque estorna o lançamento pelo
  algoritmo do RFC-Payroll/002 §4 (rascunho → cancela; postado → estorno com
  sinais invertidos + `reversed_entry_id` + `move_reversal_id`);
- **Idempotência** — um lançamento por contracheque (RFC-Payroll/001 §8 decisão
  5); o botão manual "Lançar no diário" cobre retrofit (RFC-001 §3.3).

## 6. Exemplo de lançamento

Folha com salário base, **comissão (evento 7)** e encargos, todas mapeadas
(diário 001 — Diversos):

| Regra (categoria) | Débito | Crédito | Valor |
|---|---|---|---|
| Salário base (Despesa) | 3.1.01 — Despesas com salários | 2.1.01 — Salários a pagar | R$ 10.000,00 |
| **Comissão — evento 7 (Despesa)** | **3.1.03 — Despesas com comissões** | **2.1.04 — Comissões a pagar** | **R$ 2.000,00** |
| INSS empregador (Encargos) | 3.1.02 — Despesas com encargos | 2.1.02 — INSS a recolher | R$ 2.400,00 |
| INSS empregado (Dedução) | 2.1.01 — Salários a pagar | 2.1.02 — INSS a recolher | R$ 900,00 |
| IRRF (Dedução) | 2.1.01 — Salários a pagar | 2.1.03 — IRRF a recolher | R$ 1.100,00 |

> **Total débito = Total crédito = R$ 16.400,00** — lançamento equilibrado, com
> a **comissão contribuindo com seu par próprio** (despesa 3.1.03 / comissão a
> pagar 2.1.04), agrupado por categoria. Se a regra do evento 7 não estivesse
> mapeada, o **par padrão do contracheque** seria usado como fallback; sem
> nenhum dos dois, a geração seria **bloqueada** (RFC-001 §4.4).

## 7. Escopo Fora Deste RFC

- **Rateio da comissão por centro de custo / departamento** (contas diferentes
  por unidade de negócio) → evolução (RFC-Payroll/005+).
- **Comissão por faixas de meta** no lançamento (a mecânica de tabelas internas
  é do RFC-005 do projeto) → evolução.
- **Moeda estrangeira** e câmbio nos lançamentos → evolução.
- **Detalhamento contábil por venda de origem** no lançamento (camada analítica
  de ligação por venda, mantendo o razão consolidado por regra) →
  **RFC-Payroll/004** (já especificada — rastreabilidade da venda ao lançamento;
  conceito rastreado na **tabela §2.3** do
  `RFC-Payroll/RFC-MAPA-rastreabilidade.md`).
- Detalhes do **livro-razão** e fechamento contábil (projeto central) → RFC-006
  (projeto), RFC-007 (projeto) e módulos contábeis da plataforma.

## 8. Decisões

1. **Comissão como regra mapeada** — a regra do evento 7 recebe
   `debit_account_id`/`credit_account_id` (despesa com comissões / comissões a
   pagar), sem campos novos (§4). ✅ 05/08/2026
2. **Mesma mecânica da série** — geração e estorno usam os algoritmos do
   RFC-Payroll/002; nenhum código novo de contabilização (§5). ✅ 05/08/2026
3. **Fallback e bloqueio herdados** — regra de comissão sem par usa o par
   padrão do contracheque; sem nenhum, a geração é bloqueada (RFC-001 §4.4).
   ✅ 05/08/2026
4. **Valor apurado do PDV** — a base contabilizada é a comissão **apurada por
   competência** (RFC-COMISSION/005, `commission_settlements`), conforme o
   **tratamento de comissão negativa da política** (RFC-COMISSION/001 §4 regra
   6 e decisão 4 — padrão: abater no mês seguinte) (§2/§3). ✅ 05/08/2026
5. **Consolidação por regra no lançamento** — o lançamento é consolidado por
   regra (par débito/crédito); o detalhamento por venda de origem permanece
   analítico no RFC-COMISSION/005 (§7) — a **rastreabilidade da venda no
   lançamento** é especificada no **RFC-Payroll/004** (camada analítica de
   ligação; o razão permanece consolidado). ✅ 05/08/2026

## 9. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| crpalmarante | autor | ✅ | 05/08/2026 |
