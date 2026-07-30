# FiscalUI — Arquitetura Geral do Sistema

## Visão Geral

```
┌──────────────────────────────────────────────────────────────┐
│                      FiscalUI                                │
│                  Interface do Usuário                        │
│           HTML / CSS / JavaScript (Vanilla)                  │
│         Consome APIs de todos os motores                     │
└────────────────────────┬─────────────────────────────────────┘
                         │ JSON sobre HTTP
┌────────────────────────┼─────────────────────────────────────┐
│         ┌──────────────┼──────────────┐                      │
│         │              │              │                      │
│  ┌──────┴──────┐ ┌─────┴──────┐ ┌────┴──────┐               │
│  │ BusinessCore│ │ FiscalCore │ │Accounting │               │
│  │ Regras de   │ │ Tributação │ │   Core    │               │
│  │  Negócio    │ │            │ │Contabilidade│              │
│  └─────────────┘ └────────────┘ └───────────┘               │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │                   WorkflowCore                        │    │
│  │           Processos e Aprovações                      │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ──────────── Núcleo de Negócio ─────────────               │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────┼─────────────────────────────────────┐
│              Persistência                                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Python (API REST, autenticação, orquestração)       │    │
│  └──────────────────────┬───────────────────────────────┘    │
│                         │                                     │
│  ┌──────────────────────┴───────────────────────────────┐    │
│  │  COBOL (Regras críticas, batch, legados)             │    │
│  └──────────────────────┬───────────────────────────────┘    │
│                         │                                     │
│  ┌──────────────────────┴───────────────────────────────┐    │
│  │  PostgreSQL (Persistência, relatórios, ACID)          │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

## Papéis de Cada Componente

### FiscalUI
- Framework de componentes **100% frontend**
- Consome APIs de todos os motores (Business, Fiscal, Accounting, Workflow)
- Renderização, interação, navegação, estado da UI, animações, acessibilidade
- Não sabe como o backend implementa — só enxerga JSON

### BusinessCore
- **Decide o que deve acontecer**
- Regras de negócio da operação (confirmar venda, aprovar compra, liberar pedido)
- Validação de limites, crédito, condições comerciais
- Orquestra a chamada dos demais motores
- **Não calcula imposto, não lança partidas, não aprova workflow**

### FiscalCore
- **Decide como tributar**
- NCM, CEST, CST, CSOSN, CFOP, alíquotas por UF, regimes tributários
- Cálculo de ICMS, PIS, COFINS, IPI, IBS, CBS
- Geração e validação de NF-e, NFC-e, NFSe, CT-e, MDF-e
- SPED Fiscal, SPED PIS/COFINS
- **Saída:** tributos calculados + documentos fiscais autorizados

### AccountingCore
- **Decide como lançar**
- Plano de Contas (REF), partidas dobradas, centro de custos, rateios
- Exercícios, abertura e encerramento, balancetes
- Balanço Patrimonial, DRE, DMPL, DFC
- Livro Diário, Livro Razão
- SPED Contábil (ECD), SPED ECF (contábil-fiscal)
- **Entrada:** recebe tributos do FiscalCore + dados da operação
- **Não recalcula impostos** — só transforma eventos em lançamentos

### WorkflowCore
- **Decide o fluxo e as aprovações**
- Máquina de estados para cada processo (pedido, compra, NF-e)
- Aprovações em cascata, níveis de alçada
- Notificações, prazos, escalonamento
- Histórico de auditoria de cada transição
- **Não contém regra de negócio, não tributa, não contabiliza**

### Python (API Layer)
- REST API para os motores
- Autenticação, autorização, rate limiting
- Orquestração entre motores (roteia chamadas)
- Integrações externas (SEFAZ, bancos, correios)

### COBOL
- Regras críticas de alta confiabilidade
- Processamento batch de grande volume
- Sistemas legados validados por décadas

### PostgreSQL
- Banco relacional único
- Dados estruturados, integridade referencial, ACID
- Relatórios e consultas cruzadas entre todos os domínios

## Contratos Entre Motores

### BusinessCore → FiscalCore
```json
{
  "operacao": "venda",
  "itens": [
    { "produto": "ARROZ-5KG", "quantidade": 10, "valor_unitario": 22.90, "ncm": "1006.30.11" }
  ],
  "cliente": { "uf": "SP", "regime": "simples_nacional" },
  "emitente": { "uf": "SP", "crt": 1 }
}
```

### FiscalCore → AccountingCore
```json
{
  "periodo": "2026-07",
  "eventos": [{
    "id": "NFe-000123",
    "tipo": "venda",
    "valor_produto": 10000.00,
    "tributos": {
      "icms": 1800.00,
      "pis": 165.00,
      "cofins": 760.00
    },
    "cfop": "5.102",
    "cst_icms": "00"
  }]
}
```

### AccountingCore — lançamentos gerados
```
D  Clientes (1.1.01.001)                     R$ 10.000,00
C  Receita de Vendas (3.1.01.001)            R$  7.275,00
C  ICMS a Recolher (2.1.01.001)              R$  1.800,00
C  PIS a Recolher (2.1.01.002)               R$    165,00
C  COFINS a Recolher (2.1.01.003)            R$    760,00
```

### WorkflowCore — estados do processo
```
Pedido → Pendente Aprovação → Aprovado → Faturado → Entregue
                                       → Rejeitado → Cancelado
