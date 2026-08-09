# RFC-5001 - Inventory Core

| Field | Value |
|--------|-------|
| RFC | 5001 |
| Name | Inventory Core |
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

This RFC defines the **Inventory Core** of the Retail Platform.

The Inventory Core represents the central business model responsible for managing inventory operations.

It establishes the domain language, aggregate boundaries, business entities and invariants used throughout the Inventory domain.

The Inventory Core contains business rules only.

It is independent of user interface, persistence and infrastructure.

---

# 2. Motivation

Inventory is a strategic business domain shared by multiple processes.

Examples:

- Receiving
- Purchasing
- Point of Sale
- Sales
- Manufacturing
- Delivery
- Returns
- Inventory Counting

Without a common business model, inventory logic becomes duplicated and inconsistent.

The Inventory Core provides a single, authoritative model for inventory operations.

---

# 3. Responsibilities

The Inventory Core is responsible for:

- defining inventory operations;
- maintaining inventory consistency;
- validating inventory invariants;
- coordinating stock movements;
- managing reservations;
- controlling inventory state;
- publishing domain events.

---

# 4. Non Responsibilities

The Inventory Core does not:

- manage warehouses;
- execute physical counting;
- calculate replenishment;
- perform fiscal processing;
- perform financial processing;
- execute purchasing workflows;
- execute receiving workflows.

These responsibilities belong to specialized modules.

---

# 5. Ubiquitous Language

The Inventory domain uses the following business terms.

### Inventory Operation

A business operation affecting inventory.

Examples:

- Receiving
- Delivery
- Internal Transfer
- Adjustment
- Production
- Return

---

### Stock Movement

The atomic inventory transaction.

Represents movement of inventory between locations.

---

### Reservation

Temporary allocation of inventory without physical movement.

---

### Inventory Ledger

Immutable history of completed inventory movements.

---

### Inventory Balance

Current stock projection calculated from the ledger.

---

### Warehouse

Logical inventory facility.

---

### Storage Location

Physical or logical area inside a warehouse.

---

### Lot

Group of products sharing common manufacturing characteristics.

---

### Serial Number

Unique identifier assigned to one inventory unit.

---

# 6. Aggregate Root

The Inventory Core is organized around one aggregate.

```
Inventory Operation
```

The Inventory Operation is the Aggregate Root.

All inventory changes occur through it.

No external module may manipulate internal entities directly.

---

# 7. Aggregate Structure

```
Inventory Operation

│

├── Stock Movements

├── Reservations

├── Lot Assignments

├── Serial Assignments

└── Operation Events
```

Child entities cannot exist without their parent operation.

---

# 8. Inventory Operation

Each Inventory Operation represents one business transaction.

Attributes include:

```
id

operation_type

status

warehouse

created_at

completed_at

reference_document
```

The operation owns all related inventory entities.

---

# 9. Operation Types

Initial operation types include:

- Receiving
- Delivery
- Internal Transfer
- Inventory Adjustment
- Production
- Return
- Cycle Count

New operation types may be introduced without modifying the domain model.

---

# 10. Operation States

Every Inventory Operation follows a defined lifecycle.

```
Draft

↓

Ready

↓

Reserved

↓

In Progress

↓

Completed

↓

Cancelled
```

Completed operations become immutable.

---

# 11. Domain Invariants

The Inventory Core enforces the following rules.

- Every movement belongs to exactly one operation.
- Completed operations cannot be modified.
- Reservations cannot exceed available inventory.
- Ledger entries are immutable.
- Every inventory change generates an audit record.
- Inventory balance is derived from movements.
- Every operation has one responsible warehouse.

---

# 12. Identity

Each Inventory Operation has a globally unique identifier.

Example:

```
INV-OP-2026-000001
```

Identifiers are immutable.

---

# 13. Business Rules

The Inventory Core validates:

- operation lifecycle;
- movement consistency;
- reservation consistency;
- warehouse consistency;
- quantity validation;
- unit of measure compatibility.

Business rules remain independent from infrastructure.

---

# 14. Domain Events

Typical events include:

```
inventory.operation.created

inventory.operation.ready

inventory.operation.reserved

inventory.operation.started

inventory.operation.completed

inventory.operation.cancelled
```

Events represent completed business facts.

---

# 15. Audit

Every Inventory Operation records:

- creation;
- status changes;
- responsible user;
- timestamps;
- related business document;
- generated events.

Audit history is immutable.

---

# 16. Dependencies

Depends on:

- RFC-5000 - Inventory Architecture

Referenced by:

- RFC-5002 - Warehouse Management
- RFC-5003 - Storage Locations
- RFC-5004 - Stock Movements
- RFC-5005 - Stock Reservations
- RFC-5006 - Inventory Ledger
- RFC-5007 - Lots and Serials
- RFC-5008 - Inventory Operations
- RFC-5009 - Physical Counting
- RFC-5010 - Inventory Workspace
- RFC-5011 - Replenishment Engine
- RFC-5012 - Inventory Event Model

---

# 17. Principles

The Inventory Core follows the Retail Platform principles.

- Simple is always better than complex.
- Business rules belong to the domain.
- Inventory owns inventory.
- Operations are immutable after completion.
- Events represent business facts.
- Every inventory change is traceable.

---

# 18. Final Considerations

The Inventory Core defines the business foundation of the Inventory domain.

By organizing inventory around the **Inventory Operation** aggregate, the platform separates business intent from implementation details while preserving consistency, traceability and scalability.

This model provides a stable foundation for all inventory-related modules and reinforces the platform principle:

> **Simple is always better than complex.**
