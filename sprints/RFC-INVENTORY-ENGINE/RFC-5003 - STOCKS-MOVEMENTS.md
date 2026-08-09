# RFC-5003 - Stock Movements

| Field | Value |
|--------|-------|
| RFC | 5003 |
| Name | Stock Movements |
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

This RFC defines the **Stock Movements** module of the Inventory domain.

A Stock Movement represents the atomic inventory transaction.

It records the physical movement of inventory between two locations.

Every inventory change is represented by one or more Stock Movements.

---

# 2. Motivation

Business operations frequently require inventory movement.

Examples include:

- Receiving goods
- Delivering products
- Internal transfers
- Manufacturing
- Returns
- Inventory adjustments

Representing every movement explicitly provides complete traceability and supports inventory reconstruction.

---

# 3. Responsibilities

The Stock Movements module is responsible for:

- representing physical inventory movement;
- validating movement consistency;
- maintaining movement lifecycle;
- publishing movement events;
- generating ledger entries after completion.

---

# 4. Non Responsibilities

The module does not:

- own inventory balances;
- calculate stock availability;
- manage reservations;
- execute replenishment;
- manage warehouses;
- coordinate business workflows.

Those responsibilities belong to other Inventory modules.

---

# 5. Movement Structure

Each Stock Movement contains:

```
StockMovement

----------------------------

id

operation_id

product_id

source_location

destination_location

quantity

unit_of_measure

status

created_at

completed_at
```

Each movement belongs to exactly one Inventory Operation.

---

# 6. Movement Types

Typical movement types include:

Inbound

- Supplier Receiving
- Production Output
- Customer Return

Outbound

- Customer Delivery
- Supplier Return
- Production Consumption

Internal

- Warehouse Transfer
- Location Transfer
- Inventory Adjustment

Movement type is determined by the parent Inventory Operation.

---

# 7. Source and Destination

Every Stock Movement defines:

```
Source Location

↓

Destination Location
```

Examples:

```
Supplier

↓

Receiving Area
```

```
Receiving Area

↓

Storage
```

```
Storage

↓

Picking
```

```
Picking

↓

Customer
```

Both locations are mandatory.

---

# 8. Movement Lifecycle

Every movement follows the same lifecycle.

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

Completed movements become immutable.

---

# 9. Business Rules

The module validates:

- valid source location;
- valid destination location;
- positive quantity;
- compatible unit of measure;
- valid product;
- valid warehouse relationship.

Invalid movements cannot proceed.

---

# 10. Quantity Rules

Movement quantity must always be greater than zero.

Zero or negative quantities are not permitted.

Unit conversion follows product configuration.

---

# 11. Immutability

Completed movements cannot be modified.

Business corrections require new compensating movements.

Example:

```
Move A

↓

Completed

↓

Correction

↓

Move B
```

History is never rewritten.

---

# 12. Ledger Integration

Every completed movement generates one Inventory Ledger entry.

The Ledger becomes the permanent inventory history.

Movement completion and Ledger creation must occur atomically.

---

# 13. Traceability

Each movement records:

- originating operation;
- originating business document;
- source location;
- destination location;
- product;
- quantity;
- execution timestamps;
- responsible user.

The complete history must remain available.

---

# 14. Events

Published events include:

```
inventory.movement.created

inventory.movement.ready

inventory.movement.started

inventory.movement.completed

inventory.movement.failed

inventory.movement.cancelled
```

Events describe completed business facts.

---

# 15. Integrations

Stock Movements are created by:

- Inventory Operations
- Receiving
- Purchase
- Point of Sale
- Sales
- Manufacturing
- Physical Counting

External domains never manipulate movements directly.

---

# 16. Audit

Every lifecycle transition records:

- previous status;
- new status;
- responsible user;
- timestamp;
- related operation.

Audit records are immutable.

---

# 17. Dependencies

Depends on:

- RFC-5000 - Inventory Architecture
- RFC-5001 - Inventory Core
- RFC-5002 - Inventory Operations

Referenced by:

- RFC-5004 - Stock Reservations
- RFC-5005 - Inventory Ledger
- RFC-5008 - Lots and Serials
- RFC-5012 - Inventory Event Model

---

# 18. Principles

The Stock Movements module follows these principles:

- Every inventory change is a movement.
- Every movement belongs to one Inventory Operation.
- Completed movements are immutable.
- Corrections generate new movements.
- Ledger entries are derived from completed movements.
- Every movement is fully traceable.

---

# 19. Final Considerations

Stock Movements represent the atomic transactions of the Inventory domain.

By modeling every physical inventory change explicitly, the platform guarantees complete traceability, auditability and consistency while preserving clear separation between business operations and inventory execution.

The module reinforces the platform principle:

> **Simple is always better than complex.**
