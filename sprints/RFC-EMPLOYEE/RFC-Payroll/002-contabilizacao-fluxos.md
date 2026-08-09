# RFC-Payroll/002 — Fluxos de Contabilização da Folha

| Campo | Valor |
|---|---|
| **Título** | Fluxos de contabilização: geração do lançamento (movimento por regra por categoria) e algoritmo de estorno no cancelamento |
| **Autor** | crpalmarante |
| **Status** | ✅ Aprovado |
| **Data** | 05/08/2026 |
| **Versão** | 1.1.0 |
| **Área** | Integração contábil — Folha (fluxos) |
| **Depende de** | RFC-Payroll/001 (modelo de dados e funcionalidades); RFC-006 (projeto — processamento), RFC-007 (projeto — holerite); módulos `eh_hr_payroll` + `account` (plataforma) |
| **Impacta** | RFC-007 (projeto — holerite, vínculos do lançamento/estorno); RFC-COMISSION/RFC-001 (comissão contabilizada como evento 7); RFC-Payroll/003 (contabilização da comissão — evento 7); RFC-Payroll/004 (detalhamento por venda de origem); RFC-Payroll/005+ (evoluções: centro de custo, rateio, lote por competência) |

> **Natureza deste documento:** detalha os **algoritmos** que implementam as
> funcionalidades do RFC-Payroll/001: (1) a **geração do lançamento contábil**
> a partir das regras salariais do contracheque — um **movimento por regra por
> categoria**; e (2) o **estorno** quando o contracheque é cancelado. Este RFC é
> **orientado a implementação** e usa a mecânica do módulo `account` da
> plataforma (`account.move`/`account.move.line`, `reversed_entry_id`), **sem
> criar modelos próprios**. A **v1.1.0** aprova as decisões da §8 (✅ 05/08/2026)
> e marca o documento como **✅ Aprovado**.

---

## 1. Objetivo

Definir, de forma executável, os dois fluxos centrais do módulo de
contabilização da folha (RFC-Payroll/001):

1. **Geração do lançamento** — como um contracheque confirmado (ou pago, via
   botão manual) vira um **lançamento contábil equilibrado**, com um **par de
   linhas (débito/crédito) por regra salarial**, agrupado **por categoria**.
2. **Estorno no cancelamento** — como o cancelamento de um contracheque
   **estorna** o lançamento efetuado (ou **cancela** o que ainda estava em
   rascunho), mantendo o livro-razão correto e o histórico rastreável.

## 2. Conceito

| Conceito | Definição |
|---|---|
| **Movimento por regra por categoria** | Cada **regra salarial** com valor não-zero contribui com um **par de linhas** (uma de débito, uma de crédito, mesmo valor); as linhas são **agrupadas por categoria** de regra dentro do lançamento. |
| **Geração** | Criação e lançamento (`action_post`) do `account.move` tipo *entry* a partir das regras do contracheque. |
| **Estorno** | Lançamento reverso, com sinais invertidos, vinculado ao contracheque (`move_reversal_id`) e associado ao original (`reversed_entry_id`). |
| **Rascunho** | `account.move` criado mas **não postado** — cancelado (não estornado) no cancelamento do contracheque. |
| **Idempotência** | Um `move_id` por contracheque: geração e estorno **não duplicam** lançamentos (RFC-Payroll/001 §8 decisão 5). |

## 3. Algoritmo de Geração do Lançamento

### 3.1 Entradas

- Contracheque **confirmado** (fluxo automático) ou **pago** (botão manual
  "Lançar no diário" — RFC-Payroll/001 §3.3);
- `journal_id` do contracheque (ou padrão da empresa);
- Regras salariais com valor do contracheque + contas resolvidas (§3.2);
- Campos do RFC-Payroll/001 §4.2 (`move_id` vazio — idempotência).

### 3.2 Resolução de contas (precedência)

Para cada regra salarial com valor não-zero:

1. **Regra mapeada** — usa `debit_account_id`/`credit_account_id` da regra
   (§4.1 do RFC-Payroll/001);
2. **Regra sem par** — usa o **par padrão** do contracheque
   (`default_debit_account_id`/`default_credit_account_id`);
3. **Sem nenhum dos dois** — **bloqueia a geração** com mensagem clara
   (invariante §4.4 e decisão 7 do RFC-Payroll/001).

