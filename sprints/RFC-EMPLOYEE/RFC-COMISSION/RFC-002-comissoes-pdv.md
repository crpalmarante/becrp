# RFC-002 — Módulo de Comissões no PDV (Ponto de Venda)

| Campo | Valor |
|---|---|
| **Título** | Módulo de comissões de vendas no PDV: cálculo e personalização por produto e categoria | 
| **Autor** | crpalmarante |
| **Status** | 📝 Draft (em revisão) |
| **Data** | 05/08/2026 |
| **Versão** | 1.2.0 |
| **Área** | Módulo — Comissões / PDV |
| **Depende de** | RFC-COMISSION/RFC-001 (Comissões de Vendas), RFC-002 (projeto — Cadastro de Funcionário) |
| **Impacta** | RFC-006 (projeto — Processamento), RFC-007 (projeto — Holerite) |

> **Natureza deste documento:** descreve o **módulo de comissões no ponto de
> venda (PDV)** — como o sistema calcula e personaliza comissões de vendas no
> PDV com facilidade, definindo comissões para os funcionários com base em
> **produtos específicos**, **categorias de produtos** e **taxas percentuais**.

---

## 1. Objetivo

Permitir **calcular e personalizar comissões de vendas no ponto de venda (PDV)**
de forma simples: o gestor define, para cada funcionário, a comissão sobre
**produtos específicos** e/ou **categorias de produtos** com **taxas percentuais**
próprias, e o sistema calcula automaticamente a comissão de cada venda realizada
no PDV.

## 2. Conceito

| Conceito | Definição |
|---|---|
| **PDV (Ponto de Venda)** | Onde as vendas são registradas (balcão, caixa, venda direta). Cada venda do PDV é a fonte da comissão. |
| **Produto** | Item do catálogo de vendas que pode ter comissão própria (ex.: celular, plano de serviço, acessório). |
| **Categoria de produto** | Agrupamento de produtos afins (ex.: Eletrônicos, Serviços, Acessórios) que compartilham uma mesma taxa de comissão (ver §3.2). |
| **Taxa percentual** | Percentual de comissão aplicado sobre o valor do produto vendido (ex.: 2%, 5%). |
| **Regra de comissão** | Vínculo entre funcionário × produto (ou categoria) × taxa percentual (ver §3). |
| **Comissão do PDV** | Valor gerado automaticamente pela venda no PDV, com base nas regras configuradas. |

## 3. Personalização por Funcionário, Produto e Categoria

O coração do módulo é a **regra de comissão** — combinação que define o
percentual aplicado a um funcionário sobre um **produto** ou uma **categoria**:

| Campo | Definição |
|---|---|
| Funcionário | O vendedor que recebe a comissão (referência ao RFC-002 (projeto)) |
| Produto | Produto específico sobre o qual a comissão incide (regra por produto) |
| Categoria | Categoria de produto sobre a qual a comissão incide (regra por categoria) |
| Taxa percentual | Percentual aplicado sobre o valor de venda do produto |
| Vigência | Data inicial (e opcionalmente final) da regra |
| Situação | Ativa / inativa |

### 3.1 Formas de definição

1. **Por produto específico** — o produto X paga 5% ao funcionário A.
2. **Por categoria de produto** — todos os produtos da categoria "Eletrônicos"
   pagam 3% ao funcionário A (ver §3.2).
3. **Taxa padrão do funcionário** — percentual geral aplicado a produtos sem
   regra específica (fallback).

> **Precedência:** regra de **produto específico** vence a regra de **categoria**,
> que vence a **taxa padrão** do funcionário; abaixo dela entra a **taxa padrão
> GLOBAL da empresa** (evolução — RFC-COMISSION/RFC-008). Se nenhuma existir, o
> produto não gera comissão (ou usa a política do RFC-COMISSION/RFC-001,
> conforme decisão do gestor).

### 3.2 Comissão por Categoria de Produto

A **categoria de produto** permite configurar uma única taxa para um grupo inteiro
de produtos, sem precisar criar uma regra para cada item. É a forma recomendada
quando muitos produtos pagam a mesma comissão.

**Catálogo de categorias (cadastro mestre):**

| Campo | Definição |
|---|---|
| Código | Identificador único da categoria |
| Descrição | Nome da categoria (ex.: "Eletrônicos", "Serviços", "Acessórios") |
| Situação | Ativa / inativa |

**Regra por categoria (funcionário × categoria × taxa):**

| Campo | Definição |
|---|---|
| Funcionário | O vendedor que recebe a comissão (RFC-002 (projeto)) |
| Categoria | Categoria de produto coberta pela regra |
| Taxa percentual | Percentual aplicado sobre o valor de venda de **todos** os produtos da categoria |
| Vigência | Data inicial (e opcionalmente final) da regra |
| Situação | Ativa / inativa |

