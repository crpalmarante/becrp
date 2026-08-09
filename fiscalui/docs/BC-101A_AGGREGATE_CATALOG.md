# Business Platform
# BC-101A — Aggregate Catalog

**Documento:** BC-101A
**Título:** Catálogo de Agregados Executáveis
**Versão:** 1.0.0 (Draft)
**Status:** Arquitetura Executável
**Dependências:** BC-005, BC-101

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

Descrever cada Aggregate Root da plataforma em detalhes executáveis: limites, responsabilidades, invariantes, atributos, eventos e relacionamentos.

Este documento é a ponte entre o modelo conceitual (BC-005) e a implementação em código.

---

## Capítulo 2 — Estrutura de Cada Agregado

```
Aggregate: Nome
├── Aggregate Root
├── Descrição
├── Limites
├── Invariantes
├── Atributos da Raiz
├── Entidades Internas
├── Value Objects
├── States
├── Events (produzidos)
├── Commands (recebidos)
├── Domain Services (utilizados)
└── Repository
```

---

## Capítulo 3 — Party

| Campo | Valor |
|---|---|
| Aggregate Root | `Party` |
| Descrição | Pessoa física ou jurídica que se relaciona com a organização |
| Limites | Identificação, contatos, endereços, papéis, documento |

**Invariantes:**
- Deve ter ao menos um nome
- Deve ter ao menos um papel (Role)
- Documento deve ser único por organização

**Atributos da Raiz:**
```
PartyId
PartyType (Person | Organization)
Name
LegalName
DisplayName
Document
State (Active | Suspended | Archived)
CreatedAt
UpdatedAt
```

**Entidades Internas:**
```
PartyRole (Role, StartDate, EndDate)
PartyAddress (Address, Type, IsMain)
PartyContact (Contact, Type, IsMain)
PartyDocument (DocumentType, Value)
```

**Eventos:**
```
PartyCreated
PartyUpdated
PartyActivated
PartySuspended
PartyArchived
```

**Commands:**
```
CreateParty
UpdateParty
ActivateParty
SuspendParty
ArchiveParty
```

---

## Capítulo 4 — Customer

| Campo | Valor |
|---|---|
| Aggregate Root | `Customer` (especialização de Party com role Customer) |
| Descrição | Cliente da organização |
| Limites | Dados comerciais, crédito, condições |

**Invariantes:**
- Customer deve estar vinculado a uma Party existente
- Limite de crédito não pode ser negativo
- Cliente bloqueado não pode comprar

**Atributos da Raiz:**
```
CustomerId
PartyId
CreditLimit
UsedCredit
PaymentTerms
PriceTable
State (Active | Blocked | Suspended)
```

**Eventos:**
```
CustomerCreated
CustomerUpdated
CustomerBlocked
CustomerUnblocked
CreditLimitUpdated
```

**Commands:**
```
CreateCustomer
UpdateCustomer
BlockCustomer
UnblockCustomer
UpdateCreditLimit
```

---

## Capítulo 5 — Product

| Campo | Valor |
|---|---|
| Aggregate Root | `Product` |
| Descrição | Produto ou serviço comercializado |
| Limites | Dados gerais, classificação, precificação, atributos |

**Invariantes:**
- Código único por organização
- Nome obrigatório
- Unidade de medida obrigatória
- Preço não pode ser negativo

**Atributos da Raiz:**
```
ProductId
Code
Name
Description
CategoryId
UnitOfMeasure
Price
Currency
Ncm
Cest
State (Active | Inactive | Discontinued)
```

**Entidades Internas:**
```
ProductAttribute (Name, Value)
ProductImage (Url, IsMain)
ProductPrice (PriceList, Value, ValidFrom, ValidTo)
ProductClassification (Type, Code)
```

**Eventos:**
```
ProductCreated
ProductUpdated
ProductDiscontinued
PriceChanged
ProductClassified
```

