# RFC-008 — Tela de Cadastro da Taxa Padrão Global da Empresa (Fallback Final)

| Campo | Valor |
|---|---|
| **Título** | Cadastro da taxa padrão global da empresa (fallback final) (tela + db/018) |
| **Autor** | crpalmarante |
| **Status** | 📝 Draft (em revisão) |
| **Data** | 05/08/2026 |
| **Versão** | 1.0.0 |
| **Área** | Módulo — Comissões / PDV (interface + dados) |
| **Depende de** | RFC-COMISSION/RFC-002 (regras do módulo), RFC-COMISSION/RFC-003 (modelo de dados + db/016), RFC-COMISSION/RFC-007 (tela de taxa padrão do funcionário) |
| **Impacta** | RFC-COMISSION/RFC-002 (precedência), RFC-COMISSION/RFC-003 (consulta de resolução), RFC-COMISSION/RFC-005 (apuração/vendas), RFC-007 (projeto — holerite), RFC-015 (projeto — relatórios) |

> **Natureza deste documento:** descreve a **tela de cadastro da taxa padrão
> GLOBAL da empresa** — o percentual geral (fallback final) aplicado aos itens
> vendidos por funcionários **sem taxa padrão própria** — com campos, fluxos,
> validações, permissões e a **nova tabela `commission_global_rules` (db/018)**.
> **Formaliza a evolução declarada no RFC-COMISSION/RFC-003 §7 e no
> RFC-COMISSION/RFC-007 §6** ("taxa padrão global da empresa (não por
> funcionário) → evolução"), complementando o RFC-COMISSION/RFC-002 (regras de
> negócio) e o RFC-COMISSION/RFC-003 (modelo de dados), sem repetir o conteúdo
> deles.

---

## 1. Objetivo

Permitir ao gestor **definir a taxa percentual padrão GLOBAL da empresa** — o
percentual geral aplicado aos itens vendidos por funcionários que **não têm
regra de produto, nem de categoria, nem taxa padrão própria** — em uma tela
simples, com **um único valor vigente para toda a empresa**. É o **último nível
da precedência** (RFC-COMISSION/RFC-002 §3.1 + este RFC): quando existe, evita
que produtos sem regra específica deixem de gerar comissão mesmo para
funcionários sem configuração individual.

## 2. Conceito e Escopo

| Conceito | Definição |
|---|---|
| **Taxa padrão global** | Percentual geral da empresa aplicado a produtos sem regra de produto, de categoria ou taxa padrão do funcionário — o fallback final da precedência. |
| **Regra global** | Vínculo **empresa × taxa percentual** — **sem funcionário, sem produto e sem categoria**; **uma única regra ativa** por empresa (`commission_global_rules` + índice único parcial da db/018). |
| **Precedência** | Produto → categoria → taxa padrão do funcionário → **taxa padrão GLOBAL** → 0: a global é usada **apenas** quando não há regra de produto, nem de categoria, nem taxa padrão do funcionário. |
| **Vigência** | Período em que a regra é válida; a venda usa a regra vigente na data da venda (RFC-COMISSION/RFC-002 §5 regra 3). |

Diferente das telas por funcionário (RFC-COMISSION/RFC-004/006/007), esta tela
tem **um único registro ativo por empresa** (não por funcionário): o formulário
define a taxa da empresa inteira, e o histórico guarda as versões anteriores
(versionamento por inativação).

## 3. Tela — Taxa Padrão Global da Empresa

### 3.1 Listagem

- Cartão/registro único com: **Taxa (%), Vigência, Situação**.
- **Histórico** das versões anteriores (inativas) abaixo do registro atual.
- Ações: **Editar**, **Inativar/Ativar**.

### 3.2 Formulário

| Campo | Obrigatório | Regra |
|---|---|---|
| Taxa percentual | ✅ | 0–100 (constraint `rate_percent` da db/018); máscara de percentual |
| Vigência inicial | ✅ | Data da vigência; default = hoje |
| Vigência final | 🔸 | Opcional; se informada, ≥ inicial (constraint `ck_global_rule_validity`) |
| Situação | ✅ | Ativa / inativa — default "Ativa" |

