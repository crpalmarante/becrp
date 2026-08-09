# EXEMPLO — Competência Mensal com Horas Extras, Faltas e Dependente

> Exemplo numérico **completo e verificado** do processamento de uma competência
> mensal, ilustrando a cadeia de cálculo do RFC-006 (§3.2) com as tabelas
> ilustrativas do RFC-005.
> **Valores conferidos por script (Decimal, sem arredondamento intermediário).**
> Gerado em 01/08/2026 a partir dos RFCs 004, 005, 006 e 007.

---

## 1. Premissas

| # | Premissa | Valor | Origem |
|---|---|---|---|
| 1 | Salário base | R$ 4.500,00 | Cadastro do funcionário (RFC-002) |
| 2 | Carga horária mensal contratual | **220 h** *(assumida)* | RFC-004, decisão 2 (vem do cadastro, não é fixa) |
| 3 | Horas extras | **10 h a 50%** (evento 002) *(assumido)* | Lançamento variável (RFC-006 §3.1) |
| 4 | Faltas | **2 dias** (evento 025) *(assumido)* | Lançamento variável (RFC-006 §3.1) |
| 5 | Dependentes | **1** — dedução IRRF de **R$ 189,59** *(assumida)* | Parâmetro da tabela IRRF da competência (RFC-005 §3) |
| 6 | Tabelas INSS/IRRF | Ilustrativas do RFC-005 (**não oficiais**) | RFC-005 §2 e §3 |
| 7 | DSR reflexo (evento 008) | **Não incluído** (decisão do exemplo) | RFC-004, catálogo de eventos |
| 8 | Vale-transporte, plano de saúde, pensão | **Não incluídos** | Fora do escopo do exemplo |
| 9 | **Base FGTS = base INSS** (4.806,818182) | *Assumida* — incidências FGTS normalmente = incidências INSS | RFC-004 §5 |

> **Regra de ouro (RFC-005 §5.5):** sem arredondamento intermediário — apenas o
> resultado final do holerite é arredondado. Os valores intermediários abaixo
> são exibidos com precisão total.

---

## 2. Cálculo Passo a Passo (cadeia do RFC-006 §3.2)

### Etapa 1 — Proventos

```
Valor da hora normal = salário ÷ carga horária = 4.500 ÷ 220 = 20,454545…
HE 50%  = 20,454545… × 10 h × 1,5 = 306,818182

TOTAL PROVENTOS = 4.500,00 + 306,818182 = R$ 4.806,818182  →  R$ 4.806,82
```

### Etapa 2 — Base INSS

```
Soma dos proventos que incidem INSS (RFC-004 §5 — HE incide INSS):
BASE INSS = R$ 4.806,818182
```

### Etapa 3 — INSS (progressivo por faixa)

| Faixa | Base da faixa | Alíquota | Parcela |
|---|---|---|---|
| Até 1.500,00 | 1.500,00 | 7,5% | 112,50 |
| 1.500,01 – 3.000,00 | 1.500,00 | 9% | 135,00 |
| 3.000,01 – 5.000,00 | 4.806,818182 − 3.000 = 1.806,818182 | 12% | 216,818182 |
| Acima de 5.000,00 | — (base não atinge a faixa) | 14% | — |

> **Teto INSS não aplicável** — a base (4.806,82) está abaixo do limite máximo
> de salário-de-contribuição, então nenhuma faixa é limitada por teto.

```
INSS = 112,50 + 135,00 + 216,818182 = R$ 464,318182  →  R$ 464,32
```

### Etapa 4 — Base IRRF

```
BASE IRRF = base INSS − INSS − dedução por dependente
          = 4.806,818182 − 464,318182 − 189,59
          = R$ 4.152,91   →  enquadra na faixa de 15% (dedução 300)
```

### Etapa 5 — IRRF

```
IRRF = (4.152,91 × 15%) − 300 = 622,9365 − 300 = R$ 322,9365  →  R$ 322,94
```

### Etapa 6 — Demais descontos (faltas)

```
Valor do dia = salário ÷ 30 = 4.500 ÷ 30 = 150,00 (RFC-004 §4.2)
Faltas = 150,00 × 2 = R$ 300,00

TOTAL DESCONTOS = 464,318182 + 322,9365 + 300,00 = R$ 1.087,254682
```

