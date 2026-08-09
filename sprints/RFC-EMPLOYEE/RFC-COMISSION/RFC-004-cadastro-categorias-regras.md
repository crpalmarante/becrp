# RFC-004 — Tela de Cadastro de Categorias e Regras de Comissão por Categoria

| Campo | Valor |
|---|---|
| **Título** | Cadastro de categorias de produto e regras de comissão por categoria (tela) |
| **Autor** | crpalmarante |
| **Status** | 📝 Draft (em revisão) |
| **Data** | 05/08/2026 |
| **Versão** | 1.1.0 |
| **Área** | Módulo — Comissões / PDV (interface) |
| **Depende de** | RFC-COMISSION/RFC-002 (regras do módulo), RFC-COMISSION/RFC-003 (modelo de dados + db/016) |
| **Impacta** | RFC-COMISSION/RFC-005 (apuração/vendas), RFC-COMISSION/RFC-006 (tela de produtos/regras por produto — complementar), RFC-COMISSION/RFC-007 (tela de taxa padrão — complementar), RFC-007 (projeto — holerite), RFC-015 (projeto — relatórios) |

> **Natureza deste documento:** descreve a **tela de cadastro** das categorias de
> produto e das **regras de comissão por categoria** — campos, fluxos, validações
> e permissões — do módulo de comissões do PDV. Complementa o RFC-COMISSION/RFC-002 (regras de
> negócio) e o RFC-COMISSION/RFC-003 (modelo de dados), sem repetir o conteúdo deles.

---

## 1. Objetivo

Permitir ao gestor **cadastrar e personalizar comissões por categoria de
produto** com facilidade, em uma tela simples: criar/editar categorias e definir,
para cada funcionário, a **taxa percentual** aplicada a **todos os produtos** da
categoria — sem fórmulas manuais e sem criar regra por produto individual.

## 2. Conceito e Escopo

| Conceito | Definição |
|---|---|
| **Categoria de produto** | Agrupamento de produtos afins (ex.: "Eletrônicos", "Serviços") que compartilha uma taxa de comissão (RFC-COMISSION/RFC-002 §3.2). |
| **Regra por categoria** | Vínculo funcionário × categoria × taxa percentual; aplica-se a todos os produtos da categoria (RFC-COMISSION/RFC-002 §3.2). |
| **Precedência** | Produto → categoria → taxa padrão: a regra de categoria é usada quando não há regra de produto específico (RFC-COMISSION/RFC-002 §3.1). |
| **Vigência** | Período em que a regra é válida; a venda usa a regra vigente na data da venda (RFC-COMISSION/RFC-002 §5 regra 3). |

A tela cobre **duas abas complementares**:

1. **Categorias** — cadastro mestre de categorias (tabela `product_categories`).
2. **Regras por categoria** — cadastro de `funcionário × categoria × taxa`
   (tabela `commission_rules` com `category_id` preenchido e `product_id` NULL).

> A tela de **produtos** e das regras **por produto** é documentada à parte
> (RFC-COMISSION/RFC-006); aqui o foco é a categoria, mas a
> precedência com produto é respeitada no cálculo (RFC-COMISSION/RFC-003 §5).

## 3. Aba 1 — Cadastro de Categorias

### 3.1 Listagem

- Tabela com as categorias (código, descrição, situação, nº de produtos).
- Ações por linha: **Editar**, **Inativar/Ativar** (inativação lógica — RFC-COMISSION/RFC-003
  §4 regra 2; nunca exclusão física).
- Botão **"Nova Categoria"** abre o formulário.

### 3.2 Formulário

| Campo | Obrigatório | Regra |
|---|---|---|
| Código | ✅ | Único (`code UNIQUE`); sugestão automática de código (ex.: prefixo + sequencial) |
| Descrição | ✅ | Nome exibido (ex.: "Eletrônicos") |
| Situação | ✅ | Ativo / inativo — default "Ativo" |

Validações:
- Código duplicado → bloqueado (constraint da db/016).
- **Inativar com regras ativas** → aviso: "Esta categoria possui N regras de
  comissão ativas. Deseja inativar também as regras?" — as regras da categoria
  seguem a inativação em cascata lógica (confirmação obrigatória).

## 4. Aba 2 — Regras de Comissão por Categoria

### 4.1 Listagem

- Tabela das regras com: **Funcionário, Categoria, Taxa (%), Vigência,
  Situação**.
- Filtros: por categoria, por funcionário, por situação.
- Ações por linha: **Editar**, **Inativar/Ativar**.
- Botão **"Nova Regra por Categoria"**.

### 4.2 Formulário

| Campo | Obrigatório | Regra |
|---|---|---|
| Funcionário | ✅ | Seleção da lista de funcionários ativos (RFC-002 (projeto) — Folha); busca por nome/CPF |
| Categoria | ✅ | Seleção da lista de categorias **ativas** |
| Taxa percentual | ✅ | 0–100 (constraint `rate_percent` da db/016); máscara de percentual |
| Vigência inicial | ✅ | Data da vigência; default = hoje |
| Vigência final | 🔸 | Opcional; se informada, ≥ inicial (constraint `ck_rule_validity`) |
| Situação | ✅ | Ativa / inativa — default "Ativa" |

