# Business Platform
# BC-101 — Business Use Cases

**Documento:** BC-101
**Título:** Catálogo Universal de Casos de Uso
**Versão:** 2.0.0 (Draft)
**Status:** Arquitetura Executável
**Dependências:** BC-001 a BC-100

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

Definir como a plataforma executa uma intenção de negócio.

Um Use Case é responsável por transformar um **Command** em uma mudança válida no domínio.

```
Business Command → Use Case → Domain Services → Aggregate → Repository → Domain Events
```

O Use Case é o orquestrador da operação.

---

## Capítulo 2 — Responsabilidades

Um Use Case deve:

- Receber um Command
- Validar permissões
- Validar regras iniciais
- Carregar Agregados
- Chamar Domain Services quando necessário
- Executar operações no Aggregate
- Persistir alterações
- Publicar Domain Events
- Retornar um resultado

Ele **não** contém regras tributárias, cálculos complexos ou SQL.

---

## Capítulo 3 — Estrutura Canônica

Todo Use Case segue a mesma estrutura:

```
UseCase
├── Authorization
├── Validation
├── Load Aggregate
├── Execute
├── Persist
├── Publish Events
└── Response
```

---

## Capítulo 4 — Exemplo Geral

```
CreateOrderCommand
  ↓
CreateOrderUseCase
  ↓
OrderAggregate.create()
  ↓
OrderRepository.save()
  ↓
OrderCreated
```

---

## Capítulo 5 — Estrutura Interna

```
execute(command)
  ↓
authorize()
  ↓
validate()
  ↓
load()
  ↓
process()
  ↓
save()
  ↓
publish()
  ↓
respond()
```

Cada etapa tem uma única responsabilidade.

---

## Capítulo 6 — Catálogo Inicial

**Parties**
```
CreatePartyUseCase
UpdatePartyUseCase
ActivatePartyUseCase
DeactivatePartyUseCase
```

**Products**
```
CreateProductUseCase
UpdateProductUseCase
ChangePriceUseCase
DeactivateProductUseCase
```

**Customers**
```
CreateCustomerUseCase
UpdateCustomerUseCase
BlockCustomerUseCase
```

**Orders**
```
CreateOrderUseCase
AddOrderItemUseCase
RemoveOrderItemUseCase
ApproveOrderUseCase
CancelOrderUseCase
CompleteOrderUseCase
```

**Purchases**
```
CreatePurchaseOrderUseCase
ApprovePurchaseOrderUseCase
ReceivePurchaseOrderUseCase
```

**Inventory**
```
ReserveStockUseCase
TransferStockUseCase
AdjustStockUseCase
```

**Fiscal**
```
GenerateFiscalDocumentUseCase
TransmitFiscalDocumentUseCase
CancelFiscalDocumentUseCase
```

**Accounting**
```
PostJournalEntryUseCase
CloseAccountingPeriodUseCase
```

---

## Capítulo 7 — Exemplo Completo

**CreateOrderUseCase**

Entrada: `CreateOrderCommand`

```
1. Validar usuário
2. Validar cliente
3. Validar itens
4. Criar Aggregate
5. Persistir
6. Publicar OrderCreated
7. Retornar OrderId
```

---

## Capítulo 8 — Interface Padrão

Todos os Use Cases implementam:

```
IUseCase
├── execute(command)
```

Opcionalmente:
```
authorize()
validate()
process()
publish()
```

---

## Capítulo 9 — Resultado

Todo Use Case retorna um objeto padronizado:

```
UseCaseResult
├── Success
├── Data
├── Warnings
├── Errors
└── Events
```

Nunca retorna exceções como resposta funcional. Exceções são para falhas técnicas.

---

## Capítulo 10 — Integração com Eventos

```
Aggregate → Domain Events → Dispatcher → Listeners
```

O Use Case nunca conhece quem consumirá os eventos.

---

## Capítulo 11 — Tratamento de Erros

```
ValidationError
BusinessRuleViolation
Unauthorized
Conflict
NotFound
TechnicalFailure
```

Cada categoria possui um código e uma mensagem padronizados.

---

## Capítulo 12 — Transações

Cada Use Case representa uma unidade transacional.

```
BEGIN → Execute → Persist → Publish → COMMIT
```

Caso ocorra falha antes da persistência, a operação é revertida. Para publicação de eventos, recomenda-se o padrão Outbox.

---

## Capítulo 13 — Organização Física

```
business_core/
  use_cases/
    party/
      CreatePartyUseCase.py
      UpdatePartyUseCase.py
    order/
      CreateOrderUseCase.py
      ApproveOrderUseCase.py
      CancelOrderUseCase.py
    inventory/
      ReserveStockUseCase.py
      AdjustStockUseCase.py
```

Cada arquivo contém um único Use Case.

---

## Capítulo 14 — Modelo de Implementação

```
1. Receber Command
2. Autorizar
3. Validar
4. Carregar Aggregate
5. Executar operação
6. Persistir
7. Publicar Eventos
8. Retornar Resultado
```

---

## Capítulo 15 — Exemplo de Sequência

```
Usuário → CreateOrderCommand → CreateOrderUseCase → OrderAggregate → OrderRepository → PostgreSQL → OrderCreated → Dispatcher → Fiscal → Contabilidade → Workflow
```

---

## Capítulo 16 — Catálogo de Responsabilidades

| Camada | Responsabilidade |
|---|---|
| Command | Expressa intenção |
| Use Case | Orquestra a operação |
| Domain Service | Implementa regras compartilhadas |
| Aggregate | Garante consistência do domínio |
| Repository | Persiste o estado |
| Domain Event | Registra fatos ocorridos |
| Dispatcher | Notifica interessados |

---

## Capítulo 17 — Template Oficial

Todo novo Use Case deverá seguir este modelo:

```
Nome:
Objetivo:
Command de Entrada:
Permissões Necessárias:
Pré-condições:
Aggregate Principal:
Domain Services Utilizados:
Eventos Gerados:
Repositórios Utilizados:
Resultado Esperado:
Possíveis Erros:
```

---

## Próxima Etapa

```
BC-101A  Aggregate Catalog (antes de Services)
BC-101B  Repository Contracts
BC-102   Domain Services
BC-103   Workflow Engine
BC-104   Permission Model
BC-105   API Contracts
```

---

**Arquivo:** `docs/BC-101_USE_CASES.md`
**Versão:** 2.0.0
**Data:** 2026-07-25