**Commands:**
```
CreateProduct
UpdateProduct
ChangeProductPrice
ChangeProductClassification
DeactivateProduct
```

---

## Capítulo 6 — Order

| Campo | Valor |
|---|---|
| Aggregate Root | `Order` |
| Descrição | Pedido de venda |
| Limites | Itens, totais, descontos, histórico |

**Invariantes:**
- Deve ter ao menos 1 item
- Cliente deve estar ativo
- Não pode ser faturado se cancelado
- Não pode receber itens após faturamento

**States:**
```
Draft → Submitted → Approved → Invoiced → Completed
                                  → Rejected → Cancelled
```

**Atributos da Raiz:**
```
OrderId
CustomerId
OrderDate
Status
TotalAmount
DiscountAmount
NetAmount
Currency
PaymentCondition
ShippingAddress
Notes
```

**Entidades Internas:**
```
OrderItem (ProductId, Quantity, Price, Discount, Total)
OrderHistory (Status, ChangedBy, ChangedAt)
OrderAttachment (FileId, FileName, Type)
```

**Eventos:**
```
OrderCreated
OrderSubmitted
OrderApproved
OrderRejected
OrderCancelled
OrderCompleted
ItemAdded
ItemRemoved
```

**Commands:**
```
CreateOrder
SubmitOrder
ApproveOrder
RejectOrder
CancelOrder
CompleteOrder
AddOrderItem
RemoveOrderItem
```

---

## Capítulo 7 — PurchaseOrder

| Campo | Valor |
|---|---|
| Aggregate Root | `PurchaseOrder` |
| Descrição | Pedido de compra |
| Limites | Itens, fornecedor, condições, recebimento |

**Invariantes:**
- Deve ter ao menos 1 item
- Fornecedor deve estar ativo
- Quantidade recebida não pode exceder a pedida

**States:**
```
Draft → Submitted → Approved → PartiallyReceived → Received → Completed
                                  → Rejected → Cancelled
```

**Atributos da Raiz:**
```
PurchaseOrderId
SupplierId
OrderDate
ExpectedDate
Status
TotalAmount
Currency
PaymentCondition
```

**Entidades Internas:**
```
PurchaseOrderItem (ProductId, Quantity, ReceivedQuantity, Price, Total)
PurchaseOrderHistory
```

**Eventos:**
```
PurchaseOrderCreated
PurchaseOrderApproved
PurchaseOrderReceived
PurchaseOrderCancelled
```

**Commands:**
```
CreatePurchaseOrder
ApprovePurchaseOrder
ReceivePurchaseOrder
CancelPurchaseOrder
```

---

## Capítulo 8 — InventoryMovement

| Campo | Valor |
|---|---|
| Aggregate Root | `InventoryMovement` |
| Descrição | Movimentação de estoque |
| Limites | Produto, quantidade, origem, destino, tipo |

**Invariantes:**
- Quantidade deve ser > 0
- Produto deve existir
- Origem e destino devem ser válidos
- Estoque não pode ficar negativo (se política proibir)

**Atributos da Raiz:**
```
MovementId
ProductId
WarehouseId
MovementType (In | Out | Transfer | Adjustment)
Quantity
UnitOfMeasure
Batch
Date
Reason
ReferenceId
```

**Eventos:**
```
StockReceived
StockTransferred
StockAdjusted
StockReserved
StockReleased
```

**Commands:**
```
ReceiveStock
TransferStock
AdjustStock
ReserveStock
ReleaseStock
```

---

## Capítulo 9 — FiscalDocument

| Campo | Valor |
|---|---|
| Aggregate Root | `FiscalDocument` |
| Descrição | Documento fiscal (NF-e, NFC-e, NFSe, CT-e) |
| Limites | Dados fiscais, itens, tributos, autorização |

**Invariantes:**
- Deve ter ao menos 1 item
- Deve estar vinculado a uma operação
- SEFAZ autorização é obrigatória para emissão

