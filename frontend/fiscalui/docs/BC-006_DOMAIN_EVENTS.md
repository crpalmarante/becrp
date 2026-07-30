# Business Platform
# BC-006 — Domain Events

**Documento:** BC-006
**Título:** Catálogo Universal de Eventos de Domínio
**Versão:** 1.0.0 (Draft)
**Dependências:** BC-000 a BC-005C

---

## Capítulo 1 — Objetivo

Definir o modelo oficial de Eventos de Domínio da plataforma.

Um evento representa um **fato de negócio que ocorreu** e não pode ser desfeito.

Um evento responde sempre à pergunta:

> "O que aconteceu?"

Nunca:

- O que fazer
- Quem chamar
- Qual tela abrir

Essas decisões pertencem a outras camadas.

---

## Capítulo 2 — Filosofia

Eventos representam fatos no **passado**.

```
PedidoCriado
PedidoAprovado
PagamentoRecebido
ProdutoMovimentado
NFEmitida
ContratoEncerrado
```

Porque o evento já aconteceu.

---

## Capítulo 3 — Características

Todo evento deve ser:

- Imutável
- Auditável
- Versionado
- Temporal
- Ordenável
- Identificável
- Publicável
- Persistente

Nunca poderá ser alterado. Caso exista erro, um novo evento corrige o anterior.

---

## Capítulo 4 — Estrutura Canônica

Todo evento herda:

```
DomainEvent
├── EventId
├── EventType
├── AggregateId
├── AggregateType
├── OccurredAt
├── RecordedAt
├── Version
├── CorrelationId
├── CausationId
├── Actor
├── Tenant
├── Organization
├── Payload
└── Metadata
```

---

## Capítulo 5 — Identificadores

**EventId** — Identificador único. Nunca reutilizado.

**CorrelationId** — Liga diversos eventos pertencentes ao mesmo fluxo.

```
Venda
  ↓
PedidoCriado → PedidoAprovado → NFEmitida → PagamentoRecebido
Todos possuem o mesmo CorrelationId.
```

**CausationId** — Indica qual evento originou outro.

```
NFEmitida possui:
  CausationId = PedidoAprovado
```

---

## Capítulo 6 — Classificação

Os eventos são classificados por Core de origem:

- Business Events
- Fiscal Events
- Accounting Events
- Workflow Events
- Security Events
- Integration Events
- System Events

---

## Capítulo 7 — Eventos do BusinessCore

**Party**
```
PartyCreated
PartyUpdated
PartyActivated
PartySuspended
PartyMerged
PartyArchived
```

**Product**
```
ProductCreated
ProductUpdated
ProductDiscontinued
PriceChanged
ProductClassified
```

**Order**
```
OrderCreated
ItemAdded
ItemRemoved
OrderSubmitted
OrderApproved
OrderRejected
OrderCancelled
OrderCompleted
```

**Contract**
```
ContractCreated
ContractSigned
ContractRenewed
ContractExpired
ContractCancelled
```

**Project**
```
ProjectCreated
TaskAdded
TaskCompleted
ProjectFinished
```

---

## Capítulo 8 — Eventos do FiscalCore

```
FiscalDocumentGenerated
FiscalDocumentValidated
FiscalDocumentSigned
FiscalDocumentAuthorized
FiscalDocumentRejected
FiscalDocumentCancelled
SPEDGenerated
TaxCalculated
IBSCalculated
CBSCalculated
SplitPaymentGenerated
```

---

## Capítulo 9 — Eventos do AccountingCore

```
JournalEntryCreated
JournalPosted
AccountReconciled
AssetDepreciated
BalanceClosed
DREGenerated
```

---

## Capítulo 10 — Eventos do WorkflowCore

```
WorkflowStarted
TaskAssigned
ApprovalRequested
ApprovalGranted
ApprovalRejected
WorkflowCompleted
```

---

## Capítulo 11 — Eventos do SecurityCore

```
UserAuthenticated
PermissionGranted
PermissionRevoked
RoleAssigned
RoleRemoved
SecurityViolationDetected
```

---

## Capítulo 12 — Eventos do IntegrationCore

```
ApiCalled
WebhookReceived
MessagePublished
QueueConsumed
SynchronizationCompleted
```

