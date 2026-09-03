# RFC-005 — Tabelas Fiscais: INSS e IRRF

| Campo | Valor |
|---|---|
| **Título** | Conceito de tabelas fiscais: INSS, IRRF e salário-família |
| **Autor** | crpalmarante |
| **Status** | ✅ Implementado (10/08/2026) |
| **Data** | 31/07/2026 |
| **Versão** | 1.0.0 |
| **Área** | Conceitos — Folha |
| **Depende de** | RFC-001, RFC-004 |
| **Impacta** | RFC-006, RFC-007 |

---

## 1. Conceito

**Tabela fiscal** é o parâmetro oficial (governo) ou interno (empresa) usado no
cálculo da folha, **versionado por competência**. O processamento (RFC-006) usa
sempre a tabela vigente no mês da folha — nunca a tabela do dia do cálculo, se
houver atraso.

## 2. Tabela INSS (empregado)

Desconto **progressivo** sobre a base INSS (soma dos proventos que incidem INSS
— RFC-004). O valor devido é a soma das parcelas de cada faixa.

| Conceito | Definição |
|---|---|
| Faixas | Intervalos de salário-de-contribuição (ex.: até X; de X até Y; de Y até Z; acima de Z) |
| Alíquota | Percentual aplicado a **cada faixa** (cálculo progressivo por faixa) |
| Teto | Limite máximo de salário-de-contribuição |
| Competência | Vigência (mês/ano) da tabela |
| Base INSS | Valor de referência para a aplicação (vem dos eventos, RFC-004) |

### Exemplo conceitual (não oficial — ilustrativo)
| Faixa | Alíquota |
|---|---|
| Até R$ 1.500,00 | 7,5% |
| De 1.500,01 até 3.000,00 | 9% |
| De 3.000,01 até 5.000,00 | 12% |
| Acima de 5.000,00 | 14% |

> **Regra:** o desconto é a soma das alíquotas aplicadas em cada faixa
> (progressivo por faixa), **não** a alíquota única sobre o total.

## 3. Tabela IRRF (empregado)

Imposto **progressivo** sobre a base IRRF. A base IRRF = base INSS − INSS −
dedução por dependente (valor fixo por dependente, vigente na competência).

| Conceito | Definição |
|---|---|
| Faixas | Intervalos de base de cálculo |
| Alíquota | Percentual por faixa |
| Dedução | Parcela a deduzir da faixa (constante) — "dedução da faixa" |
| Dependentes | Valor dedutível por dependente |
| Isenção | Faixa em que não há imposto |
| Competência | Vigência da tabela |

### Exemplo conceitual (não oficial — ilustrativo)
| Faixa | Alíquota | Dedução da faixa |
|---|---|---|
| Até R$ 2.000,00 | Isento | — |
| De 2.000,01 até 4.000,00 | 10% | R$ 100,00 |
| De 4.000,01 até 6.000,00 | 15% | R$ 300,00 |
| Acima de 6.000,00 | 22,5% | R$ 700,00 |

> **Regra:** imposto = (base × alíquota da faixa) − dedução da faixa.

## 4. Tabela Salário-Família

Benefício pago ao empregado **de baixa renda** por dependente, dentro de faixas.

| Conceito | Definição |
|---|---|
| Faixa de salário | Limite para ter direito |
| Valor por cota | Valor por dependente |
| Cotas | Quantidade de dependentes elegíveis |
| Competência | Vigência |

## 5. Regras Gerais de Tabelas

1. **Toda tabela tem competência de vigência** — o cálculo da folha da
   competência X usa a tabela vigente em X.
2. **Tabelas são imutáveis após publicação/uso** — alteração gera nova versão
   com nova competência (nunca edita a usada em folha fechada).
3. **A fonte de atualização é manual/administrada** — o sistema não busca
   tabelas de lugar nenhum; a empresa cadastra os valores oficiais.
4. **Aplicação é progressiva por faixa** para INSS e IRRF — nunca alíquota única
   sobre o total (exceto onde a legislação disser o contrário).
5. **Valores monetários são exatos** — sem arredondamento intermediário que
   altere o resultado final do holerite.

## 6. Decisões Aprovadas

1. **Guardar todas as tabelas históricas** — cada versão por competência é
   preservada para recálculo e auditoria. ✅ 31/07/2026
2. **Tabelas internas genéricas** — a mesma mecânica de tabela serve para
   parâmetros internos (faixas de comissão, percentuais de benefício) além das
   fiscais. ✅ 31/07/2026
3. **Múltiplos tipos de dependência no IRRF** — a dedução por dependente aceita
   mais de um tipo de dependência. ✅ 31/07/2026

## 7. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| crpalmarante | autor | ✅ Aprovado | 10/08/2026 |
