# RFC-013 — Folha Complementar

| Campo | Valor |
|---|---|
| **Título** | Folha complementar: ajustes de competência fechada |
| **Autor** | crpalmarante |
| **Status** | 📝 Draft (em revisão) |
| **Data** | 01/08/2026 |
| **Versão** | 1.0.0 |
| **Área** | Conceitos — Processos |
| **Depende de** | RFC-001, RFC-006 |
| **Impacta** | RFC-006, RFC-007, RFC-009 |

---

## 1. Conceito

**Folha complementar** é a folha especial usada para **ajustar uma competência
já fechada** (RFC-006, regra 1: competência fechada é imutável). Ela **nunca
altera a folha original** — apenas registra diferenças (positivas ou negativas)
em uma competência própria de ajuste.

## 2. Quando Usar

| Situação | Exemplo |
|---|---|
| Lançamento esquecido | Hora extra não lançada na competência original |
| Erro de cálculo | Valor incorreto que já foi pago |
| Decisão judicial | Reajuste retroativo determinado pela justiça |
| Diferença de tabela | Tabela fiscal corrigida após o fechamento |

## 3. Regras do Processo

1. **A competência fechada permanece intocada** — a correção nunca é feita
   "na folha original".
2. **Toda folha complementar referencia a competência original** (mês/ano) e o
   motivo do ajuste.
3. **Usa o mesmo fluxo de estados** do processamento (RFC-006): aberta →
   calculada → validada → fechada → paga.
4. **Pode conter valores positivos (a favor) ou negativos (contra) do
   funcionário.** Valores negativos exigem **motivo específico e validado**
   (erro comprovado, devolução, decisão judicial) e respeitam os **limites
   legais de desconto**.
5. **O holerite complementar é distinto** do holerite da competência original
   (RFC-007) — exibe apenas as diferenças.
6. **Exige autorização** (RFC-009) — abrir e fechar uma complementar são ações
   auditadas com motivo obrigatório.

## 4. Diferença entre Folha Complementar e Outras Folhas

| Folha | O que é |
|---|---|
| Mensal | Competência regular |
| Complementar | Ajuste de competência fechada (este RFC) |
| 13º | Gratificação natalina (RFC-011) |
| Férias | Gozo de férias (RFC-010) |
| Adiantamento | Adiantamento quinzenal (RFC-006) |
| Rescisão | Acerto do desligamento (RFC-003) |

## 5. Decisões Aprovadas

1. **Motivo obrigatório** ao abrir uma folha complementar (rastreabilidade). ✅ 01/08/2026
2. **Valores positivos e negativos permitidos** — diferenças a favor ou contra
   o funcionário; valores **negativos exigem motivo específico e validado**
   (erro comprovado, devolução, decisão judicial) e respeitam os **limites
   legais de desconto**. ✅ 01/08/2026
3. **Múltiplas complementares por competência são permitidas**, cada uma com
   motivo próprio (ex.: uma para decisão judicial, outra para erro de
   lançamento). ✅ 01/08/2026
4. **Encargos e recolhimentos são recalculados apenas sobre a diferença**
   (RFC-014). ✅ 01/08/2026

## 6. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| _em aberto_ | _autor_ | ⏳ | — |
