# RFC-009 — Usuários, Papéis e Auditoria

| Campo | Valor |
|---|---|
| **Título** | Usuários, papéis, autorização e trilha de auditoria |
| **Autor** | crpalmarante |
| **Status** | ✅ Implementado (11/08/2026) |
| **Data** | 01/08/2026 |
| **Versão** | 1.0.0 |
| **Área** | Conceitos — Governança |
| **Depende de** | RFC-001 (Conceitos Gerais), RFC-006 (Processamento) |
| **Impacta** | RFC-006, RFC-013, RFC-015 |

---

## 1. Conceito

**Usuário** é a pessoa que opera o sistema. **Papel** é o conjunto de permissões
que define o que esse usuário pode fazer. **Auditoria** é o registro imutável de
toda mutação relevante, garantindo a rastreabilidade exigida pelo RFC-001
(regra 4: todo valor exibido deve ser rastreável).

## 2. Usuário

| Campo | Obrigatório | Observação |
|---|---|---|
| Login | ✅ | Identificador único de acesso |
| Nome | ✅ | |
| Papéis | ✅ | Um ou mais (ver 3) |
| Situação | ✅ | Ativo / inativo |
| Vínculo com funcionário | 🔸 | Se o operador também é funcionário da empresa |

## 3. Papéis

Papéis derivados das ações de estado do RFC-006 (seção 5) + administração.

| Papel | O que pode fazer |
|---|---|
| Operador | Lançar eventos variáveis, abrir competência, calcular |
| Conferente | Revisar e validar (estado "Validada") |
| Aprovador | Fechar a competência (estado "Fechada") |
| Tesouraria | Registrar pagamento (estado "Paga") |
| Administrador | Gerir usuários, cadastros mestres e tabelas |

### 3.1 Matriz de permissões por ação

| Ação | Operador | Conferente | Aprovador | Tesouraria | Admin |
|---|---|---|---|---|---|
| Abrir competência | ✅ | — | — | — | ✅ |
| Lançar eventos | ✅ | — | — | — | — |
| Calcular | ✅ | — | — | — | — |
| Validar | — | ✅ | — | — | — |
| Fechar | — | — | ✅ | — | — |
| Registrar pagamento | — | — | — | ✅ | — |
| Manter cadastros/tabelas | — | — | — | — | ✅ |
| Manter usuários | — | — | — | — | ✅ |

## 4. Regras de Autorização

1. **Toda ação de estado exige o papel correspondente** (RFC-006, regra 5).
2. **Separação de funções (moderada)** — o **Aprovador deve ser diferente do
   Operador** da competência (quem lança não fecha a própria folha). O
   **Conferente também deve ser diferente do Operador**, exceto quando acumular
   também o papel de **Aprovador** — nesse caso, a regra Aprovador ≠ Operador já
   garante a separação.
3. **Papéis são atribuídos por usuário** — um usuário pode ter múltiplos papéis,
   desde que respeitada a separação de funções na prática.
4. **Ações irreversíveis exigem confirmação explícita** — validar, fechar e pagar
   são ações conscientes, com registro em auditoria.

## 5. Auditoria

Toda mutação relevante é registrada com:

| Campo | Descrição |
|---|---|
| Quando | Data e hora |
| Quem | Usuário autenticado (ou "sistema" para ações automáticas) |
| O quê | Ação (lançar, calcular, validar, fechar, alterar cadastro, alterar tabela…) |
| Antes / depois | Estado anterior e posterior (valores alterados) |
| Contexto | Competência, funcionário, evento ou tabela afetados |

### 5.1 Regras da auditoria

1. **A trilha é imutável** — nenhum registro de auditoria pode ser editado ou
   apagado.
2. **O cálculo registra a versão das tabelas usadas** (RFC-005) — permite
   reproduzir o cálculo da competência.
3. **A auditoria cobre cadastros e tabelas**, não só o processamento — uma
   alteração de tabela sem processamento posterior deve ser rastreável.
4. **O holerite é a visão final** — da auditoria ao evento e ao cadastro
   (RFC-001, regra 4; RFC-007, regra 2).

## 6. Decisões Aprovadas

1. **Papéis fixos na 1ª versão** — sem criação de papéis customizados; a matriz
   acima é a tabela única de permissões. ✅ 01/08/2026
2. **Usuário pode ter múltiplos papéis**, respeitando a separação de funções na
   prática. ✅ 01/08/2026
3. **Auditoria obrigatória** para: lançamento, cálculo, mudança de estado,
   alteração de cadastro e de tabela. ✅ 01/08/2026
4. **Fechamento exige Aprovador ≠ Operador da competência** — separação de
   funções moderada; o Conferente pode acumular o papel de Aprovador, mas
   **nunca o de Operador** (Conferente ≠ Operador, exceto quando acumular
   Aprovador). ✅ 01/08/2026
5. **Pagamento exige Tesouraria ≠ Aprovador da competência** — quem registra
   o pagamento (estado "Paga") não pode ser o Aprovador que fechou a
   competência, tanto no pagamento da competência quanto no pagamento do
   holerite (que herda a competência). ✅ 11/08/2026

## 7. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| crpalmarante | _autor_ | ✅ Aprovado | 11/08/2026 |

---

## 8. Implementação (rastreabilidade)

| Item | Evidência |
|---|---|
| Trilha de auditoria imutável (append-only) | `folha_auditoria.py` → `dados/folha_auditoria.jsonl` (nunca reescreve/edita/apaga) |
| Auditoria de lançamento/cálculo/estado | `server.py` registra `abrir_competencia`, `calcular`, `concluir`, `validar`, `fechar`, `pagar`, `lancar` (férias/13º/rescisão), `alterar_cadastro` e `alterar_tabela` (config) com quando/quem/antes/depois/contexto |
| Auditoria dos cadastros mestres de RH | `alterar_cadastro` também cobre **funcionário, departamento, cargo e evento** (incluir/alterar/excluir) — `server.py` handlers `/api/departamento/*`, `/api/cargo/*`, `/api/evento/*` |
| Versão das tabelas no cálculo (RFC-005 §5.1.2) | `calcular` grava `tax_table_versions` na trilha (`folha_auditoria.versao_tabela_usada`) |
| Consulta da trilha | `GET /api/folha/auditoria?competencia=&acao=&quem=&limite=` (admin/instrutor) |
| Tela de auditoria | Aba **Auditoria** em `pages/folha.html` (filtros + antes/depois + tabelas) |
| Aprovador ≠ Operador no fechamento | `POST /api/folha/competencia/fechar` bloqueia quando o usuário é o Operador da competência (quem abriu/calculou) |
| Conferente ≠ Operador na validação | `POST /api/folha/competencia/validar` bloqueia quando o usuário é o Operador |
| Tesouraria ≠ Aprovador no pagamento | `POST /api/folha/competencia/pagar` e `POST /api/folha/holerite/pagar` bloqueiam quando o usuário é o Aprovador da competência (quem fechou) |
| Auditoria do holerite | `gerar_holerites`, `pagar_holerite` e `excluir_holerite` registrados na trilha com competência/holerite_id |
| Operador/Aprovador expostos na tela | `GET /api/folha/competencias` inclui `operador` e `aprovador` de cada competência (colunas na aba de competências) |
| CI | `scripts/smoke_rfc009_auditoria.py` (52 checks: trilha, regras de separação Aprovador/Conferente/Tesouraria, cadastros mestres, anexo no relatório, imutabilidade) + `review_tela_folha` com usuários aprovador e tesouraria |
