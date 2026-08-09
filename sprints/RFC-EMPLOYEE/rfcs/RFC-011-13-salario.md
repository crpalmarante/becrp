# RFC-011 — 13º Salário

| Campo | Valor |
|---|---|
| **Título** | Processo de 13º salário (gratificação natalina) |
| **Autor** | crpalmarante |
| **Status** | 📝 Draft (em revisão) |
| **Data** | 01/08/2026 |
| **Versão** | 1.0.0 |
| **Área** | Conceitos — Processos |
| **Depende de** | RFC-001, RFC-002, RFC-004, RFC-006 |
| **Impacta** | RFC-003, RFC-006, RFC-007, RFC-014 |

---

## 1. Conceito

**13º salário** (gratificação natalina) é um pagamento anual ao funcionário,
pago em **2 parcelas**: 1ª parcela até 30/11 e 2ª parcela até 20/12. É um
direito proporcional: **1/12 por mês trabalhado** (mês com 15 dias ou mais de
trabalho conta como mês inteiro).

## 2. Base de Cálculo

| Componente | Origem |
|---|---|
| Salário base | RFC-002 |
| Médias de horas extras / comissões / adicionais | Média dos 12 meses anteriores (RFC-004) |
| 1ª parcela | Metade do valor bruto calculado, **sem descontos** |
| 2ª parcela | Valor restante, **com INSS e IRRF** |

## 3. Parcelas

### 3.1 1ª Parcela (até 30/11)
- Metade do salário de dezembro (ou do último salário).
- **Sem descontos** de INSS/IRRF.
- Pode ser **antecipada junto com as férias** (decisão: proposta — ver 7).

### 3.2 2ª Parcela (até 20/12)
- Valor total do 13º **menos** a 1ª parcela.
- **Com descontos** de INSS (tabela vigente — RFC-005) e IRRF.
- Pode ter dedução de pensão alimentícia (RFC-004, evento 27).

## 4. Proporcionalidade

| Situação | Regra |
|---|---|
| Mês com 15+ dias trabalhados | Conta como mês inteiro |
| Admissão no meio do ano | Proporcional aos meses trabalhados |
| Afastamento sem remuneração | Não conta como mês trabalhado (ver RFC-012) |
| Rescisão | 13º proporcional no acerto (RFC-003) |

## 5. Competência Própria

Conforme RFC-006 (seção 6), o 13º é **competência separada** com processamento
próprio (1ª e 2ª parcela como folhas próprias). Isso isola o cálculo e mantém a
auditabilidade.

## 6. Regras do Processamento

1. **1ª parcela nunca tem descontos** de INSS/IRRF.
2. **2ª parcela usa as tabelas vigentes da competência** de dezembro.
3. **Médias integram a base** — horas extras, comissões, adicionais do período.
4. **Encargos patronais e FGTS incidem sobre o 13º** conforme a legislação
   vigente — consolidados no relatório de encargos (RFC-014).

## 7. Decisões Aprovadas

1. **Antecipação da 1ª parcela nas férias** — permitida na 1ª versão. ✅ 01/08/2026
2. **Médias dos 12 meses integram a base** do 13º. ✅ 01/08/2026
3. **1ª parcela sem descontos** (conforme legislação). ✅ 01/08/2026
4. **Competência própria de 13º com 1ª e 2ª parcela** — já decidido no RFC-006. ✅

## 8. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| _em aberto_ | _autor_ | ⏳ | — |
