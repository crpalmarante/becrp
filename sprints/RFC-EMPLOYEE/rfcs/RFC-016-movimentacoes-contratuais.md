# RFC-016 — Movimentações Contratuais

| Campo | Valor |
|---|---|
| **Título** | Movimentações contratuais: alterações com vigência |
| **Autor** | crpalmarante |
| **Status** | ✅ Implementado (09/08/2026 — cargo e departamento com vigência; salário com vigência desde 31/07/2026; jornada/benefícios/forma de pagamento como evolução) |
| **Data** | 01/08/2026 |
| **Versão** | 1.0.0 |
| **Área** | Conceitos — Processos |
| **Depende de** | RFC-001, RFC-002, RFC-008 |
| **Impacta** | RFC-004, RFC-006, RFC-007, RFC-013, RFC-015 |

---

## 1. Conceito

**Movimentação contratual** é toda alteração no contrato do funcionário que
muda dados usados no cálculo: salário, cargo, departamento, jornada, benefícios
ou forma de pagamento. Toda movimentação tem **data de vigência** (RFC-002,
regra 3) — o cálculo usa o valor vigente na competência.

## 2. Tipos de Movimentação

| Tipo | O que muda | Impacto no cálculo |
|---|---|---|
| **Alteração salarial** | Salário base (RFC-002) | Base de todos os eventos proporcionais |
| **Mudança de cargo** | Cargo (RFC-008) | Referência; possivelmente adicional |
| **Mudança de departamento** | Departamento/centro de custo (RFC-008) | Rateio e relatórios (RFC-015) |
| **Alteração de jornada** | Carga horária contratual (RFC-002) | Valor da hora (RFC-004) |
| **Alteração de benefícios** | VT, VR, plano de saúde (RFC-002) | Descontos do funcionário |
| **Alteração de forma de pagamento** | Banco/agência/conta | Holerite e pagamento (RFC-007) |

## 3. Vigência e Retroação

1. **Toda movimentação tem data de vigência** — o processamento da competência
   aplica os dados vigentes naquele mês.
2. **Vigência retroativa é permitida** apenas se **não altera competências já
   fechadas** (RFC-002, regra 4).
3. **Retroatividade que afeta competência fechada** gera **folha complementar**
   (RFC-013) — nunca edição da fechada.
4. **O histórico completo é preservado** desde a admissão (RFC-002, decisão 1).

## 4. Regras do Processo

1. **O cálculo usa a vigência da competência**, não o valor atual do cadastro.
2. **Alteração de cargo/departamento não altera salário automaticamente** — são
   movimentações independentes.
3. **Alterações retroativas a períodos abertos** (não fechados) podem ser feitas
   diretamente na competência.
4. **Toda movimentação é auditada** (RFC-009) — quem, quando, o quê, vigência.

## 5. Decisões Aprovadas

1. **Histórico completo de movimentações desde a admissão** — nunca
   sobrescrever; sempre registrar a nova vigência. ✅ 01/08/2026
2. **Cada tipo de movimentação é independente** — salário e cargo são
   movimentações separadas. ✅ 01/08/2026
3. **Vigência retroativa permitida só para competências abertas**; fechadas
   apenas via folha complementar (RFC-013). ✅ 01/08/2026
4. **Auditoria obrigatória de toda movimentação** (RFC-009). ✅ 01/08/2026

## 6. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| crpalmarante | autor | ✅ Aprovado | 10/08/2026 |
