# RFC-006 — Tela de Cadastro de Produtos e Regras de Comissão por Produto

| Campo | Valor |
|---|---|
| **Título** | Cadastro de produtos e regras de comissão por produto (tela) |
| **Autor** | crpalmarante |
| **Status** | 📝 Draft (em revisão) |
| **Data** | 05/08/2026 |
| **Versão** | 1.0.0 |
| **Área** | Módulo — Comissões / PDV (interface) |
| **Depende de** | RFC-COMISSION/RFC-002 (regras do módulo), RFC-COMISSION/RFC-003 (modelo de dados + db/016), RFC-COMISSION/RFC-004 (tela de categorias/regras por categoria — base do módulo de cadastro) |
| **Impacta** | RFC-COMISSION/RFC-005 (apuração/vendas), RFC-007 (projeto — holerite), RFC-015 (projeto — relatórios) |

> **Natureza deste documento:** descreve a **tela de cadastro** dos **produtos**
> do catálogo e das **regras de comissão por produto** — campos, fluxos,
> validações e permissões — do módulo de comissões do PDV. Complementa o
> RFC-COMISSION/RFC-002 (regras de negócio) e o RFC-COMISSION/RFC-003 (modelo
> de dados), e **formaliza a evolução declarada no RFC-COMISSION/RFC-004**
> (§2/§7: "tela de produtos e regras por produto documentada à parte"), sem
> repetir o conteúdo deles.

---

## 1. Objetivo

Permitir ao gestor **cadastrar os produtos** do catálogo de vendas e
**personalizar comissões por produto específico** com facilidade, em uma tela
simples: criar/editar produtos e definir, para cada funcionário, a **taxa
percentual** aplicada **àquele produto** — a forma mais específica da
precedência, sem fórmulas manuais e sem depender apenas da taxa da categoria.

## 2. Conceito e Escopo

| Conceito | Definição |
|---|---|
| **Produto** | Item do catálogo de vendas que pode ter comissão própria (ex.: "Celular Modelo X", "Plano de serviço") (RFC-COMISSION/RFC-002 §2). |
| **Regra por produto** | Vínculo funcionário × produto × taxa percentual; aplica-se somente àquele produto (RFC-COMISSION/RFC-002 §3.1). |
| **Precedência** | Produto → categoria → taxa padrão: a regra de produto é a **precedência máxima** — vence a regra de categoria e a taxa padrão (RFC-COMISSION/RFC-002 §3.1). |
| **Vigência** | Período em que a regra é válida; a venda usa a regra vigente na data da venda (RFC-COMISSION/RFC-002 §5 regra 3). |

A tela cobre **duas abas complementares**:

1. **Produtos** — cadastro mestre do catálogo (tabela `products`).
2. **Regras por produto** — cadastro de `funcionário × produto × taxa`
   (tabela `commission_rules` com `product_id` preenchido e `category_id` NULL).

> A tela de **categorias** e das regras **por categoria** é o
> RFC-COMISSION/RFC-004; aqui o foco é o produto, mas a precedência com
> categoria e taxa padrão é respeitada no cálculo (RFC-COMISSION/RFC-003 §5).

## 3. Aba 1 — Cadastro de Produtos

### 3.1 Listagem

- Tabela com os produtos (código, descrição, categoria, situação).
- Ações por linha: **Editar**, **Inativar/Ativar** (inativação lógica —
  RFC-COMISSION/RFC-003 §4 regra 2; nunca exclusão física).
- Botão **"Novo Produto"** abre o formulário.

### 3.2 Formulário

| Campo | Obrigatório | Regra |
|---|---|---|
| Código | ✅ | Único (`code UNIQUE` da db/016); sugestão automática de código (ex.: prefixo + sequencial) |
| Descrição | ✅ | Nome exibido (ex.: "Celular Modelo X") |
| Categoria | ✅ | Seleção da lista de categorias **ativas** — todo produto pertence a uma categoria (RFC-COMISSION/RFC-002 §3.2 regra 1) |
| Situação | ✅ | Ativo / inativo — default "Ativo" |

Validações:
- Código duplicado → bloqueado (constraint da db/016).
- **Inativar com regras ativas** → aviso: "Este produto possui N regras de
  comissão ativas. Deseja inativar também as regras?" — as regras do produto
  seguem a inativação em cascata lógica (confirmação obrigatória).

## 4. Aba 2 — Regras de Comissão por Produto

### 4.1 Listagem

- Tabela das regras com: **Funcionário, Produto, Taxa (%), Vigência,
  Situação**.
- Filtros: por produto, por funcionário, por situação.
- Ações por linha: **Editar**, **Inativar/Ativar**.
- Botão **"Nova Regra por Produto"**.

### 4.2 Formulário

| Campo | Obrigatório | Regra |
|---|---|---|
| Funcionário | ✅ | Seleção da lista de funcionários ativos (RFC-002 (projeto) — Folha); busca por nome/CPF |
| Produto | ✅ | Seleção da lista de produtos **ativos** |
| Taxa percentual | ✅ | 0–100 (constraint `rate_percent` da db/016); máscara de percentual |
| Vigência inicial | ✅ | Data da vigência; default = hoje |
| Vigência final | 🔸 | Opcional; se informada, ≥ inicial (constraint `ck_rule_validity`) |
| Situação | ✅ | Ativa / inativa — default "Ativa" |

Validações:
- **Duplicidade** → bloqueada pela constraint da db/016: já existe regra de
  produto **ativa** para o mesmo (funcionário × produto) — a tela exibe
  mensagem clara apontando a regra existente (índice único parcial
  `uq_commission_rules_product` com filtro `status = 'ativo'`).
