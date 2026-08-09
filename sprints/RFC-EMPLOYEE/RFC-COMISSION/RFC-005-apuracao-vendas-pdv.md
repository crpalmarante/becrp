# RFC-005 — Apuração das Vendas do PDV e Comissão por Venda

| Campo | Valor |
|---|---|
| **Título** | Apuração das vendas do PDV (venda × item × vendedor) e detalhamento da comissão por venda |
| **Autor** | crpalmarante |
| **Status** | 📝 Draft (em revisão) |
| **Data** | 05/08/2026 |
| **Versão** | 1.2.0 |
| **Área** | Módulo — Comissões / PDV (apuração) |
| **Depende de** | RFC-COMISSION/RFC-002 (regras do módulo), RFC-COMISSION/RFC-003 (modelo de dados + db/016) |
| **Impacta** | RFC-006 (projeto — Processamento), RFC-007 (projeto — Holerite), RFC-015 (projeto — Relatórios) |

> **Natureza deste documento:** descreve a **apuração das vendas do PDV** —
> como a venda registrada (venda × item × vendedor) gera a **comissão por
> venda**, com a taxa resolvida pela precedência (RFC-COMISSION/RFC-002 §3.1), e como o
> apurado do período alimenta o **evento 7 (Comissão/Vendas)** na folha
> (RFC-006 (projeto)). Fecha a lacuna de granularidade apontada no RFC-COMISSION/RFC-002 §5 regra 5:
> o detalhamento por venda de origem agora tem tabela própria.

---

## 1. Objetivo

Transformar as **vendas registradas no PDV** na fonte da comissão do vendedor:
cada venda (com seus itens e o vendedor responsável) é apurada pela precedência
produto → categoria → taxa padrão (RFC-COMISSION/RFC-002 §3.1), gera o **detalhe da comissão
por venda** e consolida o valor do período que entra como provento no evento 7
da folha — de forma auditável, da venda ao holerite.

## 2. Conceito

| Conceito | Definição |
|---|---|
| **Venda do PDV** | Documento da venda registrado no PDV, com data, vendedor e itens (venda × item × vendedor). |
| **Item de venda** | Linha da venda: produto, quantidade e valor vendido. A comissão incide sobre o item. |
| **Vendedor** | Funcionário responsável pela venda (RFC-002 (projeto)) — o comissionado. |
| **Comissão por venda** | Valor gerado pela venda = soma das comissões dos itens, cada uma com a taxa da regra vigente na data da venda. |
| **Apuração do período** | Consolidação das comissões por funcionário × competência que alimenta o evento 7 na folha. |
| **Origem da regra** | Qual nível da precedência resolveu a taxa do item (produto, categoria ou padrão) — registrado para auditoria. |
| **Devolução parcial** | Retorno de um ou mais itens de uma venda (não a venda inteira): o item recebe `pos_sale_items.status = 'devolvido'` e sai da apuração; a venda permanece `aberta` (ver §3.2/§5 regra 2). |
| **Devolução total** | Retorno da venda inteira: representado por `pos_sales.status = 'cancelada'`/`'estornada'` — a venda sai da apuração (§5 regra 2). |

## 3. Modelo de Dados (migration de acompanhamento — db/017, proposta)

Convenções do projeto: SQL puro, tabelas em inglês plural, inativação lógica,
sem exclusão física, permissão por ação (db/011). Pré-requisitos: db/002
(employees), db/016 (products, product_categories, commission_rules).

### 3.1 `pos_sales` — cabeçalho da venda

| Coluna | Tipo | Regra | Definição |
|---|---|---|---|
| id | BIGSERIAL | PK | Identificador da venda |
| code | TEXT | NOT NULL UNIQUE | Número/identificador da venda no PDV |
| employee_id | BIGINT | NOT NULL FK → employees | Vendedor responsável (RFC-002 (projeto)) |
| sale_date | DATE | NOT NULL | Data da venda — define a regra vigente |
| total_value | NUMERIC(12,2) | NOT NULL CHECK ≥ 0 | Total vendido |
| status | TEXT | DEFAULT 'aberta' CHECK (aberta/cancelada/estornada) | Situação da venda — **só vendas `aberta` entram na apuração** (ver §3.4/§5 regra 2) |
| created_at / updated_at | TIMESTAMPTZ | DEFAULT now() | Auditoria |

