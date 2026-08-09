# RFC-007 — Tela de Cadastro da Taxa Padrão do Funcionário (Fallback)

| Campo | Valor |
|---|---|
| **Título** | Cadastro da taxa padrão do funcionário (fallback) (tela) |
| **Autor** | crpalmarante |
| **Status** | 📝 Draft (em revisão) |
| **Data** | 05/08/2026 |
| **Versão** | 1.0.0 |
| **Área** | Módulo — Comissões / PDV (interface) |
| **Depende de** | RFC-COMISSION/RFC-002 (regras do módulo), RFC-COMISSION/RFC-003 (modelo de dados + db/016), RFC-COMISSION/RFC-004 (tela de categorias/regras por categoria), RFC-COMISSION/RFC-006 (tela de produtos/regras por produto) |
| **Impacta** | RFC-COMISSION/RFC-005 (apuração/vendas), RFC-COMISSION/RFC-008 (tela de taxa padrão global — complementar), RFC-007 (projeto — holerite), RFC-015 (projeto — relatórios) |

> **Natureza deste documento:** descreve a **tela de cadastro da taxa padrão do
> funcionário** — o percentual geral (fallback) aplicado aos itens vendidos sem
> regra de produto nem de categoria — com campos, fluxos, validações e
> permissões. **Formaliza a evolução declarada no RFC-COMISSION/RFC-004 §7 e no
> RFC-COMISSION/RFC-006 §7** ("tela própria pode vir em evolução"), complementando
> o RFC-COMISSION/RFC-002 (regras de negócio) e o RFC-COMISSION/RFC-003 (modelo
> de dados), sem repetir o conteúdo deles.

---

## 1. Objetivo

Permitir ao gestor **definir a taxa percentual padrão de cada funcionário** — o
percentual geral aplicado aos itens vendidos que **não têm regra de produto nem
regra de categoria** — em uma tela simples, sem fórmulas manuais e sem criar
regra por produto/categoria individual. É o **último nível da precedência**
(RFC-COMISSION/RFC-002 §3.1): quando existe, evita que produtos sem regra
específica deixem de gerar comissão.

## 2. Conceito e Escopo

| Conceito | Definição |
|---|---|
| **Taxa padrão do funcionário** | Percentual geral aplicado a produtos sem regra de produto nem de categoria — o fallback da precedência (RFC-COMISSION/RFC-002 §3.1). |
| **Regra padrão** | Vínculo funcionário × taxa percentual **sem produto e sem categoria** (`product_id` e `category_id` NULL — RFC-COMISSION/RFC-003 §3.3); uma única regra **ativa** por funcionário (`uq_commission_rules_default` da db/016). |
| **Precedência** | Produto → categoria → taxa padrão: a taxa padrão é usada **apenas** quando não há regra de produto nem de categoria (RFC-COMISSION/RFC-002 §3.1). |
| **Vigência** | Período em que a regra é válida; a venda usa a regra vigente na data da venda (RFC-COMISSION/RFC-002 §5 regra 3). |

Diferente das telas de categorias (RFC-COMISSION/RFC-004) e de produtos
(RFC-COMISSION/RFC-006) — que têm **duas abas** —, esta tela tem **uma única
aba**: a lista de regras padrão por funcionário (funcionário × taxa), sobre a
tabela `commission_rules` com `product_id` e `category_id` NULL.

## 3. Tela — Regras Padrão por Funcionário

### 3.1 Listagem

- Tabela das regras com: **Funcionário, Taxa (%), Vigência, Situação**.
- Filtros: por funcionário, por situação.
- Ações por linha: **Editar**, **Inativar/Ativar**.
- Botão **"Nova Taxa Padrão"**.

### 3.2 Formulário

| Campo | Obrigatório | Regra |
|---|---|---|
| Funcionário | ✅ | Seleção da lista de funcionários ativos (RFC-002 (projeto) — Folha); busca por nome/CPF |
| Taxa percentual | ✅ | 0–100 (constraint `rate_percent` da db/016); máscara de percentual |
| Vigência inicial | ✅ | Data da vigência; default = hoje |
| Vigência final | 🔸 | Opcional; se informada, ≥ inicial (constraint `ck_rule_validity`) |
| Situação | ✅ | Ativa / inativa — default "Ativa" |

Validações:
- **Duplicidade** → bloqueada pela constraint da db/016: já existe taxa padrão
  **ativa** para o mesmo funcionário — a tela exibe mensagem clara apontando a
  regra existente (índice único parcial `uq_commission_rules_default` com filtro
  `status = 'ativo'` e produto/categoria NULL).
- **Versionamento por vigência** → para mudar a taxa padrão de um funcionário, o
  gestor **inativa a regra atual** e cria a nova regra com a nova vigência — o
  banco garante uma única regra **ativa** por funcionário, e a regra vigente na
  data da venda é a única aplicável (RFC-COMISSION/RFC-002 §5 regra 3).