Validações:
- **Duplicidade** → bloqueada pela constraint da db/018: já existe taxa padrão
  global **ativa** — a tela exibe mensagem clara apontando a regra existente
  (índice único parcial `uq_commission_global_default` com filtro
  `status = 'ativo'` — uma única ativa por empresa).
- **Versionamento por vigência** → para mudar a taxa global, o gestor
  **inativa a regra atual** e cria a nova regra com a nova vigência — o banco
  garante uma única regra **ativa** por empresa, e a regra vigente na data da
  venda é a única aplicável (RFC-COMISSION/RFC-002 §5 regra 3).
- **Sem funcionário** → a regra global não referencia funcionário (não há
  `employee_id` em `commission_global_rules`) — a taxa vale para toda a empresa.

### 3.3 Resumo visual da precedência

A tela mostra o **resumo da precedência** (informativo, do RFC-COMISSION/RFC-002
§3.1 + este RFC) para um funcionário sem regra específica:

```
Funcionário sem regra específica
├── Regra de produto:      (ex.: Celular Modelo X — 5%)
├── Regra de categoria:    (ex.: Eletrônicos — 3%)
├── Taxa padrão do funcionário: (ex.: 1,5%)
└── Taxa padrão GLOBAL da empresa: 1%   ← fallback final
```

## 4. Fluxos

### 4.1 Criar/alterar taxa padrão global

1. Gestor abre a tela de **Taxa padrão global**.
2. Informa a taxa (ex.: 1%) e a vigência.
3. Salvar → grava em `commission_global_rules` com a ação `manter_cadastros`
   (RFC-009 §3.1 via db/011 — ver §5).
4. A taxa passa a valer como **fallback final** para funcionários sem taxa
   padrão própria na vigência (consulta de resolução — ver §6).

### 4.2 Inativar taxa padrão global

1. Gestor inativa a taxa padrão global.
2. Confirmando, a regra inativa (histórico preservado — sem exclusão física).
3. A partir daí, funcionários sem regra específica **não geram comissão** (taxa
   resolvida = 0) — a tela avisa: "Funcionários sem regra deixarão de gerar
   comissão."

## 5. Permissões e Auditoria

- **Escrita** (criar/editar/inativar taxa padrão global) exige a ação
  `manter_cadastros` da matriz RFC-009 §3.1 (fail-closed via db/011
  `f_has_permission_guc`), no padrão das demais telas do módulo
  (RFC-COMISSION/RFC-004 §6 / RFC-COMISSION/RFC-006 §6 / RFC-COMISSION/RFC-007 §5):
  `SET app.actor_roles = 'OPERADOR';`
- **Auditoria** — as operações de cadastro geram registros em `audit_log`
  (RFC-009 §5) com `action = 'manter_cadastros'` e contexto (`taxa_global`),
  responsabilidade da camada de aplicação.
- **Leitura** (listagem/histórico) liberada aos papéis que operam a folha
  (OPERADOR, CONFERENTE, APROVADOR, ADMINISTRADOR), conforme a matriz.

## 6. Migration SQL — db/018 (nova tabela `commission_global_rules`)

A migration completa está em **`db/018_commission_global_rules.sql`**
(executável com `psql -v ON_ERROR_STOP=1 -f db/018_commission_global_rules.sql`),
no padrão das demais migrations do projeto:

| Coluna | Tipo | Regra | Definição |
|---|---|---|---|
| id | BIGSERIAL | PK | Identificador |
| rate_percent | NUMERIC(5,2) | NOT NULL CHECK 0–100 | Taxa percentual da empresa (ex.: 1,00 = 1%) |
| valid_from / valid_until | DATE | CHECK valid_until ≥ valid_from | Vigência (venda usa a regra vigente na data da venda) |
| status | TEXT | DEFAULT 'ativo' CHECK ativo/inativo | Inativação lógica |
| created_at / updated_at | TIMESTAMPTZ | DEFAULT now() | Auditoria; updated_at por trigger |

**Constraints de negócio:**

1. `ck_global_rule_validity` — vigência coerente (padrão do RFC-004 (projeto)).
2. **Índice único parcial** — **uma regra ATIVA por empresa**:
   ```sql
   CREATE UNIQUE INDEX uq_commission_global_default
       ON commission_global_rules ((true))
       WHERE status = 'ativo';
   ```
   Todas as linhas ATIVAS colidem na mesma chave (`true`), então no máximo uma
   existe por vez; regras **inativas** ficam como histórico (versionamento por
   vigência — RFC-COMISSION/RFC-002 §5 regra 3).