- **Versionamento por vigência** → para mudar a taxa de um funcionário ×
  produto, o gestor **inativa a regra atual** e cria a nova regra com a nova
  vigência — o banco garante uma única regra **ativa** por (funcionário ×
  produto), e a regra vigente na data da venda é a única aplicável
  (RFC-COMISSION/RFC-002 §5 regra 3).
- **Exclusividade de alvo** → o formulário de produto grava somente
  `product_id` (nunca produto + categoria juntos; `ck_rule_target_exclusive` da
  db/016).

### 4.3 Resumo visual da precedência

A tela de regras por produto mostra, para o funcionário selecionado, um
**resumo da precedência** (informativo, do RFC-COMISSION/RFC-002 §3.1):

```
Funcionário: Ana Silva
├── Regras de produto:  2 (Celular Modelo X — 5%, Plano de serviço — 4%)
├── Regras de categoria: 3 (Eletrônicos — 3%, Serviços — 4%, ...)
└── Taxa padrão:        1,5%
```

Ajuda o gestor a entender qual taxa será aplicada a cada item na venda do PDV —
e que a regra de produto, quando existir, **vence** as demais.

## 5. Fluxos

### 5.1 Criar regra por produto

1. Gestor abre a aba **Regras por produto** → **Nova Regra por Produto**.
2. Seleciona funcionário, produto e informa a taxa (ex.: 5%) e vigência.
3. Salvar → grava em `commission_rules` (product_id preenchido, category_id
   NULL) com a ação `manter_cadastros` (RFC-009 §3.1 via db/011 — ver §6).
4. A regra passa a valer para **aquele produto** na vigência, com **precedência
   máxima** sobre a categoria e a taxa padrão (RFC-COMISSION/RFC-002 §3.1).

### 5.2 Inativar produto com regras

1. Gestor inativa o produto "Celular Modelo X".
2. A tela avisa sobre as regras ativas vinculadas e pede confirmação.
3. Confirmando, produto e regras do produto inativam; o produto deixa de
   gerar comissão pela regra própria e passa a seguir a **regra da categoria**
   (se houver ativa) ou a **taxa padrão** do funcionário — precedência
   resolvida na consulta (RFC-COMISSION/RFC-003 §5).

## 6. Permissões e Auditoria

- **Escrita** (criar/editar/inativar produtos e regras) exige a ação
  `manter_cadastros` da matriz RFC-009 §3.1 (fail-closed via db/011
  `f_has_permission_guc`), no padrão das demais telas do projeto (incluindo o
  RFC-COMISSION/RFC-004 §6): `SET app.actor_roles = 'OPERADOR';`
- **Auditoria** — as operações de cadastro geram registros em `audit_log`
  (RFC-009 §5) com `action = 'manter_cadastros'` e contexto
  (`produto`/`regra`/`funcionario`/`taxa`), responsabilidade da camada de
  aplicação.
- **Leitura** (listagens/filtros) liberada aos papéis que operam a folha
  (OPERADOR, CONFERENTE, APROVADOR, ADMINISTRADOR), conforme a matriz.

## 7. Escopo Fora Deste RFC

- Regras de negócio e precedência → RFC-COMISSION/RFC-002.
- Modelo de dados e migration db/016 → RFC-COMISSION/RFC-003.
- Cadastro de categorias e regras por categoria → RFC-COMISSION/RFC-004.
- Apuração das vendas do PDV → RFC-COMISSION/RFC-005.
- Taxa padrão do funcionário (fallback) → tratada como regra com
  produto/categoria NULL (RFC-COMISSION/RFC-003 §3.3); tela própria no
  RFC-COMISSION/RFC-007.

## 8. Decisões Aprovadas

1. **Duas abas na mesma tela** — produtos e regras por produto convivem no
   mesmo módulo de cadastro, com filtros e navegação simples, no padrão do
   RFC-COMISSION/RFC-004. ✅ 05/08/2026
2. **Regra por produto é a precedência máxima** — o produto específico
   sobrescreve a regra da categoria e a taxa padrão (RFC-COMISSION/RFC-002
   §3.1); a tela deixa isso explícito no resumo da precedência (§4.3). ✅ 05/08/2026
3. **Inativação em cascata lógica** — inativar produto inativa as regras do
   produto (com confirmação e aviso), sem apagar nada (padrão RFC-008 (projeto)
   decisão 4). ✅ 05/08/2026
4. **Versionamento por vigência (uma regra ativa por funcionário × produto)**
   — mudar a taxa = inativar a atual e criar a nova com a nova vigência; a
   db/016 garante no banco uma única regra ativa por (funcionário × produto)
   (índice único parcial `uq_commission_rules_product` com `status = 'ativo'`),
   e a regra vigente na data da venda é a única aplicável
   (RFC-COMISSION/RFC-002 §5 regra 3). ✅ 05/08/2026
5. **Escrita com `manter_cadastros`** — cria/edita/inativa exige a ação da
   matriz RFC-009 §3.1 (fail-closed, padrão do projeto), idêntico ao
   RFC-COMISSION/RFC-004. ✅ 05/08/2026
6. **Sem nova migration** — o catálogo `products` e as regras por produto já
   estão materializados pela db/016 (RFC-COMISSION/RFC-003); este RFC especifica
   apenas a **interface**, sem alteração de schema. ✅ 05/08/2026

## 9. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| _em aberto_ | _autor_ | ⏳ | — |