### 3.2 `pos_sale_items` — itens da venda

| Coluna | Tipo | Regra | Definição |
|---|---|---|---|
| id | BIGSERIAL | PK | Identificador do item |
| sale_id | BIGINT | NOT NULL FK → pos_sales | Venda a que pertence |
| product_id | BIGINT | NOT NULL FK → products | Produto vendido (db/016) |
| quantity | NUMERIC(12,3) | NOT NULL CHECK > 0 | Quantidade |
| unit_price | NUMERIC(12,2) | NOT NULL CHECK ≥ 0 | Preço unitário |
| item_total | NUMERIC(12,2) | NOT NULL CHECK ≥ 0 | = quantity × unit_price — CHECK `item_total = quantity × unit_price` (padrão de CHECKs do projeto, ex.: `ck_liquid_equation` da db/012) |
| status | TEXT | DEFAULT 'ativo' CHECK (ativo/devolvido) | Situação do item — **devolução parcial**: item `devolvido` sai da apuração (ver §3.4/§5 regra 2), a venda permanece `aberta` |
| created_at | TIMESTAMPTZ | DEFAULT now() | Auditoria |

> O vendedor é do cabeçalho (`pos_sales.employee_id`) — o item não repete o
> funcionário (uma venda tem um vendedor na 1ª versão; divisão de venda entre
> vendedores fica para evolução).

### 3.3 `commission_details` — detalhe da comissão POR VENDA (a tabela que fecha a rastreabilidade)

Uma linha por **item de venda apurado**: a comissão individual com a taxa
resolvida e a **origem da regra** registrada.

| Coluna | Tipo | Regra | Definição |
|---|---|---|---|
| id | BIGSERIAL | PK | Identificador |
| sale_id | BIGINT | NOT NULL FK → pos_sales | Venda de origem |
| sale_item_id | BIGINT | NOT NULL FK → pos_sale_items (UNIQUE) | Item apurado — um detalhe por item |
| employee_id | BIGINT | NOT NULL FK → employees | Vendedor (deve ser o da venda) |
| product_id | BIGINT | NOT NULL FK → products | Produto do item |
| rate_source | TEXT | NOT NULL CHECK (produto/categoria/padrao) | Nível da precedência que resolveu a taxa |
| rule_id | BIGINT | FK → commission_rules | Regra aplicada (quando existir — taxa padrão também é linha da db/016) |
| rate_percent | NUMERIC(5,2) | NOT NULL CHECK 0–100 | Taxa efetivamente aplicada |
| commission_value | NUMERIC(12,2) | NOT NULL CHECK ≥ 0 | = item_total × rate_percent/100 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | Auditoria |

**Constraints de negócio:**
1. `UNIQUE (sale_item_id)` — um detalhe por item apurado (sem duplicidade).
2. `employee_id` = vendedor da venda (consistência — como a db/015 invariante 2).
3. **Imutabilidade** — detalhe apurado não se edita/apaga (rastreabilidade RFC-007 (projeto)
   regra 2). **Estorno/devolução NÃO se representam com valor negativo nem
   UPDATE**: o cancelamento da venda vive no `status` do cabeçalho
   (`pos_sales.status`) e a **devolução parcial** vive no `status` do item
   (`pos_sale_items.status = 'devolvido'`). A apuração (§3.4/§4 passo 4) soma
   apenas os detalhes de vendas **`aberta`** com itens **`ativo`** (filtros
   `status = 'aberta'` e `status = 'ativo'` no join — `cancelada`, `estornada`
   e `devolvido` saem). O detalhe permanece como trilha de auditoria do que foi
   calculado, sem negativos (padrão db/012/db/015).