Regras da categoria:

1. **Todo produto pertence a uma categoria** — o produto herda automaticamente a
   taxa da sua categoria, salvo regra de produto específico (precedência §3.1).
2. **A categoria permite taxas diferentes por funcionário** — a taxa é definida
   por vendedor; dois vendedores podem ter percentuais distintos na mesma
   categoria.
3. **Mudança de taxa da categoria vale para o catálogo inteiro** — ao ajustar a
   taxa, todos os produtos da categoria passam a usar o novo percentual (com
   vigência, respeitando vendas já feitas).
4. **Produto pode ter taxa própria dentro da categoria** — o produto específico
   sobrescreve a taxa da categoria (ex.: celular flagship 5% numa categoria de
   3%).

## 4. Cálculo no PDV

1. **Venda registrada no PDV** → o sistema identifica os itens (produtos) e o
   vendedor responsável.
2. Para cada item, busca a regra de comissão do vendedor (precedência do §3.1).
3. **Comissão do item** = valor de venda do item × taxa percentual da regra.
4. A comissão total da venda = soma das comissões dos itens (inclusive DSR,
   conforme RFC-COMISSION/RFC-001 §7.1).
5. O valor apurado no período alimenta o **evento Comissão / Vendas** (código 7,
   RFC-004 (projeto)) no processamento da folha (RFC-006 (projeto)).

### 4.1 Exemplo numérico

| Item da venda | Valor | Regra | Comissão |
|---|---|---|---|
| Celular Modelo X | R$ 2.000,00 | Funcionário A × produto X × 5% | R$ 100,00 |
| Plano de serviço | R$ 500,00 | Funcionário A × categoria Serviços × 3% | R$ 15,00 |
| Acessório (sem regra) | R$ 100,00 | — (taxa padrão 0%) | R$ 0,00 |
| **Total da venda** | **R$ 2.600,00** | | **R$ 115,00** |

## 5. Regras do Módulo

1. **Personalização fácil** — o gestor cadastra a regra (funcionário + produto
   ou categoria + taxa) em uma tela simples; nada de fórmulas manuais no PDV.
2. **Produtos sem regra não geram comissão** por padrão (ou caem na taxa da
   categoria / taxa padrão, configurável).
3. **Alteração de regra tem vigência** — a venda usa a regra vigente na data da
   venda (consistente com RFC-COMISSION/RFC-002 §3 e RFC-005 (projeto)).
4. **Comissão do PDV é provento** — entra na folha pelo evento Comissão/Vendas
   e segue as incidências do RFC-COMISSION/RFC-001 §6 (INSS/IRRF/FGTS).
5. **Rastreabilidade** — o holerite (RFC-007 (projeto)) apresenta a comissão como o
   evento Comissão/Vendas **consolidado por competência** (uma entrada por
   evento — db/015 `payroll_entries`, `UNIQUE (stub_id, event_id)`). O
   detalhamento **por venda de origem** (funcionário, produto, taxa aplicada)
   é a consulta de `commission_details` por funcionário × competência —
   RFC-COMISSION/RFC-005 (tabela própria na apuração).

## 6. Escopo Fora Deste RFC

- Política de comissão ampla, metas e faixas → RFC-COMISSION/RFC-001.
- Cadastro de funcionário → RFC-002 (projeto — Folha).
- Eventos e incidências → RFC-004 (projeto), RFC-005 (projeto).
- Processamento e holerite → RFC-006 (projeto), RFC-007 (projeto).

## 7. Decisões Aprovadas

1. **Comissão por produto com taxa percentual** — a 1ª versão define comissão
   por produto específico com taxa percentual; valor fixo por produto fica para
   evolução. ✅ 05/08/2026
2. **Comissão por categoria de produto** — a 1ª versão também define comissão por
   categoria, com taxa única aplicada a todos os produtos da categoria e
   personalização por funcionário. ✅ 05/08/2026
3. **Precedência produto → categoria → taxa padrão** — regra mais específica
   sempre vence; taxa padrão como fallback opcional. ✅ 05/08/2026
4. **Venda do PDV é a fonte da comissão** — com o módulo em uso, a comissão é
   apurada automaticamente das vendas registradas no PDV, sem digitação manual
   de valores; **antes** de o módulo existir, a entrada é manual/importação
   (RFC-COMISSION/RFC-001 decisão 1). ✅ 05/08/2026
5. **Integração com a folha via evento 7** — o apurado do período alimenta o
   evento Comissão/Vendas do processamento mensal (RFC-006 (projeto)), com as incidências
   do RFC-COMISSION/RFC-001. ✅ 05/08/2026

## 8. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| _em aberto_ | _autor_ | ⏳ | — |