### 3.3 Montagem do movimento (movimento por regra por categoria)

1. Para cada regra, gera-se um **par de linhas** `account.move.line`:
   - **débito** → conta de débito da regra, valor da regra;
   - **crédito** → conta de crédito da regra, valor da regra.
2. As linhas são **agrupadas por categoria** de regra (ex.: Despesa, Encargos,
   Dedução) dentro do mesmo lançamento — **um movimento por regra por
   categoria**: cada regra contribui com o seu par de linhas, estruturado e
   auditável, em um único lançamento por contracheque.
3. Cria-se o `account.move` com `move_type='entry'`, `journal_id` do
   contracheque, data da competência.
4. **Validação de equilíbrio** — total débito = total crédito (invariante §4.4
   do RFC-Payroll/001).
5. **Posta** o lançamento (`action_post`) e grava `move_id` no contracheque.

### 3.4 Pseudocódigo

```
função gerar_lancamento(contracheque, manual=false):
    # Pré-condições
    se contracheque.move_id não vazio:  retorna erro "já lançado"   # idempotência
    se não manual e contracheque não confirmado:  retorna erro
    se contracheque.journal_id vazio:  usa o diário herdado dos padrões (§5.1 do RFC-001)

    linhas = []
    para cada regra em contracheque.regras com valor != 0:
        (conta_debito, conta_credito) = resolver_contas(regra, contracheque)
        se nenhuma das duas:  bloqueia com mensagem (regra sem contas e sem fallback)
        linhas += linha(debito=conta_debito, valor=regra.valor, categoria=regra.categoria)
        linhas += linha(credito=conta_credito, valor=regra.valor, categoria=regra.categoria)

    move = account.move(move_type='entry', journal_id=contracheque.journal_id,
                        date=contracheque.competencia, line_ids=ordenar_por_categoria(linhas))
    valida_equilibrio(move)              # débito total = crédito total
    move.action_post()
    contracheque.move_id = move          # vínculo somente leitura (§4.2)
```

## 4. Algoritmo de Estorno no Cancelamento

### 4.1 Entradas e pré-condições

- Ação de **cancelamento** do contracheque;
- `move_id` atual do contracheque (pode estar vazio — nada a estornar).

### 4.2 Caso A — lançamento em rascunho

- O `account.move` foi criado mas **não postado** → **cancela o registro**
  (nenhum efeito no livro-razão; o lançamento deixa de existir).

### 4.3 Caso B — lançamento efetuado (postado)

1. Gera o **estorno** pelo mecanismo do módulo `account`: novo `account.move`
   com **sinais invertidos** (crédito vira débito e vice-versa), na mesma data
   ou na data do cancelamento (decisão de configuração);
2. O estorno aponta o **lançamento original** via `reversed_entry_id`;
3. **Posta** o estorno;
4. Grava `move_reversal_id` no contracheque (vínculo somente leitura).

### 4.4 Pseudocódigo

```
função estornar_contracheque(contracheque):
    move = contracheque.move_id
    se move vazio:  retorna (nada a estornar)

    se move.state == 'draft':
        move.button_cancel()                 # cancela rascunho — nada no razão
    senão se move.state == 'posted':
        estorno = move._reverse_moves(      # mecanismo do account: sinais invertidos
                     date=contracheque.cancelamento_data)
        estorno.action_post()               # lança o estorno
        contracheque.move_reversal_id = estorno   # vínculo (§4.2)
    # move_id permanece apontando ao lançamento original (rastreabilidade,
    # RFC-001 §3.4) — o estorno associado é o move_reversal_id
```

### 4.5 Pós-condições

- Lançamento original permanece no histórico com o estorno **associado**
  (`reversed_entry_id`);
- O contracheque exibe o **link somente leitura** do estorno
  (`move_reversal_id`);
- Livro-razão reflete o cancelamento (lançamento + estorno = zero líquido).

## 5. Exemplos

### 5.1 Geração (mesma folha do RFC-Payroll/001 §6)

Regras mapeadas (diário 001 — Diversos), movimento por regra por categoria:

