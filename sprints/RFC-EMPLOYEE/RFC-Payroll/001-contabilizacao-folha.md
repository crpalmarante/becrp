# RFC-Payroll/001 — Contabilização Automática da Folha de Pagamento

| Campo | Valor |
|---|---|
| **Título** | Contabilização da folha: modelo de dados e funcionalidades — contas nas regras salariais, diário/contas padrão no contracheque, lançamento automático e estorno |
| **Autor** | crpalmarante |
| **Status** | ✅ Aprovado |
| **Data** | 05/08/2026 |
| **Versão** | 1.2.0 |
| **Área** | Integração contábil — Folha (dados + módulo da plataforma) |
| **Depende de** | Módulos `eh_hr_payroll` e `account` (plataforma); RFC-006 (projeto — processamento), RFC-007 (projeto — holerite) |
| **Impacta** | RFC-007 (projeto — holerite, vínculos do lançamento), RFC-COMISSION/RFC-001 (comissão contabilizada como evento 7), RFC-Payroll/002 (fluxos de contabilização), RFC-Payroll/003 (contabilização da comissão — evento 7), RFC-Payroll/004 (detalhamento por venda de origem), RFC-Payroll/005+ (evoluções: centro de custo, rateio) |

> **Natureza deste documento:** especifica o **módulo de contabilização da folha**
> de pagamento — extensão da plataforma que adiciona contabilização às **regras
> salariais** e aos **contracheques** já existentes. Este RFC é **orientado a
> implementação**: descreve o **modelo de dados** (campos novos — §4), os fluxos
> de lançamento/estorno e a mecânica sobre os módulos `eh_hr_payroll` e
> `account`, **sem criar modelos próprios**. A **v1.1.0** formalizou o modelo de
> dados como **evolução** do escopo funcional; a **v1.2.0** aprova as decisões da
> §8 (✅ 05/08/2026) e marca o documento como **✅ Aprovado**.

---

## 1. Objetivo

Automatizar a contabilização da folha de pagamento de ponta a ponta:

1. **Cada regra salarial** passa a ter um **par de contas** (débito/crédito), de
   modo que despesas com salários, líquido a pagar e impostos a pagar caiam nas
   contas **escolhidas pelo usuário**.
2. **Cada contracheque** ganha um **diário geral** e um **par de contas padrão**
   (fallback) usado sempre que uma regra não estiver mapeada.
3. A **confirmação** de um contracheque **cria e lança automaticamente** o
   registro contábil equilibrado; um **botão manual** cobre os contracheques já
   pagos antes da configuração contábil.
4. O **cancelamento** de um contracheque **estorna** o lançamento efetuado,
   mantendo o livro-razão correto e o histórico rastreável.

## 2. Conceito

| Conceito | Definição |
|---|---|
| **Regra salarial mapeada** | Regra salarial com **conta de débito** e **conta de crédito** definidas. |
| **Lançamento por categoria** | Registro contábil organizado por categoria de regra, em que cada regra contribui com **sua própria linha equilibrada** (débito = crédito). |
| **Par padrão (fallback)** | Par de contas configurado no contracheque (despesas com salários / salários a pagar) usado quando a regra **não** está mapeada. |
| **Lançamento contábil** | `account.move` de tipo *entry*, sempre **equilibrado** (total débito = total crédito). |
| **Estorno** | Lançamento reverso, **vinculado ao contracheque** e **associado ao lançamento original**. |
| **Contracheque pago sem lançamento** | Contracheque confirmado antes da configuração contábil — coberto pelo botão manual (§3.3). |

## 3. Funcionalidades

### 3.1 Mapeamento de contas nas regras salariais

- Adiciona **dois campos por regra salarial**: uma **conta de débito** e uma
  **conta de crédito**.
- Ao mapeá-las, obtém-se um **lançamento por categoria**, no qual **cada regra
  contribui com sua própria linha equilibrada** de débito e crédito.
- Efeito prático: **despesas com salários**, **valores líquidos a pagar** e
  **impostos a pagar** são contabilizados nas contas de sua escolha.

### 3.2 Diário e contas padrão (fallback) no contracheque

- Adiciona um **seletor de diário geral** (`journal`) no contracheque.
- Adiciona **contas padrão** para dois papéis: **despesas com salários** e
  **salários a pagar**.
- Exibe **links somente leitura** para o **lançamento contábil efetuado** e para
  o seu **estorno** (`move_id`/`move_reversal_id` — §4.2).
- O **par de contas padrão** é utilizado sempre que as regras **não estiverem
  mapeadas** para contas específicas.

### 3.3 Lançamento automático na confirmação e botão manual quando necessário

- A **confirmação de um contracheque configurado** cria e lança
  **automaticamente** o registro contábil equilibrado (`move_id` — §4.2).