```

## Princípios da Arquitetura

```
1. Independência total entre motores
   BusinessCore não sabe o que é ICMS.
   FiscalCore não sabe o que é partida dobrada.
   AccountingCore não sabe o que é aprovação.
   WorkflowCore não sabe o que é regra de negócio.

2. Responsabilidade única
   Cada motor faz exatamente uma coisa.
   Business decide. Fiscal tributa. Accounting lança. Workflow aprova.

3. API first
   Toda comunicação é via contrato JSON explícito.
   Nenhum motor chama o outro diretamente — sempre via API/mensageria.

4. Frontend cego de backend
   FiscalUI consome JSON — não importa quem produz.
   Motores podem ser reescritos sem impacto na interface.

5. Cada motor com seu ciclo de vida
   FiscalCore → legislação tributária (SEFAZ, NCM, alíquotas)
   AccountingCore → NBC TG, plano de contas, ECD/ECF
   WorkflowCore → regras de processo da empresa
   BusinessCore → regras de negócio do cliente
```

## Fluxo de uma Requisição Típica (Venda)

```
Usuário finaliza pedido no FiscalUI
        │
        ▼
FiscalUI → POST /api/pedidos (JSON)
        │
        ▼
BusinessCore → valida regras (crédito, estoque, condições)
            → aprova pedido
        │
        ▼
BusinessCore → chama FiscalCore
            →  POST /api/fiscal/calcular
        │
        ▼
FiscalCore → consulta NCM, CST, alíquotas
           → calcula ICMS, PIS, COFINS
           → autoriza NF-e na SEFAZ
        │
        ▼
FiscalCore → retorna tributos + NF-e autorizada
        │
        ▼
BusinessCore → chama AccountingCore
            →  POST /api/contabil/lancar
        │
        ▼
AccountingCore → recebe tributos
              → identifica contas
              → gera partidas dobradas
        │
        ▼
BusinessCore → chama WorkflowCore
            →  POST /api/workflow/avancar
        │
        ▼
WorkflowCore → avança estado: Pedido → Faturado
             → notifica usuário
        │
        ▼
FiscalUI → exibe NF-e autorizada + status do pedido
```

## Níveis de Maturidade

A arquitetura conceitual completa (UBMC, UBP, UBSB, Event Store, CQRS, Event Sourcing, Saga, Kafka) está documentada como **visão de futuro** — o mapa completo da cidade.

A implementação segue três níveis, evoluindo conforme a demanda real:

### N1 — MVP (agora)

```
HTML/CSS/JS → Controllers → Use Cases → BusinessCore → Repositories → PostgreSQL
                                                      ↓
                                           Domain Event → Dispatcher → Listeners
                                                                  ↓
                                                          Event Log (tabela)
```

O que está incluso:
- BusinessCore completo (entidades, VOs, agregados, regras)
- Dispatcher interno (Mediator pattern, ~10 classes)
- Event Log em tabela PostgreSQL (`event_log`)
- FiscalCore, AccountingCore, WorkflowCore no mesmo processo
- Python + COBOL + PostgreSQL
- Auditoria via tabelas de histórico

O que **não** está incluso:
- ❌ Kafka / RabbitMQ / NATS
- ❌ Service Bus / Registry / Discovery
- ❌ CQRS / Event Sourcing
- ❌ Saga Pattern
- ❌ Microsserviços
- ❌ Streaming

### N2 — Plataforma (próximo ciclo)

Adiciona:
- APIs públicas versionadas
- Filas de processamento para tarefas pesadas (SPED, fechamento)
- Cache (Redis)
- Observabilidade (OpenTelemetry, Prometheus)
- Sistema de plugins

Núcleo permanece inalterado.

### N3 — Enterprise (futuro)

Adiciona quando houver demanda real:
- Service Bus (Kafka / RabbitMQ)
- Event Streaming
- CQRS + Event Sourcing
- Saga Pattern para transações distribuídas
- Registry / Discovery
- Escalabilidade horizontal
- Microsserviços por Core

---

**Arquivo:** `docs/ARCHITECTURE.md`
**Versão:** 4.0
**Data:** 2026-07-25
