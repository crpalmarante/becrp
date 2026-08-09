# RFC-001 — Comissões de Vendas

| Campo | Valor |
|---|---|
| **Título** | Comissões de vendas: política, cálculo e reflexos na folha |
| **Autor** | crpalmarante |
| **Status** | 📝 Draft (em revisão) |
| **Data** | 05/08/2026 |
| **Versão** | 1.2.0 |
| **Área** | Conceitos — Folha |
| **Depende de** | RFC-001 (projeto), RFC-002 (projeto), RFC-004 (projeto), RFC-005 (projeto) |
| **Impacta** | RFC-006 (projeto), RFC-007 (projeto), RFC-010 (projeto), RFC-011 (projeto), RFC-COMISSION/RFC-002 (PDV), RFC-COMISSION/RFC-003 (dados) |

> **Natureza deste documento:** define **conceitos e regras de negócio** sobre
> comissões de vendas. Não trata de tecnologia, implementação ou ferramentas.
> Este RFC detalha o evento **Comissão / Vendas** (código 7 do catálogo do
> RFC-004 (projeto)).

---

## 1. Objetivo

Estabelecer como a comissão de vendas é **apurada, calculada e refletida** na
folha de pagamento: quais são os elementos de uma política de comissão, como o
valor da comissão entra no processamento mensal (RFC-006 (projeto)), quais são as
incidências (RFC-005 (projeto)) e quais os reflexos em DSR, férias e 13º salário.

## 2. Conceito

**Comissão** é a remuneração variável do funcionário calculada sobre o valor
das vendas (ou meta atingida) por ele realizadas em um período, conforme a
política comercial da empresa.

| Conceito | Definição |
|---|---|
| **Comissionado** | Funcionário cuja remuneração (total ou parcial) é composta por comissões. |
| **Política de comissão** | Conjunto de parâmetros que define como a comissão é calculada (ver §3). |
| **Precedência de taxa** | Ordem de resolução da taxa aplicada a um item vendido: **produto → categoria → taxa padrão** (módulo PDV — RFC-COMISSION/RFC-002 §3.1; modelada no RFC-COMISSION/RFC-003 §5). |
| **Período de apuração** | Intervalo em que as vendas são consideradas (normalmente o mês da competência). |
| **Venda elegível** | Venda que entra no cálculo (base), conforme regras da política (ex.: exclui cancelamentos, devoluções, vendas a prazo não liquidadas). |
| **Meta** | Valor (ou condição) cujo atingimento altera o percentual de comissão (opcional). |
| **DSR sobre comissão** | Reflexo do descanso semanal remunerado sobre a remuneração variável (ver §7.1). |

## 3. Estrutura de uma Política de Comissão

| Campo | Definição |
|---|---|
| Código | Identificador único da política |
| Descrição | Nome da política (ex.: "Vendas à vista — 2%", "Meta mensal escalonada") |
| Tipo de base | **Percentual sobre vendas** (ex.: 2% do valor vendido) ou **valor por unidade/faixa** |
| Percentual / faixas | Percentual único ou faixas escalonadas por meta (ex.: até 50.000 → 1,5%; acima → 2,5%) |
| Período de apuração | Mês de referência das vendas (competência) |
| Fonte do valor | Lançamento manual/importação (1ª versão) ou apuração automática no PDV (evolução) — ver §5 e decisões |
| Regras de elegibilidade | O que entra ou sai da base (cancelamentos, devoluções, comissão por recebimento) |
| Vigência | Políticas versionadas por competência, como as tabelas (RFC-005 (projeto)) |
| Reflexos | Se a comissão gera DSR, se compõe média para férias/13º (ver §7) |

