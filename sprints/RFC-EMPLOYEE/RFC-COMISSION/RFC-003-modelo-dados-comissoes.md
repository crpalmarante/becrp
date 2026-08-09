# RFC-003 — Modelo de Dados do Módulo de Comissões

| Campo | Valor |
|---|---|
| **Título** | Modelo de dados: product_categories, products e commission_rules (migration db/016) |
| **Autor** | crpalmarante |
| **Status** | 📝 Draft (em revisão) |
| **Data** | 05/08/2026 |
| **Versão** | 1.1.0 |
| **Área** | Módulo — Comissões / PDV (dados) |
| **Depende de** | RFC-COMISSION/RFC-001, RFC-COMISSION/RFC-002, RFC-002 (projeto — Cadastro), RFC-009 (projeto — Permissões) |
| **Impacta** | RFC-COMISSION/RFC-004 (tela de categorias/regras), RFC-COMISSION/RFC-005 (apuração/vendas), RFC-COMISSION/RFC-006 (tela de produtos/regras), RFC-COMISSION/RFC-007 (tela de taxa padrão), RFC-COMISSION/RFC-008 (tela de taxa padrão global — complementar), RFC-006 (projeto), RFC-007 (projeto) |

> **Natureza deste documento:** define o **modelo de dados** do módulo de
> comissões do PDV e a **migration SQL** que o materializa no PostgreSQL.
> Acompanha as migrations do projeto em `db/` (convenções PLAN_ERP §6: SQL puro,
> tabelas em inglês plural, inativação lógica, permissões via GUC).

---

## 1. Objetivo

Materializar as regras do RFC-COMISSION/RFC-002 em **tabelas e constraints**:
o catálogo de categorias, o catálogo de produtos e as regras de comissão por
funcionário × (produto | categoria | padrão) × taxa percentual, com a
**precedência** produto → categoria → taxa padrão garantida na consulta e sem
conflitos de regra duplicada no banco.

## 2. Visão do Modelo

```
┌───────────────────────┐     ┌───────────────────────┐
│ product_categories    │     │ commission_rules      │
│  id BIGSERIAL PK      │     │  id BIGSERIAL PK      │
│  code UNIQUE          │◀────│  employee_id  FK      │──▶ employees (RFC-002 (projeto))
│  description          │  FK │  product_id   FK      │──▶ products
│  status               │     │  category_id  FK      │──▶ product_categories
│                       │     │  rate_percent NUMERIC │
│  ▲                    │     │  valid_from / until   │
│  │ category_id (FK)   │     │  status               │
│  │                    │     └───────────────────────┘
│ ┌──────────────┐      │
│ │ products     │      │     Precedência (RFC-COMISSION/RFC-002 §3.1):
│ │  id PK       │      │       produto → categoria → padrão
│ │  code UNIQUE │      │     Taxa padrão = regra com product_id
│ │  category_id │      │       e category_id ambos NULL
│ │  status      │      │
│ └──────────────┘      │
└───────────────────────┘
```

Três tabelas, seguindo o mesmo desenho dos cadastros mestres do projeto
(banco, `set_updated_at()`, `prevent_hard_delete()` — db/002; permissão por
ação — db/011).

## 3. Tabelas

### 3.1 `product_categories` — Catálogo de categorias (RFC-COMISSION/RFC-002 §3.2)

| Coluna | Tipo | Regra | Definição |
|---|---|---|---|
| id | BIGSERIAL | PK | Identificador |
| code | TEXT | NOT NULL UNIQUE | Código único da categoria |
| description | TEXT | NOT NULL | Nome (ex.: "Eletrônicos", "Serviços", "Acessórios") |
| status | TEXT | DEFAULT 'ativo' CHECK ativo/inativo | Inativação lógica (padrão do projeto) |
| created_at / updated_at | TIMESTAMPTZ | DEFAULT now() | Auditoria; updated_at por trigger |

### 3.2 `products` — Catálogo de produtos do PDV (RFC-COMISSION/RFC-002 §2)

