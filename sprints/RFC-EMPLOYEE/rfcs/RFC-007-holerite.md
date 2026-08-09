# RFC-007 — Holerite (Demonstrativo de Pagamento)

| Campo | Valor |
|---|---|
| **Título** | Conceito e conteúdo do holerite |
| **Autor** | crpalmarante |
| **Status** | 📝 Draft (em revisão) |
| **Data** | 31/07/2026 |
| **Versão** | 1.0.0 |
| **Área** | Conceitos — Saídas |
| **Depende de** | RFC-001, RFC-004, RFC-006 |
| **Impacta** | — (documento de saída) |

---

## 1. Conceito

**Holerite** (demonstrativo de pagamento) é o documento que apresenta ao
funcionário, de forma clara e auditável, o resultado do processamento da folha
naquela competência: proventos, descontos, bases de cálculo e o valor líquido.
Todo valor exibido deve vir do processamento (RFC-006) — nada é digitado no
holerite.

## 2. Estrutura do Holerite

### 2.1 Cabeçalho
| Campo | Origem |
|---|---|
| Razão social / nome da empresa + CNPJ | Cadastro da empresa |
| Nome do funcionário + matrícula | RFC-002 |
| Cargo e departamento | RFC-002 |
| CPF | RFC-002 |
| Competência (mês/ano) | RFC-006 |
| Data de admissão | RFC-002 |

### 2.2 Corpo — Proventos
| Campo | Origem |
|---|---|
| Código do evento | RFC-004 |
| Descrição do evento | RFC-004 |
| Referência (horas, cotas, % ou —) | Lançamento do evento |
| Valor | Resultado do cálculo |

### 2.3 Corpo — Descontos
Mesmos campos do bloco de proventos (código, descrição, referência, valor).

### 2.4 Bases de Cálculo
| Base | Origem |
|---|---|
| Base INSS | RFC-006 (passo 7) |
| Base IRRF | RFC-006 (passo 9) |
| Base FGTS | RFC-004 (incidências) |
| Salário de referência | RFC-002 |

### 2.5 Rodapé — Totais
| Campo | Definição |
|---|---|
| Total de proventos | Soma de todos os créditos |
| Total de descontos | Soma de todos os débitos |
| **Líquido a receber** | Proventos − descontos |
| Forma de pagamento | Banco/agência/conta (RFC-002) |

## 3. Regras do Holerite

1. **Exibe somente o que foi processado** — é uma visão do resultado da
   competência, não uma planilha editável.
2. **Todo valor é rastreável** — do holerite ao evento e ao cadastro.
3. **Líquido = proventos − descontos**, sempre (validação automática).
4. **O holerite da competência fechada é imutável** — regenerá-lo reproduz
   exatamente os mesmos valores (nunca valores diferentes).
5. **Entrega:** impresso (papel) ou eletrônico (visualização) — o funcionário
   deve conseguir guardar/consultar o histórico das competências.
6. **Histórico:** o funcionário pode consultar holerites de competências
   anteriores (fechadas).

## 4. Relatórios Relacionados (não-holerite)

| Relatório | Conteúdo | Público |
|---|---|---|
| Folha por departamento | Totais de proventos/descontos por setor | Gestão |
| Total de encargos | Soma dos valores por evento de encargo | Contabilidade |
| Resumo por funcionário | Competência, líquido, forma de pagamento | Tesouraria |
| Comissões por venda de origem | Detalhe da comissão por venda/item (RFC-015 §2.1) | Conferente / Gestão |

## 5. Decisões Aprovadas

1. **Só valores do funcionário** — o holerite mostra proventos, descontos e
   líquido do funcionário; encargos do empregador (FGTS, INSS patronal) ficam
   em relatório separado. ✅ 31/07/2026
2. **Observações livres** — campo opcional de observações/mensagem por
   holerite, preenchido na competência. ✅ 31/07/2026
3. **Gestão + funcionário (autoatendimento)** — a gestão consulta todos;
   o funcionário consulta os próprios holerites. ✅ 31/07/2026

## 6. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| _em aberto_ | _autor_ | ⏳ | — |