**Pré-requisitos e ordem:** db/002 (`set_updated_at`, `prevent_hard_delete`),
db/011 (permissões) e db/016 (`enforce_commission_write_permission` — a db/018
**reusa** os triggers de permissão, `updated_at` e bloqueio de exclusão física
das migrations anteriores). Ordem de aplicação:
`002 → 009 → 011 → 016 → 017 → 018`.

**Consulta de resolução estendida** (RFC-COMISSION/RFC-003 §5 + nível global) —
a taxa aplicada a um item vendido, na data da venda:

```sql
SELECT COALESCE(
    (SELECT rate_percent FROM commission_rules
      WHERE employee_id = :emp AND product_id = :prod AND status = 'ativo'
        AND (valid_from IS NULL OR valid_from <= :sale_date)
        AND (valid_until IS NULL OR valid_until >= :sale_date)),
    (SELECT rate_percent FROM commission_rules
      WHERE employee_id = :emp AND category_id = :cat AND status = 'ativo'
        AND (valid_from IS NULL OR valid_from <= :sale_date)
        AND (valid_until IS NULL OR valid_until >= :sale_date)),
    (SELECT rate_percent FROM commission_rules
      WHERE employee_id = :emp AND product_id IS NULL AND category_id IS NULL
        AND status = 'ativo'
        AND (valid_from IS NULL OR valid_from <= :sale_date)
        AND (valid_until IS NULL OR valid_until >= :sale_date)),
    (SELECT rate_percent FROM commission_global_rules
      WHERE status = 'ativo'
        AND (valid_from IS NULL OR valid_from <= :sale_date)
        AND (valid_until IS NULL OR valid_until >= :sale_date)),
    0
) AS rate_percent;
-- comissão do item = valor de venda × rate_percent/100 (RFC-COMISSION/RFC-002 §4)
```

## 7. Escopo Fora Deste RFC

- Regras de negócio e precedência → RFC-COMISSION/RFC-002.
- Modelo de dados por funcionário e migration db/016 → RFC-COMISSION/RFC-003.
- Cadastro de categorias e regras por categoria → RFC-COMISSION/RFC-004.
- Cadastro de produtos e regras por produto → RFC-COMISSION/RFC-006.
- Cadastro da taxa padrão do funcionário → RFC-COMISSION/RFC-007.
- Apuração das vendas do PDV → RFC-COMISSION/RFC-005.
- Taxa padrão por **filial/unidade** da empresa (uma por CNPJ) → evolução
  futura (mesma mecânica, com coluna de unidade).

## 8. Decisões Aprovadas

1. **Nova tabela `commission_global_rules` (db/018)** — a taxa padrão GLOBAL
   não cabe na `commission_rules` da db/016 (que exige `employee_id` NOT NULL —
   regra sempre por funcionário); a empresa precisa de um vínculo único
   empresa × taxa, sem funcionário. ✅ 05/08/2026
2. **Uma regra ATIVA por empresa** — o índice único parcial
   `uq_commission_global_default` (db/018) garante no máximo uma taxa global
   ativa, com versionamento por inativação (RFC-COMISSION/RFC-002 §5 regra 3).
   ✅ 05/08/2026
3. **Inativação lógica, nunca exclusão física** — padrão RFC-008 (projeto)
   decisão 4 aplicado à regra global (histórico preservado). ✅ 05/08/2026
4. **Escrita com `manter_cadastros`** — cria/edita/inativa exige a ação da
   matriz RFC-009 §3.1 (fail-closed, padrão do projeto), idêntico ao
   RFC-COMISSION/RFC-004/006/007. ✅ 05/08/2026
5. **4º nível da precedência** — a taxa global entra **abaixo** da taxa padrão
   do funcionário: produto → categoria → funcionário → global → 0; aplica-se
   apenas a funcionários **sem taxa padrão própria**. ✅ 05/08/2026

## 9. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| _em aberto_ | _autor_ | ⏳ | — |