Validações:
- **Duplicidade** → bloqueada pela constraint da db/016: já existe regra de
  categoria **ativa** para o mesmo (funcionário × categoria) — a tela exibe
  mensagem clara apontando a regra existente (índice único parcial com filtro
  `status = 'ativo'`).
- **Versionamento por vigência** → para mudar a taxa de um funcionário ×
  categoria, o gestor **inativa a regra atual** e cria a nova regra com a nova
  vigência — o banco garante uma única regra **ativa** por (funcionário ×
  categoria), e a regra vigente na data da venda é a única aplicável
  (RFC-COMISSION/RFC-002 §5 regra 3).
- **Exclusividade de alvo** → o formulário de categoria grava somente
  `category_id` (nunca produto + categoria juntos; `ck_rule_target_exclusive` da
  db/016).

### 4.3 Resumo visual da precedência

A tela de regras por categoria mostra, para o funcionário selecionado, um
**resumo da precedência** (informativo, do RFC-COMISSION/RFC-002 §3.1):

```
Funcionário: Ana Silva
├── Regras de produto:  2 (Celular Modelo X — 5%)
├── Regras de categoria: 3 (Eletrônicos — 3%, Serviços — 4%, ...)
└── Taxa padrão:        1,5%
```

Ajuda o gestor a entender qual taxa será aplicada a cada item na venda do PDV.

## 5. Fluxos

### 5.1 Criar regra por categoria

1. Gestor abre a aba **Regras por categoria** → **Nova Regra por Categoria**.
2. Seleciona funcionário, categoria e informa a taxa (ex.: 3%) e vigência.
3. Salvar → grava em `commission_rules` (categoria_id preenchido, produto_id
   NULL) com a ação `manter_cadastros` (RFC-009 §3.1 via db/011 — ver §6).
4. A regra passa a valer para **todos os produtos** da categoria na vigência.

### 5.2 Inativar categoria com regras

1. Gestor inativa a categoria "Eletrônicos".
2. A tela avisa sobre as regras ativas vinculadas e pede confirmação.
3. Confirmando, categoria e regras da categoria inativam; produtos da categoria
   continuam existindo (situação própria) e passam a seguir a **taxa padrão** do
   funcionário (não mais a da categoria inativa).

## 6. Permissões e Auditoria

- **Escrita** (criar/editar/inativar categorias e regras) exige a ação
  `manter_cadastros` da matriz RFC-009 §3.1 (fail-closed via db/011
  `f_has_permission_guc`), no padrão das demais telas do projeto:
  `SET app.actor_roles = 'OPERADOR';`
- **Auditoria** — as operações de cadastro geram registros em `audit_log`
  (RFC-009 §5) com `action = 'manter_cadastros'` e contexto
  (`categoria`/`regra`/`funcionario`/`taxa`), responsabilidade da camada de
  aplicação.
- **Leitura** (listagens/filtros) liberada aos papéis que operam a folha
  (OPERADOR, CONFERENTE, APROVADOR, ADMINISTRADOR), conforme a matriz.

## 7. Escopo Fora Deste RFC

- Regras de negócio e precedência → RFC-COMISSION/RFC-002.
- Modelo de dados e migration db/016 → RFC-COMISSION/RFC-003.
- Cadastro de produtos e regras por produto → RFC-COMISSION/RFC-006.
- Apuração das vendas do PDV → RFC-COMISSION/RFC-005.
- Taxa padrão do funcionário (fallback) → tratada como regra com
  produto/categoria NULL (RFC-COMISSION/RFC-003 §3.3); tela própria no
  RFC-COMISSION/RFC-007.

## 8. Decisões Aprovadas

1. **Duas abas na mesma tela** — categorias e regras por categoria convivem no
   mesmo módulo de cadastro, com filtros e navegação simples. ✅ 05/08/2026
2. **Regra por categoria é a forma recomendada** — quando muitos produtos pagam
   a mesma comissão, o gestor cadastra UMA regra de categoria (RFC-COMISSION/RFC-002 §3.2),
   evitando regras por produto. ✅ 05/08/2026
3. **Inativação em cascata lógica** — inativar categoria inativa as regras da
   categoria (com confirmação e aviso), sem apagar nada (padrão RFC-008 (projeto)
   decisão 4). ✅ 05/08/2026
4. **Versionamento por vigência (uma regra ativa por funcionário × categoria)**
   — mudar a taxa = inativar a atual e criar a nova com a nova vigência; a
   db/016 garante no banco uma única regra ativa por (funcionário × categoria)
   (índices únicos parciais com `status = 'ativo'`), e a regra vigente na data
   da venda é a única aplicável (RFC-COMISSION/RFC-002 §5 regra 3). ✅ 05/08/2026
5. **Escrita com `manter_cadastros`** — cria/edita/inativa exige a ação da
   matriz RFC-009 §3.1 (fail-closed, padrão do projeto). ✅ 05/08/2026

## 9. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| _em aberto_ | _autor_ | ⏳ | — |
