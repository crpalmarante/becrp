# Business Platform
# BC-100 — Business Commands

**Documento:** BC-100
**Título:** Catálogo Universal de Business Commands
**Versão:** 2.0.0 (Draft)
**Status:** Arquitetura Executável
**Dependências:** BC-001 a BC-006

---

## Capítulo 1 — Objetivo

Definir todos os comandos oficiais da plataforma.

Todo comportamento do sistema começa com um **Command**.

```
Usuário → CreateOrder → BusinessCore → OrderCreated
```

Os **Commands** representam intenções. Os **Events** representam fatos.

---

## Capítulo 2 — Princípios

Todo Command deve ser:

- **Imperativo** (verbo no infinitivo em inglês para padronização técnica)
- Atômico
- Idempotente quando aplicável
- Validável
- Auditável
- Versionável

Exemplos: `CreateCustomer`, `UpdateCustomer`, `ApproveOrder`, `CancelOrder`, `ReceivePayment`, `IssueInvoice`

---

## Capítulo 3 — Estrutura Canônica

Todo Command herda da estrutura base:

```
BusinessCommand
├── CommandId
├── CommandType
├── Version
├── IssuedAt
├── CorrelationId
├── CausationId
├── TenantId
├── OrganizationId
├── UserId
├── Payload
└── Metadata
```

Essa estrutura será serializada pelo UBMC.

---

## Capítulo 4 — Ciclo de Vida

```
Frontend
  │
  ▼
Business Command
  │
  ▼
Validation
  │
  ▼
Use Case
  │
  ▼
Domain Service
  │
  ▼
Aggregate
  │
  ▼
Repository
  │
  ▼
Domain Event
```

O Command nunca altera diretamente o banco de dados.

---

## Capítulo 5 — Catálogo de Commands

**Parties**
```
CreateParty
UpdateParty
ActivateParty
DeactivateParty
MergeParties
ArchiveParty
```

**Products**
```
CreateProduct
UpdateProduct
DeactivateProduct
ChangeProductPrice
ChangeProductClassification
```

**Customers**
```
CreateCustomer
UpdateCustomer
BlockCustomer
UnblockCustomer
```

**Suppliers**
```
CreateSupplier
UpdateSupplier
ApproveSupplier
SuspendSupplier
```

**Orders**
```
CreateOrder
AddOrderItem
RemoveOrderItem
UpdateOrderItem
SubmitOrder
ApproveOrder
RejectOrder
CancelOrder
CompleteOrder
```

**Purchases**
```
CreatePurchaseOrder
ApprovePurchaseOrder
ReceivePurchaseOrder
CancelPurchaseOrder
```

**Inventory**
```
ReserveStock
ReleaseStock
TransferStock
AdjustStock
CountInventory
```

**Finance**
```
CreateReceivable
ReceivePayment
CreatePayable
PaySupplier
ReversePayment
```

**Accounting**
```
PostJournalEntry
ReverseJournalEntry
CloseAccountingPeriod
OpenAccountingPeriod
```

**Fiscal**
```
GenerateFiscalDocument
ValidateFiscalDocument
TransmitFiscalDocument
CancelFiscalDocument
GenerateSPED
CalculateTaxes
```

---

## Capítulo 6 — Estrutura de um Command

Exemplo conceitual:

```
Command: CreateOrder

Payload:
├── CustomerId
├── Items
├── PaymentTerms
├── ShippingAddress
├── Currency
├── Discount
└── RequestedDate
```

O Command contém apenas os dados necessários para executar a intenção.

---

## Capítulo 7 — Responsabilidades

**O Command:**
- ✔ Expressa uma intenção
- ✔ Transporta dados
- ✔ Possui identificação
- ✔ Pode ser validado
- ✔ Pode ser auditado

**O Command não:**
- ✘ Calcula impostos
- ✘ Persiste dados
- ✘ Chama diretamente outros Cores
- ✘ Publica eventos por conta própria

---

## Capítulo 8 — Resultado

Um Command pode produzir:

```
Success
ValidationError
BusinessRuleViolation
Unauthorized
Conflict
NotFound
```

Em caso de sucesso, um ou mais Domain Events serão publicados.

---

## Capítulo 9 — Exemplo de Fluxo

```
CreateOrder
  ↓
Use Case
  ↓
Order Aggregate
  ↓
Repository
  ↓
OrderCreated
  ↓
Event Dispatcher
  ↓
FiscalCore → AccountingCore → WorkflowCore
```

Esse fluxo será implementado inicialmente no mesmo processo, utilizando um Dispatcher interno.

---

## Capítulo 10 — Interface Base

Todos os Commands seguirão uma interface comum:

```
ICommand
├── getCommandId()
├── getCommandType()
├── getVersion()
├── validate()
├── getPayload()
└── getMetadata()
```

Em Python: classe abstrata ou dataclass. Em COBOL: COPYBOOK padronizado. Em JavaScript: objeto tipado.

---

## Capítulo 11 — Organização do Código

```
business_core/
│
├── commands/
│   ├── party/
│   ├── product/
│   ├── customer/
│   ├── supplier/
│   ├── order/
│   ├── purchase/
│   ├── inventory/
│   ├── finance/
│   ├── accounting/
│   └── fiscal/
│
├── use_cases/
├── domain/
├── repositories/
├── events/
├── services/
└── shared/
```

---

## Capítulo 12 — Próximo Documento

**BC-101 — Business Use Cases**

Ligar cada comando ao comportamento do sistema:

```
CreateOrder           → CreateOrderUseCase
ApproveOrder          → ApproveOrderUseCase
ReceivePayment        → ReceivePaymentUseCase
GenerateFiscalDocument → GenerateFiscalDocumentUseCase
```

---

**Arquivo:** `docs/BC-100_COMMANDS.md`
**Versão:** 2.0.0
**Data:** 2026-07-25
