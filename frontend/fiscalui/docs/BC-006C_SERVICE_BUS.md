# Business Platform
# BC-006C — Universal Business Service Bus (UBSB)

**Documento:** BC-006C
**Título:** Universal Business Service Bus
**Versão:** 2.0.0 (Draft)
**Dependências:** BC-006A (UBMC), BC-006B (UBP)

---

## Capítulo 1 — Objetivo

Definir o barramento lógico que conecta todos os componentes da plataforma.

O UBSB é responsável por:

- Descobrir serviços
- Encaminhar mensagens
- Aplicar políticas
- Controlar integrações
- Garantir observabilidade
- Manter desacoplamento

Ele não implementa regras de negócio. Ele apenas conecta quem produz e quem consome.

---

## Capítulo 2 — Filosofia

Nenhum Core conhece outro Core. Todos conhecem apenas o Barramento.

```
BusinessCore → UBSB → AccountingCore
```

O mesmo vale para FiscalCore, WorkflowCore, SecurityCore, AnalyticsCore, IntegrationCore, NotificationCore.

---

## Capítulo 3 — Arquitetura Geral

```
                Business Platform
                        │
                Universal API
                        │
                     UBMC
                        │
                      UBP
                        │
────────────────────────────────────────
        Universal Business Service Bus
────────────────────────────────────────
      │        │         │        │
      ▼        ▼         ▼        ▼
Business Fiscal Accounting Workflow
 Core     Core      Core      Core
      │        │         │        │
      └────────┴─────────┴────────┘
              IntegrationCore
```

---

## Capítulo 4 — Componentes do Barramento

O UBSB é composto pelos seguintes módulos:

- Router
- Registry
- Dispatcher
- Policy Engine
- Transformation Engine
- Subscription Manager
- Dead Letter Manager
- Monitoring
- Tracing
- Audit
- Metrics
- Security Gateway

Cada componente possui uma responsabilidade única.

---

## Capítulo 5 — Registry

Todos os serviços registrados informam:

```
ServiceId
ServiceName
Capabilities
Supported Messages
Supported Versions
Health Status
Endpoint
Owner
```

O Registry é a "lista telefônica" da plataforma.

---

## Capítulo 6 — Router

O Router decide para onde cada mensagem deve seguir.

```
OrderApproved
  ↓
Router
  ↓
FiscalCore → AccountingCore → WorkflowCore → NotificationCore
```

O produtor não precisa conhecer os consumidores.

---

## Capítulo 7 — Dispatcher

Responsável pela entrega efetiva. Suporta:

- Sync
- Async
- Broadcast
- Streaming
- Delayed Delivery
- Priority Queue

---

## Capítulo 8 — Subscription Manager

Cada Core informa quais mensagens deseja receber.

```
FiscalCore
  └── Subscribe: OrderApproved, OrderCancelled, ProductUpdated
```

O Subscription Manager mantém esse catálogo.

---

## Capítulo 9 — Policy Engine

Controla políticas de comunicação:

- Prioridade
- QoS
- Criptografia
- Compressão
- Expiração
- Retry
- Roteamento por Tenant
- Roteamento por Organização

---

## Capítulo 10 — Transformation Engine

Nem todos os consumidores precisam do mesmo formato.

```
UBMC → JSON → XML → Avro → Protobuf → COBOL Copybook
```

O contrato lógico permanece o mesmo.

---

## Capítulo 11 — Security Gateway

Toda mensagem passa por validação:

- Autenticação
- Autorização
- Assinatura
- Integridade
- Permissões
- Tenant
- Organização

Nenhuma mensagem chega ao Core sem validação.

---

## Capítulo 12 — Dead Letter Manager

```
Fila Principal → Erro Permanente → DLQ → Revisão → Reprocessamento
```

Nenhuma mensagem é descartada silenciosamente.

---

## Capítulo 13 — Monitoramento

Cada mensagem gera métricas:

