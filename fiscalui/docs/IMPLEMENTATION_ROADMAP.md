# FiscalUI — Roadmap de Implementação

**Arquivo:** `docs/IMPLEMENTATION_ROADMAP.md`
**Versão:** 1.0.0
**Data:** 2026-07-25

---

Este documento define **o que será construído agora** vs. **o que permanece como visão de futuro**.

Arquitetura conceitual completa (BC-000 a BC-006C) documenta o mapa da cidade.
Este roadmap define a primeira rua a ser pavimentada.

---

## N1 — MVP

**O que construir agora.** ≈ 80% das necessidades com ≈ 20% da complexidade.

### Stack

| Camada | Tecnologia |
|--------|------------|
| Frontend | HTML / CSS / JavaScript (FiscalUI) |
| API | Python (FastAPI) |
| Regras críticas | COBOL |
| Persistência | PostgreSQL |
| Comunicação | Dispatcher interno (Mediator pattern) |
| Eventos | Tabela `event_log` no PostgreSQL |

### Arquitetura Executável

```
HTML/CSS/JS
    ↓
Controllers
    ↓
Use Cases
    ↓
BusinessCore (Entidades, VOs, Agregados, Regras)
    ↓
Repositories
    ↓
PostgreSQL

── Paralelo ──

Use Case
    ↓
Domain Event
    ↓
Dispatcher (Mediator, ~10 classes)
    ↓
Listeners → FiscalCore / AccountingCore / WorkflowCore
    ↓
Event Log (tabela PostgreSQL)
```

### Módulos

| Módulo | Descrição | Prioridade |
|--------|-----------|------------|
| **BusinessCore** | Entidades, VOs, agregados, invariantes, políticas | Alta |
| **Dispatcher** | Mediator interno para eventos | Alta |
| **FiscalCore** | Cálculo de impostos, NF-e, SPED | Alta |
| **AccountingCore** | Plano de contas, partidas dobradas, balancete | Alta |
| **WorkflowCore** | Máquina de estados, aprovações, auditoria | Média |
| **Event Log** | Tabela `event_log` para auditoria | Alta |
| **FiscalUI** | Interface do usuário (componentes visuais) | Média |
| **Segurança** | Autenticação, autorização, RBAC | Alta |

### O que NÃO está incluso no MVP

| Item | Motivo |
|------|--------|
| Kafka / RabbitMQ / NATS | Complexidade desnecessária para processo único |
| Service Bus | Dispatcher interno resolve |
| Registry / Discovery | Apenas 1 servidor |
| CQRS | Commands e Queries no mesmo processo |
| Event Sourcing | Event Log + estado atual resolve |
| Saga Pattern | Transações no mesmo banco |
| Microsserviços | Escopo não justifica |
| Streaming | Sem demanda |
| Cache | Pode ser adicionado depois sem impacto |

---

## N2 — Plataforma

**Próximo ciclo, quando houver necessidade.**

### O que adicionar

| Item | Quando |
|------|--------|
| APIs públicas versionadas | Integrações com parceiros |
| Filas de processamento | Tarefas pesadas (SPED, fechamento mensal) |
| Cache (Redis) | Mais de 100 usuários simultâneos |
| Observabilidade | OpenTelemetry, Prometheus, Grafana |
| Sistema de plugins | Marketplace de extensões |
| CI/CD | Pipeline de deploy automatizado |

### O que NÃO muda

- BusinessCore permanece idêntico
- Contratos entre Cores permanecem
- PostgreSQL permanece como fonte da verdade
- Dispatcher interno pode ser substituído por filas sem impacto nos Cores

---

## N3 — Enterprise

**Somente quando houver demanda real.**

### O que adicionar

| Item | Quando |
|------|--------|
| Kafka / Event Streaming | Múltiplos consumidores, alta throughput |
| Service Bus | Múltiplos servidores, descoberta dinâmica |
| CQRS | Commands e Queries em bancos separados |
| Event Sourcing | Reconstrução de estado a partir de eventos |
| Saga Pattern | Transações distribuídas entre servidores |
| Registry / Discovery | Escalabilidade horizontal |
| Microsserviços | Cada Core em processo separado |

### Gatilhos para evoluir

- Mais de 500 usuários simultâneos
- Mais de 50 empresas no mesmo tenant
- Necessidade de escalar Cores independentemente
- Time de desenvolvimento com mais de 10 pessoas
- Demanda de mercado por APIs públicas

---

## Riscos da Superengenharia

Implementar N3 agora causaria:

- Centenas de classes para problemas que não existem
- Complexidade acidental (configuração de brokers, serialização, schemas)
- Dificuldade de contratação (time pequeno conhece Python + COBOL, não Kafka)
- Lentidão no desenvolvimento do que realmente importa: regras de negócio
- Frustração por não entregar valor visível

A arquitetura conceitual está documentada. Quando chegar a hora, o caminho está traçado.

---

## Princípio

> Construa o mínimo que resolva o problema de hoje.
> Desenhe o máximo que permita crescer amanhã.
> Nunca implemente o máximo antes do mínimo.

---

## Documentos Relacionados

| Documento | Conteúdo |
|-----------|----------|
| `ARCHITECTURE.md` | Arquitetura geral com níveis de maturidade |
| `BC-000_MANIFESTO.md` | Filosofia arquitetural |
| `BC-006A_MESSAGE_CONTRACT.md` | Formato UBMC (referência futura) |
| `BC-006B_UNIVERSAL_PROTOCOL.md` | Protocolo UBP (referência futura) |
| `BC-006C_SERVICE_BUS.md` | Barramento UBSB (referência futura) |