| Categoria | Regra | Linha débito | Linha crédito | Valor |
|---|---|---|---|---|
| Despesa | Salário base | 3.1.01 — Despesas com salários | 2.1.01 — Salários a pagar | R$ 10.000,00 |
| Encargos | INSS empregador | 3.1.02 — Despesas com encargos | 2.1.02 — INSS a recolher | R$ 2.000,00 |
| Dedução | INSS empregado | 2.1.01 — Salários a pagar | 2.1.02 — INSS a recolher | R$ 900,00 |
| Dedução | IRRF | 2.1.01 — Salários a pagar | 2.1.03 — IRRF a recolher | R$ 1.100,00 |

> Total débito = Total crédito = **R$ 14.000,00** — equilibrado, com par por
> regra agrupado por categoria.

### 5.2 Estorno no cancelamento

Cancelando esse contracheque (lançamento postado):

| Categoria | Regra | Linha débito | Linha crédito | Valor |
|---|---|---|---|---|
| Despesa | Salário base | 2.1.01 — Salários a pagar | 3.1.01 — Despesas com salários | R$ 10.000,00 |
| Encargos | INSS empregador | 2.1.02 — INSS a recolher | 3.1.02 — Despesas com encargos | R$ 2.000,00 |
| Dedução | INSS empregado | 2.1.02 — INSS a recolher | 2.1.01 — Salários a pagar | R$ 900,00 |
| Dedução | IRRF | 2.1.03 — IRRF a recolher | 2.1.01 — Salários a pagar | R$ 1.100,00 |

> **Sinais invertidos** — o estorno aponta o original via `reversed_entry_id` e
> é registrado no `move_reversal_id` do contracheque. No livro-razão,
> lançamento + estorno = **zero líquido**.

## 6. Casos de Borda

1. **Retrofit (botão manual)** — contracheque pago antes da configuração
   contábil: o mesmo algoritmo de geração (§3) roda manualmente; idempotência
   garante que **não duplica** se já houver `move_id`.
2. **Cancelamento sem lançamento** — contracheque cancelado antes de qualquer
   geração: nada a estornar (§4.4).
3. **Regra sem contas nem fallback** — geração **bloqueada** com mensagem;
   contracheque permanece confirmado/pago sem lançamento até a configuração
   (cobrível pelo botão manual).
4. **Regra de comissão (evento 7)** — a contabilização da comissão apurada no
   PDV segue a **mesma mecânica** (regra mapeada com par de contas) —
   especificada no **RFC-Payroll/003** (evolução declarada no RFC-Payroll/001 §7).
5. **Estorno de lançamento já estornado** — bloqueado: um contracheque tem no
   máximo um `move_reversal_id` (decisão 5).

## 7. Escopo Fora Deste RFC

- **Rateio por centro de custo / departamento** (uma regra com contas
  diferentes por unidade de negócio) → evolução (RFC-Payroll/005+).
- **Moeda estrangeira** e câmbio nos lançamentos → evolução.
- **Lançamento consolidado por competência** (um lote para toda a folha, em vez
  de um lançamento por contracheque) → evolução.
- **Contabilização automática da comissão** apurada no PDV (evento 7) → mesma
  mecânica deste RFC, **RFC-Payroll/003** (já especificada e aprovada).
- Detalhes do **livro-razão** e fechamento contábil (projeto central) → RFC-006
  (projeto), RFC-007 (projeto) e módulos contábeis da plataforma.

## 8. Decisões

1. **Movimento por regra por categoria** — cada regra contribui com um **par de
   linhas** (débito/crédito), agrupadas por categoria, em um lançamento por
   contracheque (§3.3). ✅ 05/08/2026
2. **Posta automaticamente na geração** — `action_post` após validação de
   equilíbrio; rascunho só existe transitoriamente durante a geração (§3.4). ✅ 05/08/2026
3. **Estorno via mecanismo do módulo `account`** — sinais invertidos +
   `reversed_entry_id`; nenhum estorno manual linha a linha (§4.3). ✅ 05/08/2026
4. **Data do estorno** — data do cancelamento (ou da competência, conforme
   configuração) (§4.3 passo 1). ✅ 05/08/2026
5. **Um estorno por contracheque** — `move_reversal_id` único; cancelamento de
   contracheque já estornado é bloqueado (§6 caso 5). ✅ 05/08/2026
6. **`move_id` preservado após o estorno** — o lançamento original permanece
   vinculado ao contracheque (rastreabilidade, RFC-001 §3.4); o estorno é
   referenciado por `move_reversal_id` (§4.4). ✅ 05/08/2026

## 9. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| crpalmarante | autor | ✅ | 05/08/2026 |
