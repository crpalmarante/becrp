# Business Platform
# BC-006B — Universal Business Protocol (UBP)

**Documento:** BC-006B
**Título:** Universal Business Protocol
**Versão:** 2.0.0 (Draft)
**Dependências:** BC-006A (UBMC)

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

Definir o protocolo oficial de comunicação entre todos os componentes da plataforma.

O UBP não define o **conteúdo** da mensagem. Ele define:

- como enviar
- quando enviar
- quem recebe
- como confirmar
- como recuperar falhas
- como rastrear

---

## Capítulo 2 — Filosofia

- **UBMC** responde: *O que está sendo enviado?*
- **UBP** responde: *Como será enviado?*

---

## Capítulo 3 — Arquitetura

```
Business Message
  ↓
UBMC
  ↓
UBP
  ↓
Transport
  ↓
Receiver
  ↓
BusinessCore
```

O protocolo é independente do meio de transporte.

---

## Capítulo 4 — Camadas

```
Application
  ↓
Business Message
  ↓
UBMC
  ↓
UBP
  ↓
Transport Adapter
  ↓
HTTP  Kafka  RabbitMQ  NATS  WebSocket  gRPC  COBOL IPC
```

Cada transporte implementa o protocolo.

---

## Capítulo 5 — Modos de Comunicação

O protocolo suporta sete modos:

- Request
- Reply
- Publish
- Subscribe
- Broadcast
- Stream
- Fire-and-Forget

---

## Capítulo 6 — Request / Reply

Comunicação síncrona.

```
Frontend → CreateOrder → BusinessCore → OrderCreated → Response
```

Usado em APIs REST e chamadas diretas.

---

## Capítulo 7 — Publish / Subscribe

Comunicação assíncrona.

```
OrderApproved → Message Broker → FiscalCore, AccountingCore, WorkflowCore, AnalyticsCore
```

Os consumidores não conhecem o produtor.

---

## Capítulo 8 — Streaming

Fluxo contínuo.

```
Sensor → Business Events → Kafka → Analytics → Dashboard
```

Ideal para monitoramento em tempo real.

---

## Capítulo 9 — Broadcast

Uma única mensagem para muitos consumidores.

```
MaintenanceModeEnabled → Todos os Serviços
```

---

## Capítulo 10 — Fire-and-Forget

Não espera resposta.

```
SendNotification → NotificationCore
```

Utilizado para tarefas não críticas.

---

## Capítulo 11 — Garantias de Entrega

O protocolo suporta diferentes garantias:

- At Most Once
- At Least Once
- Exactly Once (quando suportado pela infraestrutura)

A escolha depende do tipo de mensagem.

---

## Capítulo 12 — Idempotência

Toda mensagem pode ser processada mais de uma vez sem produzir efeitos duplicados.

```
MessageId
  ├── Já processado? → Ignorar
  └── Não → Executar
```

Essa regra é essencial para integração com filas e reprocessamentos.

---

## Capítulo 13 — Ordenação

O protocolo suporta ordenação por agregado.

```
AggregateId + SequenceNumber

OrderCreated (seq 1)
OrderApproved (seq 2)
OrderCompleted (seq 3)
```

A ordem é preservada por agregado.

---

## Capítulo 14 — Retry

Falhas temporárias com política configurável.

```
Erro → Retry → Retry → Retry → Sucesso
```

Exemplo: 3 tentativas, 5s, backoff exponencial.

---

## Capítulo 15 — Dead Letter Queue

Mensagens que falharam permanentemente.

```
Business Queue → Erro Permanente → DLQ → Administrador → Reprocessamento
```

Nada é perdido.

---

## Capítulo 16 — Timeout

Toda mensagem possui validade.

```
Timeout → Expirou? → Cancelar → Gerar Evento
```

---

## Capítulo 17 — Rastreabilidade

Toda mensagem possui rastreamento.

```
TraceId → SpanId → CorrelationId → CausationId
```

Compatível com OpenTelemetry.

---

## Capítulo 18 — QoS (Quality of Service)

| Nível | Característica |
|-------|----------------|
| QoS 0 | Melhor esforço |
| QoS 1 | Confirmada |
| QoS 2 | Confirmada e ordenada |
| QoS 3 | Transacional |

---

## Capítulo 19 — Segurança

Toda comunicação suporta:

```
TLS
JWT
OAuth2
Mutual TLS
Digital Signature
Checksum
Encryption
```

A escolha depende do canal e da sensibilidade da operação.

---

## Capítulo 20 — Adaptadores de Transporte

| Transporte | Uso Principal |
|---|---|
| HTTP/HTTPS | APIs REST |
| WebSocket | Interface em tempo real |
| Kafka | Event Streaming |
| RabbitMQ | Filas de trabalho |
| NATS | Mensageria leve |
| gRPC | Comunicação entre serviços |
| IPC COBOL | Processos locais |
| Arquivos | Integração legada |

Todos implementam a mesma interface do UBP.

---

## Capítulo 21 — Ciclo de Vida da Mensagem

```
Producer
  ↓
UBMC Envelope
  ↓
UBP Protocol
  ↓
Transport Adapter
  ↓
Message Broker
  ↓
Consumer
  ↓
Validation
  ↓
Business Processing
  ↓
Acknowledgment
  ↓
Audit Log
```

Cada etapa é rastreável e auditável.

---

## Capítulo 22 — Observabilidade

Cada mensagem registra:

- Tempo de criação
- Tempo de envio
- Tempo de recebimento
- Tempo de processamento
- Latência
- Número de tentativas
- Origem
- Destino
- Resultado
- Código de erro

---

## Capítulo 23 — Compatibilidade Tecnológica

| Tecnologia | Implementação |
|---|---|
| HTML / JavaScript | Fetch API, WebSocket |
| Python | AsyncIO, FastAPI, Celery |
| COBOL | Copybook + IPC/MQ Adapter |
| PostgreSQL | Outbox, Inbox e Event Log |
| Kafka | Producer/Consumer |
| RabbitMQ | Exchange / Queue |
| NATS | Subjects |
| REST | HTTP Adapter |

O protocolo permanece idêntico, mudando apenas o adaptador.

---

## Arquitetura Geral

```
                   Business Platform
                           │
                     Universal API
                           │
               Universal Business Message (UBMC)
                           │
              Universal Business Protocol (UBP)
                           │
                Transport Adapter Layer
        ┌────────────┬────────────┬────────────┬────────────┐
        ▼            ▼            ▼            ▼
      REST       WebSocket      Kafka      RabbitMQ
        │            │            │            │
        └────────────┴────────────┴────────────┘
                           │
                    Business Service Bus
                           │
        ┌────────────┬────────────┬────────────┬────────────┐
        ▼            ▼            ▼            ▼
  BusinessCore  FiscalCore  AccountingCore WorkflowCore
                           │
                    IntegrationCore
```

---

**Arquivo:** `docs/BC-006B_UNIVERSAL_PROTOCOL.md`
**Versão:** 2.0.0
**Data:** 2026-07-25