> Cada comissionado pode ter **uma política** e/ou **percentual próprio**
> registrado no cadastro (RFC-002 (projeto)), prevalecendo o percentual do funcionário
> quando informado.
>
> **Precedência de taxa no módulo PDV** (RFC-COMISSION/RFC-002 §3.1): quando a
> comissão é apurada no ponto de venda, a taxa de um item vendido é resolvida
> na ordem **produto específico → categoria de produto → taxa padrão do
> funcionário** — a regra mais específica sempre vence. Essa precedência é
> materializada no banco pelo RFC-COMISSION/RFC-003 (índices únicos parciais em
> `commission_rules`, consulta de referência no §5).
>
> **Faixas escalonadas (evolução):** na 1ª versão, as regras do módulo PDV
> (RFC-COMISSION/RFC-003) aplicam **percentual único** por produto/categoria
> (`commission_rules.rate_percent`). Políticas com **faixas por meta** seguirão
> a mecânica de **tabelas internas genéricas** do RFC-005 (projeto — decisão 2 "faixas
> de comissão"), em evolução futura.

## 4. Regras de Cálculo

1. **Base da comissão** = soma das vendas elegíveis do período (descontados
   cancelamentos e devoluções), conforme a política.
2. **Comissão do mês** = base × percentual da política (ou do funcionário), ou
   resultado das faixas da meta quando escalonada.
3. **Comissão = provento variável** — entra como evento de provento (código 7,
   RFC-004 (projeto)) no processamento da competência (RFC-006 (projeto)).
4. **Adiantamento de comissão** — quando a empresa adianta parte da comissão
   durante o mês, o valor entra como **desconto de adiantamento** no
   processamento, abatendo a comissão devida (ajuste no holerite, RFC-007 (projeto)).
5. **Arredondamento** — o valor da comissão segue a mesma política de
   arredondamento dos demais eventos (centavos, padrão do projeto).
6. **Comissão negativa** — devoluções/cancelamentos que superem as vendas do
   período podem gerar comissão negativa; o tratamento (zerar ou abater) é
   decisão de negócio da política.

### 4.1 Exemplo numérico

- Política: 2% sobre vendas à vista do mês.
- Vendas elegíveis do mês: R$ 100.000,00 → Comissão = R$ 2.000,00.
- DSR (7.1): 2.000,00 ÷ 26 × 4 = R$ 307,69 (dia útil médio × domingos/feriados).
- **Total de proventos por comissão no mês: R$ 2.307,69.**

## 5. Apuração no PDV e Precedência de Taxa

1. **Fonte da comissão** — na 1ª versão, a comissão é **lançada manualmente ou
   importada** (valor da base de vendas do período); **com o módulo de PDV em
   uso** (RFC-COMISSION/RFC-002), cada venda registrada gera a comissão dos
   itens conforme as regras configuradas, sem digitação manual.
2. **Precedência produto → categoria → taxa padrão** — para cada item vendido,
   o sistema aplica a regra de **produto específico**; não havendo, a regra da
   **categoria** do produto; não havendo, a **taxa padrão** do funcionário
   (RFC-COMISSION/RFC-002 §3.1). Sem nenhuma regra, o produto não gera comissão.
3. **Vigência na data da venda** — a taxa usada é a da regra **ativa e vigente
   na data da venda** (RFC-COMISSION/RFC-003 §5).
4. **Alimenta a folha** — o valor apurado no período entra como evento
   **Comissão / Vendas** (código 7) no processamento da competência (RFC-006 (projeto)),
   seguindo as incidências da §6 abaixo.

## 6. Incidências (RFC-005 (projeto))

| Imposto/Encargo | Incide sobre a comissão? |
|---|---|
| **INSS** | ✅ Sim — comissão compõe a base INSS |
| **IRRF** | ✅ Sim — comissão compõe a base IRRF |
| **FGTS** | ✅ Sim — base FGTS acompanha a base INSS |

> O DSR sobre comissão também incide INSS/IRRF/FGTS. O detalhamento por evento
> é decisão de negócio registrada no cadastro do evento (RFC-004 (projeto) §5).

## 7. Reflexos na Remuneração

### 7.1 DSR sobre comissão

- A comissão variável gera reflexo de **Descanso Semanal Remunerado**.
- Fórmula de referência: DSR = comissão ÷ (dias úteis do mês) × (domingos e
  feriados do mês). O divisor exato segue a jurisprudência adotada (decisão de
  negócio — ver §9).

### 7.2 Férias (RFC-010)

- Comissões integram o **cálculo da média para férias** (média dos últimos 12
  meses de remuneração variável, conforme legislação) e o **1/3 constitucional**
  incide sobre o total.

### 7.3 13º Salário (RFC-011)

- Comissões integram o **13º salário pela média** do período aquisitivo,
  refletida na 1ª e 2ª parcela.

### 7.4 Rescisão (RFC-003 (projeto))

- Na rescisão, as comissões devidas e não pagas entram como **verbas
  rescisórias**, com reflexos em aviso prévio, férias proporcionais e 13º
  proporcional, conforme a média histórica.

## 8. Escopo Fora Deste RFC

- Cadastro de funcionários e percentual individual → RFC-002 (projeto).
- Catálogo de eventos → RFC-004 (projeto).
- Tabelas e incidências → RFC-005 (projeto).
- Processamento da folha → RFC-006 (projeto).
- Holerite → RFC-007 (projeto).
- Férias e 13º → RFC-010, RFC-011.
- Módulo de comissões no PDV (produto/categoria/taxa padrão) → RFC-COMISSION/RFC-002.
- Modelo de dados das regras de comissão → RFC-COMISSION/RFC-003.

## 9. Decisões Aprovadas

1. **Comissão é provento variável mensal** — apurada por competência, com
   lançamento manual ou importação do valor da base de vendas. **Fonte:** até o
   módulo de PDV existir (RFC-COMISSION/RFC-002), a comissão é lançada
   manualmente; depois, passa a ser apurada automaticamente pelas vendas do PDV
   (decisão RFC-COMISSION/RFC-002 nº 4). ✅ 05/08/2026
2. **DSR sobre comissão computado** — a 1ª versão calcula o reflexo de DSR no
   próprio processamento mensal, conforme §7.1. ✅ 05/08/2026
3. **Adiantamento de comissão como desconto** — quando houver adiantamento, ele
   é lançado como desconto no holerite e abate a comissão do mês. ✅ 05/08/2026
4. **Comissão negativa não zera automaticamente** — a regra de zerar/abater é
   configurável na política; padrão da 1ª versão: **abater** no mês seguinte. ✅ 05/08/2026
5. **Faixas por meta via tabela interna (evolução)** — na 1ª versão, percentual
   único por produto/categoria (RFC-COMISSION/RFC-003); faixas escalonadas por
   meta usarão a mecânica de tabelas internas do RFC-005 (projeto — decisão 2). ✅ 05/08/2026

## 10. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| _em aberto_ | _autor_ | ⏳ | — |
