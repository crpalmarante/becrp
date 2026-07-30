# Business Platform
# BC-005C — Enterprise Capability Map & Value Streams

**Documento:** BC-005C
**Título:** Enterprise Capability Map & Value Streams
**Versão:** 1.0.0 (Draft)
**Dependências:** BC-000 a BC-005B

---

## Capítulo 1 — Objetivo

Definir como as Capacidades Empresariais se organizam para entregar valor ao negócio.

Este documento conecta:

- Estratégia
- Capacidades
- Processos
- Eventos
- Agregados
- Interfaces

É a ponte entre a arquitetura corporativa e a implementação do ERP.

---

## Capítulo 2 — Conceitos Fundamentais

**Business Capability**

Representa uma competência permanente da organização. Exemplo: Vender.

**Value Stream**

Representa uma sequência de atividades que gera valor.

```
Cliente solicita orçamento
    ↓
Empresa analisa
    ↓
Empresa vende
    ↓
Empresa entrega
    ↓
Cliente recebe
    ↓
Empresa recebe pagamento
```

O cliente não compra um "Pedido". O cliente compra uma **solução**.

---

## Capítulo 3 — Arquitetura Geral

```
Estratégia
    ↓
Business Capabilities
    ↓
Value Streams
    ↓
Business Processes
    ↓
Casos de Uso
    ↓
Eventos
    ↓
Interface
```

---

## Capítulo 4 — Value Streams Universais

Toda empresa possui alguns fluxos universais.

```
Lead to Customer
Quote to Order
Order to Cash
Procure to Pay
Plan to Produce
Record to Report
Hire to Retire
Idea to Market
Issue to Resolution
```

Esses fluxos são independentes do segmento.

---

## Capítulo 5 — Order to Cash

Fluxo clássico de vendas.

```
Cliente
  ↓
Orçamento
  ↓
Pedido
  ↓
Separação
  ↓
Expedição
  ↓
Documento Comercial
  ↓
Documento Fiscal
  ↓
Recebimento
  ↓
Contabilidade
  ↓
Encerramento
```

**Participação dos Cores:**

| Etapa | Core |
|-------|------|
| Orçamento | BusinessCore |
| Pedido | BusinessCore |
| Estoque | BusinessCore |
| Documento Fiscal | FiscalCore |
| Recebimento | BusinessCore |
| Contabilização | AccountingCore |
| Aprovações | WorkflowCore |

---

## Capítulo 6 — Procure to Pay

```
Necessidade
  ↓
Cotação
  ↓
Fornecedor
  ↓
Pedido de Compra
  ↓
Recebimento
  ↓
Documento Fiscal
  ↓
Pagamento
  ↓
Contabilidade
```

---

## Capítulo 7 — Record to Report

Fluxo contábil.

```
Eventos
  ↓
Lançamentos
  ↓
Conciliação
  ↓
Balancete
  ↓
DRE
  ↓
Balanço
  ↓
SPED
```

Responsável: **AccountingCore**

---

## Capítulo 8 — Lead to Customer

```
Lead
  ↓
Contato
  ↓
Oportunidade
  ↓
Proposta
  ↓
Negociação
  ↓
Cliente
  ↓
Venda
```

---

## Capítulo 9 — Issue to Resolution

```
Chamado
  ↓
Análise
  ↓
Diagnóstico
  ↓
Execução
  ↓
Validação
  ↓
Encerramento
```

---

## Capítulo 10 — Fluxos da Reforma Tributária Brasileira

O BusinessCore permanece neutro, mas os fluxos de valor precisam considerar a existência do FiscalCore.

```
Venda
  ↓
Documento Comercial
  ↓
Documento Fiscal
  ↓
Motor Tributário
  ↓
IBS
  ↓
CBS
  ↓
Split Payment
  ↓
Contabilidade
```

Essa sequência permite acomodar a evolução da legislação sem alterar o núcleo do domínio.

---

## Capítulo 11 — Capability Map

```
Gestão Estratégica
├── Planejamento
├── Governança
├── Compliance

Comercial
├── CRM
├── Vendas
├── Contratos

Operações
├── Compras
├── Estoque
├── Produção
├── Logística

Financeiro
├── Receber
├── Pagar
├── Tesouraria

Contabilidade
├── Lançamentos
├── DRE
├── Balanço

Fiscal
├── Tributação
├── SPED
├── Reforma Tributária
```