| Coluna | Tipo | Regra | Definição |
|---|---|---|---|
| id | BIGSERIAL | PK | Identificador |
| code | TEXT | NOT NULL UNIQUE | Código do produto |
| description | TEXT | NOT NULL | Descrição (ex.: "Celular Modelo X") |
| category_id | BIGINT | NOT NULL FK → product_categories | Todo produto pertence a uma categoria (RFC-COMISSION/RFC-002 §3.2 regra 1) |
| status | TEXT | DEFAULT 'ativo' CHECK ativo/inativo | Inativação lógica |
| created_at / updated_at | TIMESTAMPTZ | DEFAULT now() | Auditoria |

### 3.3 `commission_rules` — Regras de comissão (RFC-COMISSION/RFC-002 §3)

| Coluna | Tipo | Regra | Definição |
|---|---|---|---|
| id | BIGSERIAL | PK | Identificador |
| employee_id | BIGINT | NOT NULL FK → employees | Vendedor que recebe a comissão (RFC-002 (projeto) — Folha) |
| product_id | BIGINT | FK → products (NULL p/ categoria/padrão) | Produto específico (precedência máxima) |
| category_id | BIGINT | FK → product_categories (NULL p/ produto/padrão) | Categoria (precedência média) |
| rate_percent | NUMERIC(5,2) | NOT NULL CHECK 0–100 | Taxa percentual (ex.: 2,50 = 2,5%) |
| valid_from / valid_until | DATE | CHECK valid_until ≥ valid_from | Vigência (venda usa a regra vigente na data da venda) |
| status | TEXT | DEFAULT 'ativo' CHECK ativo/inativo | Inativação lógica |
| created_at / updated_at | TIMESTAMPTZ | DEFAULT now() | Auditoria |

**Constraints de negócio:**

1. `ck_rule_target_exclusive` — uma regra mira **produto** OU **categoria** OU
   **nenhum** (taxa padrão), nunca os dois:
   ```sql
   CHECK (NOT (product_id IS NOT NULL AND category_id IS NOT NULL))
   ```
2. `ck_rule_validity` — vigência coerente (padrão do RFC-004 (projeto)).
3. **Índices únicos parciais** — **uma regra ATIVA por (funcionário × alvo)**
   em cada nível, sem conflito entre níveis; regras **inativas** ficam como
   histórico (versionamento por vigência — RFC-COMISSION/RFC-002 §5 regra 3):
   ```sql
   CREATE UNIQUE INDEX uq_commission_rules_product
       ON commission_rules (employee_id, product_id)
       WHERE product_id IS NOT NULL AND status = 'ativo';
   CREATE UNIQUE INDEX uq_commission_rules_category
       ON commission_rules (employee_id, category_id)
       WHERE category_id IS NOT NULL AND status = 'ativo';
   CREATE UNIQUE INDEX uq_commission_rules_default
       ON commission_rules (employee_id)
       WHERE product_id IS NULL AND category_id IS NULL AND status = 'ativo';
   ```
   O funcionário pode ter, ao mesmo tempo, **uma regra ativa** de produto,
   **uma regra ativa** de categoria e **uma taxa padrão ativa** — cada uma no
   seu nível. **Versionar uma taxa** = inativar a regra atual (histórico
   preservado — inativação lógica, nunca exclusão física) e criar a nova regra
   com a nova vigência. A consulta de resolução (§5) usa apenas regras
   `ativo`, coerente com a regra "a taxa da data da venda"
   (RFC-COMISSION/RFC-002 §5 regra 3).

## 4. Regras de Integridade (triggers)

1. **Permissão por ação** — escrever em qualquer uma das três tabelas exige a
   ação `manter_cadastros` da matriz RFC-009 §3.1 (via db/011
   `f_has_permission_guc`, fail-closed):
   ```sql
   SET app.actor_roles = 'OPERADOR';
   ```
2. **Sem exclusão física** — DELETE/TRUNCATE bloqueados por trigger (reusa
   `prevent_hard_delete` da db/002): categoria/produto/regra **inativa**, nunca
   apaga (preserva histórico — RFC-008 (projeto) decisão 4).
3. **updated_at automático** — trigger `set_updated_at` nas três tabelas.

## 5. Consulta de Precedência (referência)