- Um botão **"Lançar no diário"** em contracheques **pagos** atende aos casos em
  que a configuração contábil foi realizada **após a confirmação** — garantindo
  que **nenhum contracheque fique sem o devido lançamento** (retrofit).

### 3.4 Estorno no cancelamento

- O **cancelamento de um contracheque**:
  - **estorna** o lançamento contábil efetuado; ou
  - **cancela** o registro que ainda estava em **rascunho**.
- O estorno é **registrado vinculado ao contracheque** e **associado ao
  lançamento original**, assegurando que o cancelamento seja refletido
  corretamente no **livro-razão** (`reversed_entry_id`/`move_reversal_id` — §4.3).

### 3.5 Baseado nos mecanismos da plataforma (sem modelos próprios)

- **Não utiliza modelos próprios**: estende as funcionalidades existentes de
  **contracheque** (`hr.payslip`) e **regra salarial** (`hr.salary.rule`).
- Depende **apenas** dos módulos **`eh_hr_payroll`** e **`account`**.
- Pode ser instalado **juntamente com a plataforma ou separadamente**, através
  do menu de **Aplicativos**.

## 4. Modelo de Dados — Campos Novos (evolução v1.1.0)

> **Evolução:** esta seção **formaliza o modelo de dados** que materializa as
> funcionalidades da §3. Os campos **estendem modelos existentes** da plataforma
> (`hr.salary.rule`, `hr.payslip`) — **sem models próprios nem migration SQL**
> (decisão 1); a contabilização vive no módulo `account`.

### 4.1 `hr.salary.rule` — contas por regra salarial (§3.1)

| Campo | Tipo | Alvo | Leitura | Descrição |
|---|---|---|---|---|
| `debit_account_id` | Many2one | `account.account` | edição | Conta de **débito** da regra — sua linha no lançamento |
| `credit_account_id` | Many2one | `account.account` | edição | Conta de **crédito** da regra |

**Invariante (par):** ambos preenchidos ou ambos vazios; regra sem par recai no
**fallback** do contracheque (§4.2).

### 4.2 `hr.payslip` — diário, contas padrão e vínculos do lançamento (§3.2/§3.3)

| Campo | Tipo | Alvo | Leitura | Descrição |
|---|---|---|---|---|
| `journal_id` | Many2one | `account.journal` | edição | Diário geral do lançamento (tipo *general*) |
| `default_debit_account_id` | Many2one | `account.account` | edição | Conta padrão de débito — **despesas com salários** (fallback) |
| `default_credit_account_id` | Many2one | `account.account` | edição | Conta padrão de crédito — **salários a pagar** (fallback) |
| `move_id` | Many2one | `account.move` | **somente leitura** | Lançamento contábil efetuado |
| `move_reversal_id` | Many2one | `account.move` | **somente leitura** | Estorno vinculado ao contracheque |

### 4.3 `account.move` / `account.move.line` — mecânica da plataforma (§3.4)

| Elemento | Valor | Descrição |
|---|---|---|
| `move_type` | `'entry'` | Lançamento geral (não-fatura) |
| Linhas (`account.move.line`) | par por regra | Cada regra contribui com **débito + crédito** equilibrados, agrupados por categoria (§3.1) |
| `reversed_entry_id` | Many2one → `account.move` (somente leitura) | Padrão do módulo `account`: o estorno aponta ao lançamento original — espelhado no `move_reversal_id` do contracheque |

### 4.4 Invariantes e validações

1. **Par da regra** — `debit_account_id` e `credit_account_id` ambos ou nenhum.
2. **Fallback** — regra sem par usa o par padrão do contracheque; sem nenhum
   dos dois, a **confirmação é bloqueada** com mensagem clara.
3. **Equilíbrio** — todo lançamento tem total débito = total crédito (validação
   no `account.move`).
4. **Idempotência** — um `move_id` por contracheque; o botão manual (§3.3) só
   cria lançamento quando `move_id` está vazio (decisão 5).
5. **Estorno vinculado** — cancelamento (§3.4) cria o estorno com
   `reversed_entry_id` → original e grava `move_reversal_id` no contracheque.

## 5. Fluxos

### 5.1 Fluxo normal (confirmação → lançamento)

1. O usuário configura o **diário** e as **contas padrão** no contracheque (ou
   herda os padrões configurados).
2. As regras do contracheque são resolvidas: regras **mapeadas** usam suas
   contas; regras **sem mapeamento** usam o **par padrão** (fallback).
3. Ao **confirmar** o contracheque, o módulo **cria e lança automaticamente** o
   registro contábil equilibrado, agrupado **por categoria**, com uma linha
   balanceada de débito/crédito por regra.