### 3.4 (Consolidação) — apuração por funcionário × competência

A consolidação mensal que alimenta o evento 7 não precisa de tabela própria na
1ª versão: é derivada por consulta de `commission_details` **de vendas
`aberta` com itens `ativo`** (estornos e devoluções excluídos por status, sem
negativos) agrupada por (funcionário, competência da `sale_date`):

```sql
-- apuração consolidada por funcionário × competência (derivada)
SELECT cd.employee_id,
       DATE_TRUNC('month', s.sale_date)::date AS competencia,
       SUM(cd.commission_value) AS total_comissao
FROM commission_details cd
JOIN pos_sales s      ON s.id = cd.sale_id
JOIN pos_sale_items i ON i.id = cd.sale_item_id
WHERE s.status = 'aberta'    -- venda não cancelada/estornada (devolução total)
  AND i.status = 'ativo'     -- item não devolvido (devolução parcial)
GROUP BY cd.employee_id, DATE_TRUNC('month', s.sale_date)::date;
```

A folha (RFC-006 (projeto)) recebe o valor como lançamento do evento 7. **Enquanto a
competência não está fechada**, o valor considerado é o derivado por esta
consulta; **após o fechamento** (§3.5), o valor passa a ser o **congelado** na
`commission_settlements` — imune a devoluções/cancelamentos posteriores.

### 3.5 `commission_settlements` — congelamento do apurado por competência (fechamento)

O **fechamento da competência** grava uma linha por (funcionário × competência)
com o total apurado; a partir daí o valor da comissão do período fica
**congelado** e é o que alimenta o **evento 7** na folha (RFC-006 (projeto)). Devoluções,
cancelamentos ou correções **posteriores ao fechamento não alteram** o valor
congelado — a trilha de auditoria continua no `commission_details`, e o ajuste
financeiro é tratado como lançamento manual/importação no período corrente
(padrão RFC-COMISSION/RFC-001 §3 — fonte do valor).

| Coluna | Tipo | Regra | Definição |
|---|---|---|---|
| id | BIGSERIAL | PK | Identificador |
| employee_id | BIGINT | NOT NULL FK → employees | Funcionário comissionado (RFC-002 (projeto)) |
| competence | DATE | NOT NULL | Competência da apuração (1º dia do mês) — mesma granularidade da consulta da §3.4 |
| total_value | NUMERIC(12,2) | NOT NULL CHECK ≥ 0 | Comissão consolidada e **congelada** do período (pré-DSR) |
| status | TEXT | DEFAULT 'fechado' CHECK (fechado/estornado) | Fechado (válido) / estornado (correção — libera regeração) |
| created_at / updated_at | TIMESTAMPTZ | DEFAULT now() | Auditoria; updated_at por trigger |

**Constraints de negócio:**

1. `uq_settlement_per_competence` — **uma linha `fechado` por (funcionário ×
   competência)** (índice único parcial, mesmo padrão da db/016 — RFC-003 §3.3):
   ```sql
   CREATE UNIQUE INDEX uq_settlement_per_competence
       ON commission_settlements (employee_id, competence)
       WHERE status = 'fechado';
   ```
2. **Imutabilidade** — após gravado, `commission_settlements` não muda as
   colunas de negócio (employee_id/competence/total_value); **só o `status` é
   alterável** (`'fechado'` → `'estornado'`) para corrigir um fechamento errado
   e permitir **regerar** — espelha o congelamento do cabeçalho (§5 regra 4).
3. **Sem exclusão física** — DELETE/TRUNCATE bloqueados (padrão RFC-008 (projeto) decisão 4).
4. **Permissão por `lancar_eventos`** — gerar/estornar o fechamento é
   **lançamento** (RFC-009 §3.1 via db/011, fail-closed — mesmo da apuração).

**Geração (fechamento da competência)** — idempotente e re-executável:

