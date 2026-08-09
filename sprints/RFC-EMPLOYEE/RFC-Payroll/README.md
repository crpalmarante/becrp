# RFC-Payroll — Série de RFCs do Módulo de Folha de Pagamento

> Pasta da **série RFC-Payroll**: documentos que especificam o **módulo de
> Folha de Pagamento (Payroll)** — cadastros, eventos, processamento, holerite,
> tabelas fiscais, encargos e movimentações — no mesmo padrão da série irmã
> `RFC-COMISSION/` (comissões do PDV).

---

## 1. Propósito da pasta

Reunir, em um único lugar, os RFCs **da folha** com numeração e qualificador
**próprios da série**, seguindo a convenção estabelecida pelo projeto:

| Pasta | Série | Escopo |
|---|---|---|
| `rfcs/` | RFC-00N (projeto central) | Especificações do núcleo da folha (001–016) |
| `RFC-COMISSION/` | RFC-COMISSION/00N | Módulo de comissões do PDV (001–008) |
| **`RFC-Payroll/`** | **RFC-Payroll/00N** | **Módulo de folha de pagamento (série própria)** |

A série **complementa** o mapa central (`docs-tecnicos/RFC-MAPA-encadeamento.md`)
e pode ser consultada em conjunto com o mapa detalhado da série irmã
(`RFC-COMISSION/RFC-MAPA-rastreabilidade.md`).

## 2. Convenção de numeração

1. **Numeração própria por série** — os arquivos seguem
   `RFC-Payroll/00N-titulo-descritivo.md` (ex.: `RFC-001-conceitos-gerais.md`),
   com números reiniciados em 001 dentro da série, **independentes** dos números
   dos RFCs do projeto central (`rfcs/`) e da série de comissões
   (`RFC-COMISSION/`).
2. **Qualificador explícito nas referências** — quando um documento citar um
   RFC da série, usa **`RFC-Payroll/00N`** (ex.: "RFC-Payroll/003"). Quando
   citar um RFC do **projeto central**, qualifica com `(projeto)` quando houver
   colisão de número (ex.: "RFC-003 (projeto)") — o mesmo padrão já aplicado na
   série RFC-COMISSION.
3. **Cabeçalho padrão** — todo RFC da série abre com a tabela de metadados do
   projeto: Título, Autor, Status (📝 Draft / ✅ aprovado), Data, Versão, Área,
   **Depende de** e **Impacta** (com os qualificadores acima).
4. **Numeração sequencial sem reuso** — um número usado não é reatribuído;
   RFCs evoluem por **versão** (ex.: 1.1.0), nunca por novo número.
5. **Mapa da série** — manter o
   `RFC-Payroll/RFC-MAPA-rastreabilidade.md` no padrão do mapa da RFC-COMISSION
   (conceito × documento × migration), ligando a série ao projeto central
   (já criado — cobre os RFC-Payroll 001–004).

## 3. Relação com o restante do repositório

- **`rfcs/`** — mantém os RFCs 001–016 do projeto central (fonte atual da
  folha). Se a série RFC-Payroll for adotada, a migração é **opcional** e deve
  preservar as referências qualificadas nos demais documentos.
- **`RFC-COMISSION/`** — série irmã; a folha **consome** o apurado de comissões
  pelo evento 7 (Comissão/Vendas) e a série RFC-Payroll deve referenciá-la como
  `RFC-COMISSION/00N`.
- **`docs-tecnicos/`** — diagramas e mapas do projeto central; o mapa de
  encadeamento (RFCs 001–016) ganhou as seções das séries RFC-COMISSION e
  RFC-Payroll (001–004).
- **`db/`** — as migrations (SQL puro) materializam as decisões dos RFCs; cada
  RFC da série que definir tabelas deve apontar a migration correspondente
  (ex.: `db/002`, `db/016`…).

## 4. Como criar um novo RFC na série

1. Copiar a estrutura do último RFC (ou de um da série irmã): cabeçalho,
   §1 Objetivo, §2 Conceito e Escopo, seções técnicas, §Decisões, §Aprovação.
2. Numerar com o **próximo número livre** da série e preencher `Depende de` /
   `Impacta` com os qualificadores da seção 2.
3. Atualizar o mapa da série (se existir) e as referências cruzadas
   (README.md, PLAN_ERP.md, mapa central) quando a numeração mudar.

---

*Criado em 05/08/2026. Pasta criada para receber a série RFC-Payroll —
**RFC-Payroll/001** (contabilização da folha — modelo de dados e funcionalidades,
v1.2.0, ✅ Aprovado), **RFC-Payroll/002** (fluxos de contabilização — geração
do lançamento e estorno, v1.1.0, ✅ Aprovado), **RFC-Payroll/003**
(contabilização da comissão — evento 7, v1.0.0, ✅ Aprovado) e
**RFC-Payroll/004** (detalhamento contábil por venda de origem no lançamento,
v1.1.0, ✅ Aprovado), cobertos pelo
**RFC-Payroll/RFC-MAPA-rastreabilidade.md**.*
