# RFC-004 — Eventos: Proventos e Descontos

| Campo | Valor |
|---|---|
| **Título** | Conceito de Evento: proventos, descontos e sua aplicação |
| **Autor** | crpalmarante |
| **Status** | ✅ Implementado (10/08/2026 — catálogo inicial com 19 eventos (RFC-004 §3) em gerir_eventos.cbl + cobol_bridge; tipos provento/desconto/informativo (§6 decisão 1); incidências INSS/IRRF/FGTS por evento (§5, ex.: Salário-Família não incide) e teto no desconto (§6 decisão 3); CRUD com bloqueio de código duplicado/tipo inválido e inativação lógica; aplicação por funcionário via estrutura_salarial.html; smoke_rfc004_eventos no CI) |
| **Data** | 31/07/2026 |
| **Versão** | 1.0.0 |
| **Área** | Conceitos — Folha |
| **Depende de** | RFC-001, RFC-002, RFC-005 |
| **Impacta** | RFC-006, RFC-007 |

---

## 1. Conceito

**Evento** é a menor unidade de crédito (provento) ou débito (desconto) que entra
na folha. Cada evento tem código, descrição, tipo e regras de cálculo próprias.
O **processamento** (RFC-006) aplica os eventos de cada funcionário e gera os
valores do holerite (RFC-007).

## 2. Estrutura de um Evento

| Campo | Definição |
|---|---|
| Código | Identificador numérico único do evento |
| Descrição | Nome exibido no holerite (ex.: "Salário Base") |
| Tipo | **Provento** (crédito) ou **Desconto** (débito) |
| Categoria | Ex.: remuneração, encargo, benefício, verba rescisória |
| Referência | A grandeza que alimenta o cálculo (ex.: horas, percentual, valor) |
| Fórmula / regra | Como o valor é calculado (ver 4) |
| Incidências | Se o valor **compõe base** de INSS, IRRF, FGTS (ver RFC-005) |
| Ordem de cálculo | Eventos com ordem relativa (ex.: calcular INSS antes do IRRF) |
| Uso | Mensal, rescisão, 13º, férias — ou todos |
| Vigência | Eventos podem ser criados/descontinuados por competência |

## 3. Catálogo Inicial de Eventos (Folha Mensal)

### 3.1 Proventos
| Código | Evento | Referência | Observação |
|---|---|---|---|
| 1 | Salário Base | Valor fixo | Principal provento do mensalista |
| 2 | Horas Extras 50% | Quantidade de horas | Sobre o valor da hora normal + 50% |
| 3 | Horas Extras 100% | Quantidade de horas | Domingos/feriados + 100% |
| 4 | Adicional Noturno | Horas noturnas / % | Horário 22h–5h |
| 5 | Adicional de Insalubridade | % sobre salário mínimo/base | 10/20/40% conforme grau |
| 6 | Adicional de Periculosidade | % sobre o salário base | 30% |
| 7 | Comissão / Vendas | Valor ou percentual | Conforme política |
| 8 | DSR (descanso semanal) | Reflexo de horas extras | Conforme legislação |
| 9 | Salário-Família | Quantidade de cotas | Conforme tabela (RFC-005) |
| 10 | Férias + 1/3 | Período | Em competência de férias |

### 3.2 Descontos
| Código | Evento | Referência | Observação |
|---|---|---|---|
| 20 | INSS | Automática | Tabela progressiva (RFC-005) |
| 21 | IRRF | Automática | Tabela progressiva (RFC-005) |
| 22 | Vale-Transporte | 6% do salário base | Somente se optante |
| 23 | Vale-Refeição | Valor ou % de participação | |
| 24 | Plano de Saúde | Valor da coparticipação | |
| 25 | Faltas / Atrasos | Quantidade (horas/dias) | Desconto sobre o valor do dia/hora |
| 26 | Adiantamento | Valor | Desconto do adiantamento feito |
| 27 | Pensão Alimentícia | % ou valor fixo | Conforme decisão judicial |
| 28 | Contribuição Sindical | Valor | Quando aplicável |

## 4. Regras de Cálculo por Evento

1. **Salário Base (1):** valor informado no cadastro do funcionário (RFC-002).
2. **Valor do dia** = salário base ÷ dias do mês (30) — usado para faltas.
3. **Valor da hora normal** = salário base ÷ carga horária mensal contratual.
4. **Horas Extras (2/3):** valor da hora × quantidade × (1 + percentual).
5. **INSS (20):** calculado sobre a **base INSS** (soma dos proventos que
   incidem INSS) conforme tabela progressiva do mês (RFC-005).
6. **IRRF (21):** calculado sobre a **base IRRF** (base INSS − INSS − dedução
   por dependente) conforme tabela progressiva (RFC-005).
7. **Vale-Transporte (22):** 6% do salário base, **limitado** ao valor de
   passagens informado (não pode ultrapassar o custo real do transporte).
8. **Ordem de cálculo:** proventos → base INSS → INSS → base IRRF → IRRF →
   demais descontos → líquido.

## 5. Incidências (composição de base)

Cada evento informa se **entra na base** de:
- **INSS** (ex.: salário, horas extras, adicional noturno, comissão)
- **IRRF** (quase tudo que entra no INSS, exceto isentos como salário-família)
- **FGTS** (a base FGTS normalmente = base INSS)

> Ex.: Salário-Família **não** incide INSS/IRRF/FGTS. Adicional de
> Periculosidade **incide** nas três bases. O detalhamento por evento é
> decisão de negócio registrada no cadastro do evento.

## 6. Decisões Aprovadas

1. **Evento informativo criado** — além de provento e desconto, existe o tipo
   "informativo" (exibido no holerite sem valor, ex.: faltas em quantidade). ✅ 31/07/2026
2. **Valor da hora por jornada contratual do funcionário** — usa a carga
   horária mensal do cadastro (RFC-002), não padrão fixo de 220h. ✅ 31/07/2026
3. **Teto no evento** — descontos com limite (ex.: VT 6%) carregam o teto no
   próprio evento e o cálculo o respeita. ✅ 31/07/2026

## 7. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| crpalmarante | autor | ✅ Aprovado | 10/08/2026 |