```sql
INSERT INTO commission_settlements (employee_id, competence, total_value)
SELECT cd.employee_id,
       DATE_TRUNC('month', s.sale_date)::date AS competencia,
       SUM(cd.commission_value)
FROM commission_details cd
JOIN pos_sales s      ON s.id = cd.sale_id
JOIN pos_sale_items i ON i.id = cd.sale_item_id
WHERE s.status = 'aberta' AND i.status = 'ativo'
GROUP BY cd.employee_id, DATE_TRUNC('month', s.sale_date)::date
ON CONFLICT (employee_id, competence) WHERE status = 'fechado' DO NOTHING;
```

> O `ON CONFLICT` com o predicado do índice parcial garante a **idempotência**:
> um segundo fechamento da mesma competência não duplica nem sobrescreve o
> valor. **Estornar** (`status = 'estornado'`) libera a regeração (nova linha
> `fechado`), preservando o histórico.

## 4. Fluxo de Apuração (da venda ao evento 7)

```
┌──────────────┐   ┌────────────────┐   ┌───────────────────┐   ┌──────────────┐
│ pos_sales    │──▶│ pos_sale_items │──▶│ commission_details│──▶│ evento 7     │
│ (venda)      │   │ (itens)        │   │ (comissão p/ venda│   │ (folha,      │
└──────────────┘   └────────────────┘   │  = item × taxa)   │   │  RFC-006)    │
                                        └───────────────────┘   └──────────────┘
```

1. **Venda registrada no PDV** → cabeçalho (`pos_sales`) com vendedor e data +
   itens (`pos_sale_items`).
2. **Apuracão por item** — para cada item, resolve a taxa pela precedência
   (produto → categoria → taxa padrão) com a regra **ativa e vigente na data da
   venda** (consulta do RFC-COMISSION/RFC-003 §5).
3. **Detalhe gravado** em `commission_details` com `rate_source` (origem da
   regra) e `commission_value` — a venda de origem vira rastreável no holerite.
4. **Consolidação do período** — soma dos detalhes por funcionário × competência
   (apuração derivada, §3.4).
5. **Alimenta a folha** — o apurado entra como provento no **evento 7
   (Comissão/Vendas)** do processamento da competência (RFC-006 (projeto) §3.1 passo 4),
   com as incidências do RFC-COMISSION/RFC-001 §6 (INSS/IRRF/FGTS) e o DSR (RFC-COMISSION/RFC-001 §7.1).
6. **Fechamento da competência** — a consolidação é **congelada** por
   funcionário × competência na `commission_settlements` (§3.5); a partir daí o
   evento 7 usa o valor congelado, imune a devoluções/cancelamentos posteriores.

> **Devolução após a apuração (fora do fluxo principal):** devolução **parcial**
> → `pos_sale_items.status = 'devolvido'` (o item sai da próxima consolidação,
> detalhe preservado, sem negativos); devolução **total** → `pos_sales.status =
> 'estornada'` (a venda sai da apuração). Em ambos os casos nada se apaga nem se
> altera no `commission_details` — a apuração é derivada e sempre refletirá os
> status atuais (§3.4). **Após o fechamento** (§3.5), a devolução tampouco
> altera o `commission_settlements` — o valor congelado permanece e o ajuste
> financeiro é tratado no período corrente (padrão RFC-COMISSION/RFC-001 §3).

## 5. Regras da Apuração

1. **A taxa é da data da venda** — vigência da regra avaliada na `sale_date`,
   não na data da apuração/fechamento (RFC-COMISSION/RFC-002 §5 regra 3). A resolução usa
   **apenas regras ativas** (RFC-COMISSION/RFC-003 §5) e a apuração é em tempo real, na data
   da venda (RFC-COMISSION/RFC-002 §7 decisão 4): **regra inativada deixa de ser resolvida**
   mesmo para vendas dentro da própria vigência — uma apuração retroativa de
   venda cuja regra já foi inativada cai no nível seguinte da precedência
   (categoria → padrão). Detalhes já apurados permanecem imutáveis (regra 3).