### Etapa 7 — Líquido

```
LÍQUIDO = 4.806,818182 − 1.087,254682 = R$ 3.719,5635  →  R$ 3.719,56
```

---

## 3. Holerite (RFC-007)

```
┌────────────────────────────────────────────────────────────────┐
│  EMPRESA LTDA · CNPJ 00.000.000/0001-00                         │
│  Funcionário: Maria da Silva · Matrícula 0042                   │
│  Cargo: Analista · Depto: Financeiro · CPF 000.000.000-00       │
│  Admissão: 10/03/2023 · Competência: 08/2026                    │
├────────────────────────────────────────────────────────────────┤
│  CÓD  DESCRIÇÃO                 REFERÊNCIA    PROVENTOS         │
│  001  Salário Base              —             4.500,00          │
│  002  Horas Extras 50%          10,0 h          306,82          │
│  ── TOTAL DE PROVENTOS                        4.806,82          │
├────────────────────────────────────────────────────────────────┤
│  CÓD  DESCRIÇÃO                 REFERÊNCIA    DESCONTOS         │
│  020  INSS                       12% faixa       464,32          │
│  021  IRRF                       15% faixa       322,94          │
│  025  Faltas                     2,0 dias        300,00          │
│  ── TOTAL DE DESCONTOS                          1.087,26         │
├────────────────────────────────────────────────────────────────┤
│  BASES DE CÁLCULO                                             │
│  Base INSS: 4.806,82 · Base IRRF: 4.152,91 · Base FGTS: 4.806,82│
│  Salário de referência: 4.500,00                               │
├────────────────────────────────────────────────────────────────┤
│  LÍQUIDO A RECEBER                            3.719,56          │
│  Pagamento: Banco 001 · Ag 1234 · Conta 567890-1               │
└────────────────────────────────────────────────────────────────┘
```

**Conferência das invariantes do RFC-007 §3:**

- Total proventos = 4.500,00 + 306,82 = **4.806,82** ✓
- Total descontos = 464,32 + 322,94 + 300,00 = **1.087,26** ✓
- Líquido = 4.806,82 − 1.087,26 = **3.719,56** ✓

> **Convenção de arredondamento do holerite:** os totais exibidos são a **soma
> dos valores arredondados por evento** (proventos: 4.500,00 + 306,82 =
> 4.806,82; descontos: 464,32 + 322,94 + 300,00 = 1.087,26). No caso dos
> descontos o somatório com precisão total (1.087,254682) arredondado daria
> 1.087,25 — por isso o **líquido usa precisão total** (3.719,5635 → 3.719,56)
> e **não** o total arredondado, evitando divergência de centavos entre o
> holerite e o cálculo (regra do RFC-005 §5.5).

---

## 4. Notas de Fidelidade

1. **DSR reflexo (evento 008) não incluído** — o RFC-004 cataloga o DSR como
   provento (reflexo de HE em dias úteis); foi omitido **intencionalmente**
   neste exemplo para mantê-lo enxuto.
2. **Faltas não reduzem as bases no modelo do RFC** — a cadeia do RFC-006 §3.2
   calcula INSS/IRRF sobre a soma dos proventos e desconta faltas só na etapa
   11. Fiel ao RFC como escrito, mas na folha real as faltas reduziriam a
   remuneração e as bases (pro-rata). **Simplificação do modelo a registrar.**
3. **Dedução por dependente é parâmetro de tabela** (RFC-005 §3), versionada
   por competência — não deve ficar fixa no código. R$ 189,59 foi premissa.
4. **Tabelas ilustrativas** — os valores oficiais INSS/IRRF viriam da tabela da
   competência (RFC-005 §2/§3), cadastrada manualmente no sistema.

---

## 5. Referências Cruzadas

| Tema | RFC |
|---|---|
| Cadastro do funcionário (salário, carga horária, dependentes) | RFC-002 |
| Eventos e regras de cálculo (HE, faltas, incidências) | RFC-004 |
| Tabelas fiscais INSS/IRRF e regras de precisão | RFC-005 |
| Cadeia de cálculo e etapas do processamento | RFC-006 §3.2 |
| Estrutura e regras do holerite | RFC-007 |

*Exemplo gerado em 01/08/2026 — valores conferidos por script (Decimal).*
