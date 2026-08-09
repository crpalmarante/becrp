# Business Platform
# BC-006A — Universal Business Message Contract (UBMC)

**Documento:** BC-006A
**Título:** Universal Business Message Contract
**Versão:** 2.0.0 (Draft)
**Dependências:** BC-006 (Domain Events)

---

## Platform Philosophy

> **Simple is always better than complex.**
> Simples é sempre melhor do que complexo.

Design systems that are easy to understand, easy to maintain, easy to extend, and easy to use.
Avoid unnecessary abstractions. Prefer explicit behavior over hidden magic.
Every feature should solve a real business problem.
Performance and maintainability always come first.

---

## Capítulo 1 — Objetivo

Definir um contrato universal para todas as mensagens da plataforma. Independentemente da tecnologia utilizada.

Toda comunicação deverá utilizar um envelope único.

---

## Capítulo 2 — Filosofia

Na plataforma não existem mensagens diferentes. Existem apenas especializações.

```
Business Message
  ↓
Command  Event  Query  Response  Notification  Integration Message
```

Todos herdam da mesma estrutura.

---

## Capítulo 3 — Arquitetura

```
Frontend
  ↓
UBMC
  ↓
Backend
  ↓
UBMC
  ↓
COBOL
  ↓
UBMC
  ↓
PostgreSQL
  ↓
UBMC
  ↓
Kafka
  ↓
UBMC
  ↓
REST
  ↓
UBMC
```

Toda comunicação passa pelo UBMC.

---

## Capítulo 4 — Estrutura Universal

Toda mensagem possui obrigatoriamente:

```
BusinessMessage
├── Header
├── Body
├── Metadata
├── Security
└── Attachments
```

---

## Capítulo 5 — Header

O Header possui informações técnicas.

```
MessageId
MessageType
Version
Timestamp
CorrelationId
CausationId
Producer
Consumer
TenantId
OrganizationId
UserId
Locale
TimeZone
```

---

## Capítulo 6 — Tipos de Mensagem

- Command
- Event
- Query
- Response
- Notification
- Integration
- System

Cada tipo possui regras específicas.

---

## Capítulo 7 — Commands

Commands representam **intenção**. Sempre usam verbo.

```
CreateOrder
ApproveOrder
CancelOrder
ReserveStock
IssueInvoice
ReceivePayment
```

Commands esperam processamento.

---

## Capítulo 8 — Events

Eventos representam **fatos**.

```
OrderCreated
OrderApproved
InvoiceIssued
StockReserved
PaymentReceived
```

Eventos nunca retornam resposta.

---

## Capítulo 9 — Queries

Queries não alteram estado.

```
GetOrder
FindCustomer
SearchProducts
ListInvoices
GetStock
```

São operações somente leitura.

---

## Capítulo 10 — Responses

Resposta de um processamento.

```
Success
Failure
ValidationError
BusinessError
NotFound
Unauthorized
Conflict
```

Sempre relacionadas a uma mensagem anterior.

---

## Capítulo 11 — Notifications

Não alteram domínio.

```
EmailSent
SmsSent
PushDelivered
UserNotified
```

---

## Capítulo 12 — Integration Messages

Mensagens destinadas a sistemas externos.

```
ERP
SEFAZ
Banco
Transportadora
Marketplace
E-commerce
CRM
```

Cada integração adapta apenas o Payload. O envelope permanece.

---

## Capítulo 13 — Body

```
Payload
  ↓
Business Object
  ↓
Business Data Types
  ↓
Value Objects
```

Exemplo: `CreateOrder` → Customer, Items, Payment, Shipping, Discounts.

---

## Capítulo 14 — Metadata

```
SchemaVersion
TraceId
Source
Destination
Priority
Expiration
RetryCount
Tags
Extensions
```

---

## Capítulo 15 — Security

```
Authentication
Authorization
Digital Signature
Checksum
Encryption
Permissions
```

Todo transporte utiliza esse bloco.

---

## Capítulo 16 — Attachments

Permite envio de PDF, XML, JSON, Imagem, Planilha, Documento, Assinatura Digital — sem alterar a estrutura da mensagem.

---

## Capítulo 17 — Serialização

UBMC é independente do formato. Pode ser serializado como:

```
JSON
XML
YAML
Avro
Protobuf
COBOL Copybook
Binary
```

A estrutura lógica permanece a mesma.

---

## Capítulo 18 — Exemplo

```
BusinessMessage
├── Header
│   └── Type = Command
├── Body
│   └── CreateOrder
├── Metadata
│   └── TraceId
├── Security
│   └── JWT
└── Attachments
    └── orçamento.pdf
```

O mesmo contrato serve para qualquer tecnologia.

---

## Capítulo 19 — Fluxo Completo

```
Frontend
  ↓
CreateOrder Command
  ↓
BusinessCore
  ↓
OrderCreated Event
  ↓
WorkflowCore → FiscalCore → AccountingCore → IntegrationCore → NotificationCore
  ↓
Frontend atualizado
```

Nenhum componente conhece diretamente o outro. Todos conhecem apenas o contrato.

---

## Capítulo 20 — Benefícios

- Linguagem única para toda a plataforma
- Independência tecnológica
- Facilidade de integração
- Baixo acoplamento
- Evolução controlada
- Auditoria consistente
- Observabilidade distribuída
- Compatibilidade entre Python, COBOL e JavaScript

---

## Capítulo 21 — Envelope Canônico UBMC

```
BusinessMessage
│
├── Header
│   ├── MessageId
│   ├── MessageType
│   ├── MessageVersion
│   ├── CorrelationId
│   ├── CausationId
│   ├── Timestamp
│   ├── Producer
│   ├── Consumer
│   ├── TenantId
│   ├── OrganizationId
│   ├── UserId
│   └── Locale
│
├── Body
│   ├── PayloadType
│   ├── PayloadVersion
│   └── Payload
│
├── Metadata
│   ├── TraceId
│   ├── SourceSystem
│   ├── DestinationSystem
│   ├── Priority
│   ├── Expiration
│   ├── RetryPolicy
│   └── Extensions
│
├── Security
│   ├── Authentication
│   ├── Authorization
│   ├── Signature
│   ├── Checksum
│   └── Encryption
│
└── Attachments
    ├── AttachmentId
    ├── MimeType
    ├── FileName
    └── Reference
```

Esse envelope é o contrato oficial da plataforma e será utilizado por APIs REST, WebSockets, filas de mensagens, integrações, jobs, processos COBOL e comunicação entre Cores.

---

## Capítulo 22 — Mapeamento Tecnológico

| Tecnologia | Implementação do UBMC |
|---|---|
| HTML / JavaScript | Objetos JSON tipados |
| Python | Dataclasses ou Pydantic Models |
| COBOL | COPYBOOK padronizado |
| PostgreSQL | JSONB + tabelas normalizadas para auditoria |
| REST API | JSON sobre HTTP |
| WebSocket | JSON UBMC em tempo real |
| Kafka / RabbitMQ / NATS | JSON, Avro ou Protobuf |
| Event Store | Envelope completo append-only |

---

**Arquivo:** `docs/BC-006A_MESSAGE_CONTRACT.md`
**Versão:** 2.0.0
**Data:** 2026-07-25