2. **Elegibilidade — por status, sem negativos** — cancelamentos/devoluções
   saem da apuração por status: **devolução total** → `pos_sales.status =
   'cancelada'` ou `'estornada'` (a venda sai — filtro `status = 'aberta'` da
   §3.4); **devolução parcial** → `pos_sale_items.status = 'devolvido'` (o item
   sai — filtro `status = 'ativo'` da §3.4, a venda permanece `aberta`). Item
   com `status = 'devolvido'` **não pode ser apurado** (fail-closed por trigger
   na db/017 — §3.3): a aplicação deve saltar itens devolvidos na apuração. A
   regra de elegibilidade da política (RFC-COMISSION/RFC-001 §3) vale para a apuração; não há
   valor negativo em `commission_details` (CHECK ≥ 0).
3. **Imutabilidade do detalhe apurado** — `commission_details` é imutável
   (sem UPDATE/DELETE/TRUNCATE, padrão db/015): correção = nova venda + nova
   apuração; o cancelamento da venda original (status) remove-a da apuração sem
   tocar no detalhe (auditoria preservada).
4. **Congelamento após apuração** — após a apuração do item, o **item**
   (`pos_sale_items`) não muda as colunas de negócio (product_id/quantity/
   unit_price/item_total); **só o `status` é alterável** — para `'devolvido'`
   (devolução parcial). O **cabeçalho** (`pos_sales`) não muda as colunas de
   negócio (code/employee_id/sale_date/total_value) de venda com detalhes — só o
   `status` (estorno) é alterável; qualquer correção = estorno da venda + nova
   venda (enforcement por trigger na db/017).
5. **Sem exclusão física** — vendas canceladas são inativadas/estornadas    (status), nunca apagadas (padrão RFC-008 (projeto) decisão 4).
6. **Permissão por ação** — registrar venda/item e apurar (gravar
   `commission_details`) é **lançamento** → ação `lancar_eventos` da matriz
   RFC-009 §3.1 (fail-closed via db/011, padrão do projeto). A confirmação
   final da ação (se `lancar_eventos` ou `manter_cadastros` para o registro de
   vendas) fica registrada na §9 decisão 5.
7. **Comissão por venda é a soma dos itens** — nada de comissão digitada na
   venda; o valor vem do item × taxa (RFC-COMISSION/RFC-002 §4).
8. **Congelamento do apurado (`commission_settlements`)** — o fechamento da
   competência grava o total por (funcionário × competência) e **congela** o
   valor que alimenta o evento 7; devoluções/cancelamentos posteriores ao
   fechamento não alteram o valor congelado (auditoria no detalhe, ajuste no
   período corrente). Uma linha `fechado` por (funcionário × competência);
   correção = estorno por status + regeração (§3.5).

## 6. Exemplo Numérico

Venda de 26/08/2026 do vendedor A (taxa padrão 1,5%; categoria Serviços 3%;
produto Celular Modelo X 5% — precedência RFC-COMISSION/RFC-002 §3.1):

| Item | Item total | Regra (origem) | Taxa | Comissão |
|---|---|---|---|---|
| Celular Modelo X | R$ 2.000,00 | produto (rule product) | 5% | R$ 100,00 |
| Plano de serviço | R$ 500,00 | categoria Serviços | 3% | R$ 15,00 |
| Acessório (sem regra) | R$ 100,00 | padrão | 1,5% | R$ 1,50 |
| **Total da venda** | **R$ 2.600,00** | | | **R$ 116,50** |

O detalhe grava 3 linhas em `commission_details` (uma por item, com `rate_source`
= produto/categoria/padrao). A soma do período vira o evento 7; o DSR sobre a
comissão é calculado na folha (RFC-COMISSION/RFC-001 §7.1).

**Devolução parcial (continuação):** o cliente devolve o "Plano de serviço". O
item recebe `pos_sale_items.status = 'devolvido'` (a venda permanece `aberta`);
a apuração consolidada passa a somar apenas Celular Modelo X (R$ 100,00) +
Acessório (R$ 1,50) = **R$ 101,50**. O detalhe do plano (R$ 15,00) permanece
gravado como auditoria — sem valor negativo e sem UPDATE no detalhe.