- **Exclusividade de alvo** → o formulário grava **somente** a taxa (produto e
  categoria NULL — `ck_rule_target_exclusive` da db/016), nunca junto com
  produto/categoria.

### 3.3 Resumo visual da precedência

A tela mostra, para o funcionário selecionado, o **resumo da precedência**
(informativo, do RFC-COMISSION/RFC-002 §3.1) — igual às telas de regras por
categoria (RFC-COMISSION/RFC-004 §4.3) e por produto (RFC-COMISSION/RFC-006
§4.3):

```
Funcionário: Ana Silva
├── Regras de produto:  2 (Celular Modelo X — 5%, Plano de serviço — 4%)
├── Regras de categoria: 3 (Eletrônicos — 3%, Serviços — 4%, ...)
└── Taxa padrão:        1,5%
```

## 4. Fluxos

### 4.1 Criar taxa padrão

1. Gestor abre a tela de **Taxa padrão** → **Nova Taxa Padrão**.
2. Seleciona funcionário e informa a taxa (ex.: 1,5%) e vigência.
3. Salvar → grava em `commission_rules` (product_id e category_id NULL) com a
   ação `manter_cadastros` (RFC-009 §3.1 via db/011 — ver §5).
4. A taxa passa a valer como **fallback** para os itens sem regra de
   produto/categoria na vigência (consulta RFC-COMISSION/RFC-003 §5).

### 4.2 Inativar taxa padrão

1. Gestor inativa a taxa padrão de um funcionário.
2. Confirmando, a regra inativa (histórico preservado — sem exclusão física).
3. A partir daí, produtos sem regra específica **não geram comissão** (taxa
   resolvida = 0, precedência RFC-COMISSION/RFC-002 §3.1) — a tela avisa:
   "Produtos sem regra deixarão de gerar comissão para este funcionário."

## 5. Permissões e Auditoria

- **Escrita** (criar/editar/inativar taxa padrão) exige a ação
  `manter_cadastros` da matriz RFC-009 §3.1 (fail-closed via db/011
  `f_has_permission_guc`), no padrão das demais telas do módulo
  (RFC-COMISSION/RFC-004 §6 / RFC-COMISSION/RFC-006 §6):
  `SET app.actor_roles = 'OPERADOR';`
- **Auditoria** — as operações de cadastro geram registros em `audit_log`
  (RFC-009 §5) com `action = 'manter_cadastros'` e contexto
  (`funcionario`/`taxa`), responsabilidade da camada de aplicação.
- **Leitura** (listagens/filtros) liberada aos papéis que operam a folha
  (OPERADOR, CONFERENTE, APROVADOR, ADMINISTRADOR), conforme a matriz.

## 6. Escopo Fora Deste RFC

- Regras de negócio e precedência → RFC-COMISSION/RFC-002.
- Modelo de dados e migration db/016 → RFC-COMISSION/RFC-003.
- Cadastro de categorias e regras por categoria → RFC-COMISSION/RFC-004.
- Cadastro de produtos e regras por produto → RFC-COMISSION/RFC-006.
- Apuração das vendas do PDV → RFC-COMISSION/RFC-005.
- Taxa padrão **global** da empresa (não por funcionário) → RFC-COMISSION/RFC-008
  (tela própria + nova tabela `commission_global_rules`, db/018).

## 7. Decisões Aprovadas

1. **Tela única de regra padrão** — diferentemente das telas de categorias e de
   produtos (duas abas), a taxa padrão é uma única lista de funcionário × taxa,
   sobre regras com produto/categoria NULL (RFC-COMISSION/RFC-003 §3.3).
   ✅ 05/08/2026
2. **Uma regra ATIVA por funcionário** — o índice único parcial
   `uq_commission_rules_default` (db/016) garante no máximo uma taxa padrão ativa
   por funcionário, com versionamento por inativação (RFC-COMISSION/RFC-002 §5
   regra 3). ✅ 05/08/2026
3. **Inativação lógica, nunca exclusão física** — padrão RFC-008 (projeto) decisão 4
   aplicado à regra padrão (histórico preservado). ✅ 05/08/2026
4. **Escrita com `manter_cadastros`** — cria/edita/inativa exige a ação da
   matriz RFC-009 §3.1 (fail-closed, padrão do projeto), idêntico ao
   RFC-COMISSION/RFC-004 e RFC-COMISSION/RFC-006. ✅ 05/08/2026
5. **Sem nova migration** — a taxa padrão já está materializada pela db/016
   (regra com produto/categoria NULL + `uq_commission_rules_default`); este RFC
   especifica apenas a **interface**, sem alteração de schema. ✅ 05/08/2026

## 8. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| _em aberto_ | _autor_ | ⏳ | — |