4. O contracheque passa a exibir o **link (somente leitura)** do lançamento
   efetuado.

### 5.2 Fluxo retrofit (configuração após a confirmação)

1. O contracheque foi confirmado/pago **antes** da configuração contábil.
2. O usuário realiza a configuração (mapeamento de contas das regras e/ou
   diário/contas padrão).
3. O usuário aciona o botão **"Lançar no diário"** — o módulo cria o lançamento
   retroativamente, garantindo que **nenhum contracheque fique sem lançamento**.

### 5.3 Fluxo de cancelamento (estorno)

1. O usuário **cancela** um contracheque.
2. Se o lançamento estava **em rascunho** → o módulo **cancela** o registro.
3. Se o lançamento estava **efetuado** → o módulo **estorna** o lançamento,
   registrando o **estorno vinculado ao contracheque** e **associado ao
   lançamento original**.
4. O contracheque passa a exibir o **link (somente leitura)** do estorno.

## 6. Exemplo de lançamento

Folha com as regras abaixo, todas mapeadas (diário geral 001 — Diversos):

| Regra (categoria) | Débito | Crédito | Valor |
|---|---|---|---|
| Salário base (Despesa) | 3.1.01 — Despesas com salários | 2.1.01 — Salários a pagar | R$ 10.000,00 |
| INSS empregador (Encargos) | 3.1.02 — Despesas com encargos | 2.1.02 — INSS a recolher | R$ 2.000,00 |
| INSS empregado (Dedução) | 2.1.01 — Salários a pagar | 2.1.02 — INSS a recolher | R$ 900,00 |
| IRRF (Dedução) | 2.1.01 — Salários a pagar | 2.1.03 — IRRF a recolher | R$ 1.100,00 |

> **Total débito = Total crédito = R$ 14.000,00** — lançamento equilibrado,
> organizado por categoria, com cada regra contribuindo com sua linha própria.
> Se uma regra não estivesse mapeada, o par **padrão do contracheque**
> (despesas com salários / salários a pagar) seria usado como fallback.

## 7. Escopo Fora Deste RFC

- **Rateio por centro de custo / departamento** (uma regra com contas
  diferentes por unidade de negócio) → evolução.
- **Moeda estrangeira** e câmbio nos lançamentos → evolução.
- **Lançamento consolidado por competência** (um lote para toda a folha, em vez
  de um lançamento por contracheque) → evolução.
- **Contabilização automática da comissão apurada no PDV** — a comissão entra
  na folha pelo evento 7 (RFC-COMISSION/RFC-001); a contabilização dela segue
  a mesma mecânica deste RFC (regra de comissão mapeada com par de contas) →
  **RFC-Payroll/003** (já especificada e aprovada).
- Detalhes do **livro-razão** e fechamento contábil (projeto central) → RFC-006
  (projeto), RFC-007 (projeto) e módulos contábeis da plataforma.

## 8. Decisões

1. **Sem modelos próprios** — o módulo estende `hr.salary.rule` e `hr.payslip`,
   dependendo apenas de `eh_hr_payroll` + `account`. Instalação com a plataforma
   ou separada (menu Aplicativos). ✅ 05/08/2026
2. **Par padrão como fallback** — regra sem mapeamento usa as contas padrão do
   contracheque (despesas com salários / salários a pagar). ✅ 05/08/2026
3. **Lançamento automático na confirmação + botão manual** — o botão "Lançar no
   diário" garante cobertura de contracheques pagos antes da configuração (§3.3). ✅ 05/08/2026
4. **Estorno vinculado e associado** — cancelamento estorna (ou cancela rascunho),
   registrando o estorno vinculado ao contracheque e associado ao lançamento
   original (§3.4, §4.4). ✅ 05/08/2026
5. **Um lançamento por contracheque** — sem relançamento duplicado: a
   confirmação e o botão manual só criam lançamento quando ainda não há
   lançamento válido para o contracheque (§4.4). ✅ 05/08/2026
6. **Campos sobre modelos da plataforma (evolução v1.1.0)** — nomes seguem a
   convenção Odoo: `debit_account_id`/`credit_account_id` em `hr.salary.rule`;
   `journal_id`, `default_debit_account_id`/`default_credit_account_id`,
   `move_id` e `move_reversal_id` em `hr.payslip`; estorno via
   `reversed_entry_id` no `account.move` (§4). Sem migration própria. ✅ 05/08/2026
7. **Confirmação bloqueada sem contas** — se uma regra não tem par e o
   contracheque não tem par padrão, a **confirmação é bloqueada** com mensagem
   clara (invariante §4.4). ✅ 05/08/2026

## 9. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| crpalmarante | autor | ✅ | 05/08/2026 |