## 7. Integração com o Holerite (granularidade resolvida)

- O holerite (RFC-007 (projeto)) mostra o **evento 7 consolidado por competência** (uma
  entrada — db/015, `UNIQUE (stub_id, event_id)`).
- O **detalhamento por venda de origem** (funcionário, produto, taxa, valor) —
  que o RFC-COMISSION/RFC-002 §5 regra 5 apontava como evolução — agora é a consulta de
  `commission_details` por (funcionário × competência), disponível para o
  relatório de comissões (RFC-015 §2.1 — comissões por venda de origem) e para
  a conferência do holerite (cruzamento com o valor do evento 7).

## 8. Escopo Fora Deste RFC

- Regras de comissão e precedência → RFC-COMISSION/RFC-002.
- Modelo de dados das regras (db/016) → RFC-COMISSION/RFC-003.
- Tela de categorias e regras por categoria → RFC-COMISSION/RFC-004.
- Tela de produtos e regras por produto → RFC-COMISSION/RFC-006.
- Tela de taxa padrão do funcionário → RFC-COMISSION/RFC-007.
- Cálculo do DSR, médias de férias/13º e rescisão → RFC-COMISSION/RFC-001.
- Relatórios consolidados de comissões → RFC-015 (projeto).
- Divisão de venda entre múltiplos vendedores → evolução.
- Devolução de **quantidade parcial** de um item (ex.: devolver 1 de 3
  unidades do mesmo produto) → evolução: a 1ª versão devolve o **item
  inteiro** via `pos_sale_items.status = 'devolvido'` (uma linha = um item;
  devolução de fração exige novo split do item).

## 9. Decisões Aprovadas

1. **A venda é a fonte da comissão** — cada venda do PDV (venda × item ×
   vendedor) gera a comissão por item; nada de comissão digitada na venda.
   ✅ 05/08/2026
2. **Tabela de detalhe por venda (`commission_details`)** — uma linha por item
   apurado, com a taxa e a **origem da regra** (produto/categoria/padrão),
   fechando a rastreabilidade da venda ao holerite. ✅ 05/08/2026
3. **Apuração mensal derivada + fechamento congelado** — a consolidação por
   funcionário × competência é consulta sobre os detalhes de vendas **não
   canceladas** com itens **ativos** (§3.4); no **fechamento**, o valor é
   congelado na `commission_settlements` (§3.5, decisão 7) e passa a alimentar
   o evento 7. ✅ 05/08/2026
4. **Imutabilidade e estorno por status** — detalhe apurado imutável; o
   cancelamento é representado por `pos_sales.status = 'cancelada'` (nunca
   negativos, nunca UPDATE no detalhe, nunca exclusão física). ✅ 05/08/2026
5. **Permissão por `lancar_eventos`** — registrar venda/item e apurar
   (`commission_details`) usa a ação `lancar_eventos` da matriz RFC-009 §3.1
   (fail-closed via db/011). ✅ 05/08/2026
6. **Devolução parcial por status do item** — o retorno de um ou mais itens é
   representado por `pos_sale_items.status = 'devolvido'` (nunca negativos,
   nunca UPDATE no detalhe, nunca exclusão física); a consolidação (§3.4)
   exclui itens devolvidos e a venda permanece `aberta`. Devolução total =
   estorno no cabeçalho (`pos_sales.status`). ✅ 05/08/2026
7. **Congelamento do apurado por competência (`commission_settlements`)** — no
   fechamento, o total derivado é gravado por (funcionário × competência) e
   congelado: imutável, sem exclusão física, uma linha `fechado` por
   (funcionário × competência) (índice único parcial). Devoluções/
   cancelamentos posteriores ao fechamento **não alteram** o valor congelado
   (ajuste no período corrente, padrão RFC-COMISSION/RFC-001 §3); correção de
   fechamento = estorno por status + regeração. ✅ 05/08/2026

## 10. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| _em aberto_ | _autor_ | ⏳ | — |