---

## Capítulo 13 — Catálogo Global

Os eventos dos 6 Cores formam o Catálogo Global. Esse catálogo crescerá por versões.

---

## Capítulo 14 — Fluxo de Eventos

```
Cliente cria pedido
  ↓
OrderCreated
  ↓
WorkflowStarted
  ↓
OrderApproved
  ↓
StockReserved
  ↓
FiscalDocumentGenerated
  ↓
FiscalDocumentAuthorized
  ↓
PaymentReceived
  ↓
JournalEntryCreated
  ↓
OrderCompleted
```

Nenhum Core chama outro diretamente. Todos reagem aos eventos.

---

## Capítulo 15 — Publicação

```
Aggregate
  ↓
Validação
  ↓
Persistência
  ↓
Evento
  ↓
Event Store
  ↓
Message Bus
  ↓
Subscribers
```

A persistência do agregado e do evento deve ser tratada de forma consistente.

---

## Capítulo 16 — Consumo

Os consumidores são independentes.

```
OrderApproved
  ↓
FiscalCore → AccountingCore → WorkflowCore → AnalyticsCore → NotificationCore
```

Cada um decide se deve agir.

---

## Capítulo 17 — Event Store

Todos os eventos são armazenados. Nunca removidos.

```
EventStore
  ↓
Append Only
  ↓
Versionado
  ↓
Auditável
  ↓
Consultável
```

O Event Store não substitui o banco transacional; ele complementa a arquitetura.

---

## Capítulo 18 — Versionamento

Eventos evoluem.

```
OrderCreated v1
OrderCreated v2
OrderCreated v3
```

Consumidores podem suportar múltiplas versões.

---

## Capítulo 19 — Benefícios

- Auditoria completa
- Baixo acoplamento
- Integrações desacopladas
- Escalabilidade
- Processamento assíncrono
- Rastreabilidade ponta a ponta
- Base para Event Sourcing
- Base para Inteligência Artificial
- Base para Analytics em tempo real

---

## Capítulo 20 — Arquitetura Geral

```
                 Business Platform
                        │
                 BusinessCore
                        │
                 Aggregate Root
                        │
               Domain Event Raised
                        │
                 Event Store (Append Only)
                        │
                 Message Bus / Broker
        ┌───────────┼───────────┬───────────┬───────────┐
        ▼           ▼           ▼           ▼           ▼
   FiscalCore  AccountingCore WorkflowCore AnalyticsCore IntegrationCore
        │           │           │           │           │
        └───────────┴───────────┴───────────┴───────────┘
                    Interfaces (Web / Mobile / API / COBOL)
```

---

## Capítulo 21 — Especificação Técnica do Evento

Para garantir interoperabilidade entre Python, COBOL, PostgreSQL, APIs REST, mensageria (Kafka/RabbitMQ/NATS) e futuras integrações, todos os eventos seguirão um envelope padronizado.

```
DomainEventEnvelope
├── Header
│   ├── EventId
│   ├── EventType
│   ├── EventVersion
│   ├── AggregateId
│   ├── AggregateType
│   ├── CorrelationId
│   ├── CausationId
│   ├── OccurredAt
│   ├── RecordedAt
│   ├── TenantId
│   ├── OrganizationId
│   └── Producer
├── Payload
│   └── Dados específicos do evento
└── Metadata
    ├── SchemaVersion
    ├── TraceId
    ├── SourceSystem
    ├── Signature
    └── Extensions
```

Essa estrutura permitirá serialização em JSON, Avro, Protobuf ou COBOL Copybook, mantendo o mesmo contrato conceitual.

---

## Roadmap

```
BC-006  Domain Events          ✓
BC-007  Business Commands
BC-008  Use Cases
BC-009  Domain Services
BC-010  State Machines
BC-011  Event Store
BC-012  CQRS
BC-013  Event Sourcing
BC-014  Saga Pattern
BC-015  Business Process Engine
BC-016  Rule Engine
BC-017  AI Business Agents
```

---

**Arquivo:** `docs/BC-006_DOMAIN_EVENTS.md`
**Versão:** 1.0.0
**Data:** 2026-07-25
