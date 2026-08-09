# RFC-006 — Processamento da Folha

| Campo | Valor |
|---|---|
| **Título** | O processo mensal: do fechamento ao pagamento |
| **Autor** | crpalmarante |
| **Status** | 📝 Draft (em revisão) |
| **Data** | 31/07/2026 |
| **Versão** | 1.0.0 |
| **Área** | Conceitos — Processos |
| **Depende de** | RFC-001 a RFC-005 |
| **Impacta** | RFC-007 |

---

## 1. Conceito

**Processamento da Folha** é a execução do cálculo de uma **competência**
(mês/ano), aplicando eventos (RFC-004) sobre os cadastros (RFC-002) com as
tabelas vigentes (RFC-005), gerando o resultado por funcionário que aparece no
holerite (RFC-007). É um **processo em etapas com estados**, que não pode ser
alterado depois de fechado.

## 2. Estados da Competência

| Estado | Descrição |
|---|---|
| **Aberta** | Competência criada; eventos e valores ainda podem ser lançados |
| **Em cálculo** | Processamento em andamento |
| **Calculada** | Cálculo concluído; valores prontos para conferência |
| **Validada** | Conferida e aprovada por quem tem autoridade |
| **Fechada** | Encerrada; **não pode mais ser alterada** |
| **Paga** | Pagamento dos funcionários registrado |

## 3. Etapas do Processamento

### 3.1 Preparação
1. **Abrir a competência** (mês/ano).
2. **Validar cadastros** — funcionários ativos com dados obrigatórios completos
   (RFC-002); alertar pendências (ex.: exame vencido, banco ausente).
3. **Carregar eventos fixos** — proventos/descontos permanentes de cada
   funcionário (salário base, VT, plano de saúde...).
4. **Lançar eventos variáveis** — horas extras, faltas, adiantamentos, comissões
   (valores ou referências por funcionário).
5. **Aplicar admissões e demissões do período** (RFC-003): incluir novos,
   excluir desligados, calcular pro-rata.

### 3.2 Cálculo
6. **Calcular proventos** — valor de cada evento de crédito.
7. **Compor a base INSS** — soma dos proventos que incidem INSS (RFC-004/005).
8. **Calcular INSS** — tabela progressiva vigente (RFC-005).
9. **Compor a base IRRF** — base INSS − INSS − dedução por dependente.
10. **Calcular IRRF** — tabela progressiva vigente (RFC-005).
11. **Calcular demais descontos** — VT (6% limitado), plano de saúde, pensão...
12. **Calcular o líquido** — total proventos − total descontos.

### 3.3 Conferência e Fechamento
13. **Revisar a folha** — conferir valores por funcionário, totais por
    departamento, conferência com o mês anterior.
14. **Aprovar/validar** — por pessoa com autoridade.
15. **Fechar a competência** — congela todos os valores.
16. **Gerar holerites** (RFC-007) e relatórios (por departamento, encargos).
17. **Registrar o pagamento** (estado "Paga").

## 4. Regras do Processamento

1. **Competência fechada é imutável** — nenhum valor pode mudar depois do
   fechamento; correções geram **folha complementar** (nova competência de
   ajuste), nunca edição da fechada.
2. **O cálculo usa a tabela da competência**, não a do dia do processamento.
3. **Todo valor do holerite tem origem rastreável** (evento + referência +
   cadastro).
4. **Estados são sequenciais** — não é possível pagar sem validar, nem validar
   sem calcular.
5. **Ações de estado exigem autorização** — abrir, validar, fechar e pagar são
   ações de pessoas com papéis distintos (ver 5).

## 5. Papéis Envolvidos

| Papel | O que pode fazer |
|---|---|
| Operador | Lançar eventos variáveis, abrir competência, calcular |
| Conferente | Revisar e validar |
| Aprovador | Fechar a competência |
| Tesouraria | Registrar pagamento |

## 6. Folhas Especiais

| Folha | Descrição | Relação |
|---|---|---|
| Folha mensal | Competência regular | Principal |
| Folha complementar | Ajustes de competência fechada | Nunca altera a fechada |
| 13º salário | 1ª e 2ª parcelas | Competência própria |
| Férias | Pagamento de férias + 1/3 | Competência/evento próprio |
| Adiantamento quinzenal | Adiantamento de salário no meio do mês (decisão: incluir) | Competência própria |
| Rescisão | Acerto do desligamento (RFC-003) | Competência da saída |

## 7. Decisões Aprovadas

1. **13º e férias como competências separadas** — processamento próprio, mais
   limpo e auditável (1ª e 2ª parcela do 13º; férias + 1/3). ✅ 31/07/2026
2. **Competência única** — a 1ª versão não processa por lotes/centros de custo;
   a competência é processada como um todo. ✅ 31/07/2026
3. **Folha de adiantamento quinzenal SIM** — decisão do autor: incluir folha de
   adiantamento quinzenal desde o início. ✅ 31/07/2026 ⚠️ (não era a
   recomendação inicial, mas foi a decisão)

## 8. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| _em aberto_ | _autor_ | ⏳ | — |