---

## Capítulo 12 — Matriz Capability × Value Stream

| Value Stream | Capacidades Envolvidas |
|---|---|
| Lead to Customer | CRM, Comercial |
| Quote to Order | Comercial, Contratos |
| Order to Cash | Comercial, Estoque, Fiscal, Financeiro, Contabilidade |
| Procure to Pay | Compras, Estoque, Fiscal, Financeiro |
| Record to Report | Financeiro, Contabilidade |
| Issue to Resolution | Atendimento, Projetos, Workflow |

Essa matriz será utilizada para identificar impactos quando uma capacidade evoluir.

---

## Capítulo 13 — Integração com Eventos

Todo Value Stream é composto por eventos de domínio.

```
PedidoCriado
  ↓
PedidoAprovado
  ↓
EstoqueReservado
  ↓
DocumentoFiscalEmitido
  ↓
PagamentoRecebido
  ↓
LançamentoContábilGerado
```

Os eventos conectam os Cores de forma desacoplada.

---

## Capítulo 14 — Integração com Workflow

Cada etapa de um fluxo pode ser enriquecida por aprovações e tarefas.

```
Pedido
  ↓
Workflow
  ↓
Aprovação Comercial
  ↓
Aprovação Financeira
  ↓
Aprovação Fiscal
  ↓
Execução
```

O **WorkflowCore** coordena, mas não substitui as regras de negócio.

---

## Capítulo 15 — Métricas de Fluxo

Cada Value Stream pode ser monitorado por indicadores.

- Tempo médio de ciclo
- Tempo de aprovação
- Tempo de faturamento
- Tempo de entrega
- Tempo de recebimento
- Percentual de retrabalho
- Taxa de conversão
- Nível de serviço (SLA)

Essas métricas alimentam o módulo de **Analytics**.

---

## Capítulo 16 — Arquitetura Integrada

```
Estratégia
    ↓
Business Capabilities
    ↓
Value Streams
    ↓
Business Processes
    ↓
Use Cases
    ↓
Aggregates
    ↓
Domain Events
    ↓
Application Services
    ↓
UI / API / Mobile / Integrações
```

Essa cadeia garante rastreabilidade completa entre estratégia e execução.

---

## Capítulo 17 — Evolução

Cada Value Stream possui um nível de maturidade.

| Nível | Característica |
|-------|----------------|
| 1 | Manual |
| 2 | Digitalizado |
| 3 | Integrado |
| 4 | Automatizado |
| 5 | Inteligente (IA e automação adaptativa) |

Essa classificação orienta o roadmap de evolução da plataforma.

---

## Capítulo 18 — Benefícios

- Alinhamento entre estratégia e tecnologia
- Priorização baseada em valor
- Menor acoplamento entre módulos
- Visibilidade ponta a ponta dos processos
- Facilidade para integração entre Cores
- Base sólida para BPM, Analytics e Inteligência Artificial

---

## Capítulo 19 — Visão Corporativa

```
Visão Estratégica
    ↓
Business Capabilities
    ↓
Value Streams
    ↓
Business Processes
    ↓
BusinessCore
    ↓
┌──────┼──────────┬────────────┐
▼      ▼          ▼            ▼
Fiscal  Accounting Workflow Integration
 Core      Core       Core        Core
    ↓
FiscalUI
```

---

## Capítulo 20 — Próxima Fronteira

Com o BC-005C concluído, a plataforma já possui:

- Filosofia arquitetural
- Ontologia
- Modelo Canônico
- Entidades
- Objetos de Valor
- Tipos de Dados de Negócio
- Agregados
- Regras de Domínio
- Capacidades Empresariais
- Fluxos de Valor

Agora começaremos a modelar o comportamento do sistema.

---

## Roadmap Proposto

```
BC-006  Domain Events
BC-007  Commands
BC-008  Use Cases
BC-009  Domain Services
BC-010  State Machines
BC-011  Event Store
BC-012  CQRS
BC-013  Event Sourcing
BC-014  Saga Pattern
BC-015  Business Process Engine
```

---

**Arquivo:** `docs/BC-005C_VALUE_STREAMS.md`
**Versão:** 1.0.0
**Data:** 2026-07-25