- Recebida
- Processada
- Falhou
- Tempo
- Latência
- Retries
- Consumidor
- Produtor

---

## Capítulo 14 — Auditoria

Todas as operações ficam registradas:

- Quem publicou
- Quando publicou
- Quem consumiu
- Resultado
- Tempo
- Versão
- TraceId

Isso complementa o Event Store.

---

## Capítulo 15 — Tracing

Compatível com OpenTelemetry.

```
CorrelationId → TraceId → SpanId
```

---

## Capítulo 16 — Descoberta de Serviços

O UBSB não utiliza endereços fixos. Ele resolve dinamicamente:

```
AccountingCore → Registry → Endpoint Atual
```

Isso facilita escalabilidade e alta disponibilidade.

---

## Capítulo 17 — Alta Disponibilidade

O barramento suporta:

- múltiplas instâncias
- balanceamento de carga
- failover automático
- particionamento por Tenant
- recuperação automática

---

## Capítulo 18 — Integração com COBOL

```
Frontend → BusinessCore → UBSB → COBOL Adapter → Programa COBOL → UBSB → AccountingCore
```

O programa COBOL não precisa conhecer REST, WebSocket ou Kafka. Ele conversa apenas através do adaptador UBMC/UBP.

---

## Capítulo 19 — Fluxo Completo

```
Usuário → Frontend → CreateOrder → BusinessCore → OrderCreated → UBSB
  → WorkflowCore → OrderApproved → UBSB
  → FiscalCore → InvoiceIssued → UBSB
  → AccountingCore → JournalEntryCreated → UBSB
  → AnalyticsCore → Dashboard Atualizado
```

Nenhum Core chama outro diretamente.

---

## Capítulo 20 — Catálogo de Adaptadores

| Adaptador | Responsabilidade |
|---|---|
| REST Adapter | APIs HTTP |
| WebSocket Adapter | Comunicação em tempo real |
| Kafka Adapter | Event Streaming |
| RabbitMQ Adapter | Filas de trabalho |
| NATS Adapter | Mensageria leve |
| COBOL Adapter | Programas legados |
| File Adapter | Troca por arquivos |
| Database Adapter | Outbox/Inbox |
| Scheduler Adapter | Execução programada |

---

## Capítulo 21 — Interfaces do UBSB

Todo adaptador implementará um conjunto padronizado de operações:

```
IMessagePublisher
    publish()

IMessageSubscriber
    subscribe()
    unsubscribe()

IMessageRouter
    route()

IMessageDispatcher
    dispatch()

IServiceRegistry
    register()
    unregister()
    discover()

ITransformationEngine
    transform()

IPolicyEngine
    evaluate()

IAuditService
    record()

IMonitoringService
    measure()

IDeadLetterService
    move()
    retry()
```

Essas interfaces independem da linguagem. Em Python: classes abstratas. Em COBOL: programas padronizados. Em JavaScript: módulos ou serviços.

---

## Capítulo 22 — Arquitetura Consolidada

```
                  Business Platform
                         │
                    Frontend UI
              HTML • CSS • JavaScript
                         │
                    Universal API
                         │
                        UBMC
                         │
                         UBP
                         │
────────────────────────────────────────────
       Universal Business Service Bus
────────────────────────────────────────────
 Registry • Router • Dispatcher
 Policy • Security • Monitoring
 Transformation • Audit • Tracing
────────────────────────────────────────────
        │          │           │
        ▼          ▼           ▼
  BusinessCore FiscalCore AccountingCore
        │          │           │
        ▼          ▼           ▼
 WorkflowCore SecurityCore IntegrationCore
        │
        ▼
 PostgreSQL • Event Store • Outbox • Inbox
        │
        ▼
 COBOL Runtime / Python Services / APIs
```

---

**Arquivo:** `docs/BC-006C_SERVICE_BUS.md`
**Versão:** 2.0.0
**Data:** 2026-07-25
