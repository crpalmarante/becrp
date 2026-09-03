# RFC-014 — Encargos Patronais e FGTS

| Campo | Valor |
|---|---|
| **Título** | Encargos patronais: FGTS, INSS patronal, RAT e terceiros |
| **Autor** | crpalmarante |
| **Status** | ✅ Implementado (11/08/2026 — INSS patronal (20%), RAT/SAT e terceiros calculados no COBOL com alíquotas versionadas por competência (§5); encargos consolidados no fechamento (§4.4); regime Simples Nacional zera INSS patronal/RAT/terceiros (DAS, §3); lançamentos contábeis idempotentes; relatório de encargos HTML imprimível gerado no fechamento; smoke_rfc014_encargos + review_tela_folha no CI) |
| **Data** | 01/08/2026 |
| **Versão** | 1.0.0 |
| **Área** | Conceitos — Folha |
| **Depende de** | RFC-001, RFC-004, RFC-005, RFC-008 |
| **Impacta** | RFC-007, RFC-015 |

---

## 1. Conceito

**Encargos patronais** são as obrigações **do empregador** incidentes sobre a
folha — FGTS, INSS patronal, RAT/SAT e contribuições a terceiros. Eles **não
aparecem no holerite do funcionário** (RFC-007, decisão 1: encargos do
empregador ficam em relatório separado) — vão para o relatório de encargos
(RFC-015).

## 2. Encargos Cobertos

| Encargo | Percentual | Base | Observação |
|---|---|---|---|
| **FGTS** | 8% | Base FGTS (proventos que incidem FGTS — RFC-004) | Depósito mensal |
| **INSS patronal** | 20% | Base de encargos | Lucro real/presumido |
| **RAT/SAT** | 1%, 2% ou 3% | Base de encargos | Conforme CNAE (RFC-008) e risco da atividade |
| **Terceiros** | Variável (SESI/SENAI/SENAC etc.) | Base de encargos | Conforme atividade |
| **Multa FGTS rescisória** | 40% (sem justa causa) / 20% (acordo) | Saldo do FGTS | Ver RFC-003 |

## 3. Simples Nacional

Empresas optantes pelo **Simples Nacional** (RFC-008, regime tributário) têm
recolhimento unificado (DAS), **sem INSS patronal separado** na folha. O cálculo
dos encargos deve respeitar o regime tributário da empresa.

## 4. Regras do Processamento

1. **Base de encargos** = soma dos proventos que incidem FGTS/INSS patronal
   (incidências dos eventos — RFC-004).
2. **Tabelas de encargos são versionadas por competência** como as demais
   (RFC-005).
3. **O cálculo usa a tabela da competência**, não a do dia do processamento.
4. **Encargos são calculados no fechamento** da competência e consolidados em
   relatório próprio (RFC-015).
5. **Retroativos** (folha complementar — RFC-013) recalculam apenas a diferença.

## 5. Decisões Aprovadas

1. **1ª versão cobre FGTS (8%), INSS patronal (20%) e RAT/SAT por CNAE.**
   Contribuições a terceiros ficam como campo configurável ou evolução. ✅ 01/08/2026
2. **Regime tributário define o cálculo** — Simples Nacional não calcula INSS
   patronal separado. ✅ 01/08/2026
3. **Encargos NUNCA aparecem no holerite** — apenas no relatório de encargos
   (RFC-015). ✅ (decisão já aprovada no RFC-007)
4. **Relatório de encargos gerado no fechamento** da competência. ✅ 01/08/2026

## 6. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| crpalmarante | _autor_ | ✅ Aprovado | 11/08/2026 |
