# RFC-5002 - Inventory Operations

| Field | Value |
|--------|-------|
| RFC | 5002 |
| Name | Inventory Operations |
| Category | Inventory |
| Status | Draft |
| Version | 1.0 |

---

## Platform Philosophy

> **Simple is always better than complex.**
> Simples é sempre melhor do que complexo.

Design systems that are easy to understand, easy to maintain, easy to extend, and easy to use.
Avoid unnecessary abstractions. Prefer explicit behavior over hidden magic.
Every feature should solve a real business problem.
Performance and maintainability always come first.

---

# 1. Objective

This RFC defines the **Inventory Operations** module.

An Inventory Operation represents a complete business transaction that affects inventory.

It is the Aggregate Root of the Inventory domain.

Every inventory movement belongs to exactly one Inventory Operation.

---

# 2. Motivation

Business processes do not manipulate inventory directly.

Instead, they request inventory operations.

Examples include:

- Receiving goods
- Delivering products
- Internal transfers
- Inventory adjustments
- Manufacturing
- Customer returns
- Supplier returns

The Inventory Operation provides a unified model for all these processes.

---

# 3. Responsibilities

The Inventory Operations module is responsible for:

- creating inventory operations;
- validating operation lifecycle;
- coordinating stock movements;
- managing operation state;
- publishing domain events;
- maintaining operation history.

---

# 4. Non Responsibilities

The module does not:

- calculate inventory balances;
- store ledger entries;
- reserve stock;
- manage warehouses;
- manage storage locations;
- perform replenishment calculations.

These responsibilities belong to specialized modules.

---

# 5. Operation Types

Supported operation types include:

Inbound

- Receiving
- Production Output
- Customer Return
- Inventory Gain

Outbound

- Delivery
- Production Consumption
- Supplier Return
- Inventory Loss

Internal

- Internal Transfer
- Relocation
- Cycle Count Adjustment

New operation types may be introduced without changing the domain model.

---

# 6. Operation Lifecycle

Every Inventory Operation follows the same lifecycle.

```
Draft

↓

Ready

↓

Executing

↓

Completed
```

Exceptional states:

```
Cancelled

Failed
```

Completed operations are immutable.

---

# 7. Aggregate Structure

```
Inventory Operation

│

├── Stock Movements

├── Reservations

├── Assignments

├── Audit Records

└── Domain Events
```

All child entities belong to one Inventory Operation.

---

# 8. Operation Structure

Each operation contains:

```
InventoryOperation

-------------------------

id

operation_type

status

warehouse_id

reference_document

requested_by

created_at

completed_at
```

Business-specific metadata may be attached without changing the core model.

---

# 9. Reference Document

Every operation may reference its business origin.

Examples:

Receiving

Purchase Order

POS Sale

Sales Order

Manufacturing Order

Transfer Request

The Inventory domain never owns these documents.

---

# 10. Validation Rules

The Inventory Core validates:

- operation type;
- warehouse consistency;
- movement consistency;
- status transitions;
- required information;
- quantity consistency.

Invalid operations cannot proceed.

---

# 11. State Transitions

Allowed transitions:

```
Draft

↓

Ready

↓

Executing

↓

Completed
```

Cancellation is allowed before completion.

Completed operations cannot be reopened.

Corrections require a new operation.

---

# 12. Traceability

Every operation records:

- originating document;
- responsible user;
- warehouse;
- timestamps;
- generated movements;
- generated events.

The operation history is immutable.

---

# 13. Domain Events

Published events include:

```
inventory.operation.created

inventory.operation.ready

inventory.operation.started

inventory.operation.completed

inventory.operation.failed

inventory.operation.cancelled
```

Events describe business facts only.

---

# 14. Integrations

Inventory Operations receive requests from:

Receiving

Purchase

Point of Sale

Sales

Manufacturing

Returns

Physical Counting

Inventory Operations coordinate processing without executing business logic from external domains.

---

# 15. Audit

Every lifecycle transition records:

- previous state;
- new state;
- responsible user;
- timestamp;
- triggering business event.

Audit records are immutable.

---

# 16. Dependencies

Depends on:

- RFC-5000 - Inventory Architecture
- RFC-5001 - Inventory Core

Referenced by:

- RFC-5003 - Stock Movements
- RFC-5004 - Stock Reservations
- RFC-5005 - Inventory Ledger
- RFC-5008 - Lots and Serials
- RFC-5009 - Physical Counting
- RFC-5012 - Inventory Event Model

---

# 17. Principles

Inventory Operations follow these principles:

- Every inventory change belongs to one operation.
- Operations coordinate business transactions.
- Completed operations are immutable.
- Events represent completed business facts.
- Inventory owns inventory behavior.
- Business documents remain outside the Inventory domain.

---

# 18. Final Considerations

Inventory Operations establish the business boundary of the Inventory domain.

By making the Inventory Operation the Aggregate Root, the platform groups all related inventory actions under a single business transaction while preserving modularity, auditability and scalability.

This model allows different business domains to interact with Inventory through a consistent interface while maintaining the platform principle:

> **Simple is always better than complex.**