A taxa aplicada a um item vendido se resolve por precedência
(produto → categoria → padrão), usando a regra **ativa e vigente na data da venda**:

```sql
-- :emp = funcionário, :prod = produto vendido, :cat = categoria do produto,
-- :sale_date = data da venda
SELECT COALESCE(
    (SELECT rate_percent FROM commission_rules
      WHERE employee_id = :emp AND product_id = :prod
        AND status = 'ativo'
        AND (valid_from  IS NULL OR valid_from  <= :sale_date)
        AND (valid_until IS NULL OR valid_until >= :sale_date)),
    (SELECT rate_percent FROM commission_rules
      WHERE employee_id = :emp AND category_id = :cat
        AND status = 'ativo'
        AND (valid_from  IS NULL OR valid_from  <= :sale_date)
        AND (valid_until IS NULL OR valid_until >= :sale_date)),
    (SELECT rate_percent FROM commission_rules
      WHERE employee_id = :emp AND product_id IS NULL AND category_id IS NULL
        AND status = 'ativo'
        AND (valid_from  IS NULL OR valid_from  <= :sale_date)
        AND (valid_until IS NULL OR valid_until >= :sale_date)),
    0
) AS rate_percent;
-- comissão do item = valor de venda × rate_percent/100  (RFC-COMISSION/RFC-002 §4)
```

## 6. Migration SQL — `db/016_commission_module.sql`

A migration completa está em **`db/016_commission_module.sql`** (executável com
`psql -v ON_ERROR_STOP=1 -f db/016_commission_module.sql`), no padrão das demais
migrations do projeto:

- Cria `product_categories`, `products` e `commission_rules` + constraints.
- Cria os índices únicos parciais da precedência e os índices de consulta.
- Cria os triggers de permissão (`manter_cadastros`), de `updated_at` e de
  bloqueio de exclusão física (reuso de `set_updated_at`/`prevent_hard_delete`).
- **Pré-requisitos:** db/002 (employees, `set_updated_at`, `prevent_hard_delete`)
  e db/011 (permissões). Ordem de aplicação: `002 → 009 → 011 → ... → 016`.
- **Não cria** as tabelas de vendas/apuração do PDV (módulo comercial — fora do
  escopo, ver §7) nem altera `payroll_events` (o evento 7 já existe na db/010).

## 7. Escopo Fora Deste RFC

- Vendas do PDV, itens e vendedor por venda → RFC-COMISSION/RFC-005 (apuração;
  tabelas `pos_sales`/`pos_sale_items`/`commission_details`).
- Detalhamento da comissão no holerite (RFC-007 (projeto)) → apurado entra pelo evento 7
  (Comissão/Vendas, RFC-004 (projeto)).
- Taxa padrão global da empresa (não por funcionário) → RFC-COMISSION/RFC-008
  (tela própria + nova tabela `commission_global_rules`, db/018).

## 8. Decisões Aprovadas

1. **Três tabelas** — `product_categories`, `products` e `commission_rules`;
   o produto pertence a uma categoria e as regras referenciam funcionário,
   produto e/ou categoria. ✅ 05/08/2026
2. **Regra com alvo exclusivo** — uma regra mira produto OU categoria OU
   nenhum (taxa padrão), nunca os dois (`ck_rule_target_exclusive`). ✅ 05/08/2026
3. **Uma regra ATIVA por (funcionário × alvo) por nível** — índices únicos
   parciais com filtro `status = 'ativo'` impedem duplicidade de regra ativa em
   cada nível da precedência, permitindo os três níveis coexistirem para o
   mesmo funcionário; regras inativas ficam como histórico (versionamento por
   vigência — RFC-COMISSION/RFC-002 §5 regra 3). ✅ 05/08/2026
4. **Permissão via `manter_cadastros`** — escrita nas tabelas do módulo exige a
   ação da matriz RFC-009 §3.1 (fail-closed, padrão do projeto). ✅ 05/08/2026
5. **Inativação lógica, nunca exclusão física** — padrão RFC-008 (projeto) decisão 4
   aplicado às três tabelas. ✅ 05/08/2026

## 9. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| _em aberto_ | _autor_ | ⏳ | — |