**States:**
```
Draft → Validated → Signed → Authorized → Cancelled
                  → Rejected → Denied
```

**Atributos da Raiz:**
```
DocumentId
DocumentType (NFe | NFCe | NFSe | CTe)
OperationType
IssuerId
CustomerId
Status
AccessKey
Number
Series
IssueDate
TotalValue
Tributos
```

**Entidades Internas:**
```
FiscalItem (ProductId, NCM, CFOP, CST, Quantity, Value, TaxValues)
FiscalReference (DocumentId, Reason)
```

**Eventos:**
```
FiscalDocumentGenerated
FiscalDocumentValidated
FiscalDocumentSigned
FiscalDocumentAuthorized
FiscalDocumentRejected
FiscalDocumentCancelled
```

**Commands:**
```
GenerateFiscalDocument
ValidateFiscalDocument
TransmitFiscalDocument
CancelFiscalDocument
```

---

## Capítulo 10 — JournalEntry

| Campo | Valor |
|---|---|
| Aggregate Root | `JournalEntry` |
| Descrição | Lançamento contábil (partidas dobradas) |
| Limites | Débito, crédito, conta, centro de custo, histórico |

**Invariantes:**
- Total débito = Total crédito
- Conta deve existir no plano de contas
- Período deve estar aberto

**States:**
```
Draft → Posted → Reversed
```

**Atributos da Raiz:**
```
EntryId
EntryDate
PeriodId
Description
TotalDebit
TotalCredit
Status
CreatedAt
PostedAt
```

**Entidades Internas:**
```
JournalLine (AccountId, Debit, Credit, CostCenterId, Historic)
```

**Eventos:**
```
JournalEntryCreated
JournalEntryPosted
JournalEntryReversed
```

**Commands:**
```
PostJournalEntry
ReverseJournalEntry
```

---

## Capítulo 11 — Aggregate × Core

| Aggregate | BusinessCore | FiscalCore | AccountingCore | WorkflowCore |
|---|---|---|---|---|
| Party | Raiz | | | |
| Customer | Raiz | | | |
| Product | Raiz | Extende | Extende | |
| Order | Raiz | Extende | Extende | Extende |
| PurchaseOrder | Raiz | Extende | Extende | Extende |
| InventoryMovement | Raiz | | | |
| FiscalDocument | | Raiz | Extende | Extende |
| JournalEntry | | | Raiz | |

---

## Capítulo 12 — Organização Física

```
domain/
├── party/
│   ├── Party.py
│   ├── PartyRole.py
│   ├── PartyAddress.py
│   ├── PartyContact.py
│   ├── PartyState.py
│   └── IPartyRepository.py
│
├── customer/
│   ├── Customer.py
│   ├── CustomerState.py
│   └── ICustomerRepository.py
│
├── product/
│   ├── Product.py
│   ├── ProductPrice.py
│   ├── ProductAttribute.py
│   ├── ProductState.py
│   └── IProductRepository.py
│
├── order/
│   ├── Order.py
│   ├── OrderItem.py
│   ├── OrderState.py
│   └── IOrderRepository.py
│
├── inventory/
│   ├── InventoryMovement.py
│   └── IInventoryRepository.py
│
├── fiscal/
│   ├── FiscalDocument.py
│   ├── FiscalItem.py
│   └── IFiscalRepository.py
│
└── accounting/
    ├── JournalEntry.py
    ├── JournalLine.py
    └── IJournalRepository.py
```

---

## Capítulo 13 — Próximos Passos

```
BC-101B  Repository Contracts
BC-102   Domain Services
BC-103   Workflow Engine
BC-104   Permission Model
BC-105   API Contracts
```

---

**Arquivo:** `docs/BC-101A_AGGREGATE_CATALOG.md`
**Versão:** 1.0.0
**Data:** 2026-07-25
