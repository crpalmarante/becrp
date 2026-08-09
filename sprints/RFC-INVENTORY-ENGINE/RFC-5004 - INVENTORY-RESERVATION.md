# RFC-5004 - Stock Reservations

| Field | Value |
|--------|-------|
| RFC | 5004 |
| Name | Stock Reservations |
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

This RFC defines the **Stock Reservations** module of the Inventory domain.

A Stock Reservation temporarily allocates inventory for a future business operation without creating a physical stock movement.

Reservations ensure that inventory is available when the related operation is executed.

---

# 2. Motivation

Many business processes require inventory allocation before physical movement.

Examples include:

- Sales Orders
- Point of Sale
- Purchase Returns
- Manufacturing
- Internal Transfers
- Picking Operations

Separating reservations from stock movements improves inventory planning and prevents overallocation.

---

# 3. Responsibilities

The Stock Reservations module is responsible for:

- allocating available inventory;
- validating inventory availability;
- preventing overallocation;
- managing reservation lifecycle;
- releasing unused reservations;
- publishing reservation events.

---

# 4. Non Responsibilities

The module does not:

- move inventory;
- update inventory balances;
- generate ledger entries;
- execute picking;
- calculate replenishment;
- manage warehouses.

Those responsibilities belong to specialized modules.

---

# 5. Reservation Concept

A reservation represents a business commitment.

```
Available Stock

↓

Reserved Stock

↓

Future Stock Movement
```

Reservations never modify physical inventory.

---

# 6. Reservation Structure

Each reservation contains:

```
StockReservation

-------------------------

id

operation_id

product_id

warehouse_id

location_id

reserved_quantity

unit_of_measure

status

created_at

expires_at
```

Each reservation belongs to exactly one Inventory Operation.

---

# 7. Reservation Lifecycle

Every reservation follows the same lifecycle.

```
Requested

↓

Reserved

↓

Allocated

↓

Consumed
```

Exceptional states:

```
Released

Cancelled

Expired
```

Consumed reservations cannot be modified.

---

# 8. Availability Rules

A reservation is created only when:

- product exists;
- warehouse is valid;
- location is valid;
- requested quantity is available;
- operation is valid.

Unavailable inventory must never be reserved.

---

# 9. Reservation Policies

The platform supports configurable allocation policies.

Examples:

- FIFO (First In, First Out)
- FEFO (First Expired, First Out)
- LIFO (Last In, First Out)
- Manual Selection

Policy selection belongs to warehouse configuration.

---

# 10. Expiration

Reservations may expire.

Expired reservations automatically release inventory.

Expiration rules are configurable.

---

# 11. Partial Reservation

When sufficient inventory is unavailable:

```
Requested

100 Units

↓

Available

60 Units

↓

Reserved

60 Units

↓

Pending

40 Units
```

Partial reservations are allowed when permitted by business rules.

---

# 12. Reservation Release

Reservations are released when:

- operation is cancelled;
- reservation expires;
- operation completes without consumption;
- user releases reservation.

Released inventory immediately becomes available.

---

# 13. Reservation Consumption

Reservation consumption occurs during stock movement execution.

```
Reservation

↓

Stock Movement

↓

Reservation Closed
```

Consumption is atomic with movement execution.

---

# 14. Events

Published events include:

```
inventory.reservation.requested

inventory.reservation.created

inventory.reservation.allocated

inventory.reservation.released

inventory.reservation.expired

inventory.reservation.consumed

inventory.reservation.cancelled
```

Events represent business facts.

---

# 15. Traceability

Every reservation records:

- originating operation;
- product;
- warehouse;
- storage location;
- reserved quantity;
- timestamps;
- responsible user.

Reservation history is immutable.

---

# 16. Integrations

Reservations may be requested by:

- Sales
- Point of Sale
- Receiving
- Manufacturing
- Internal Transfers
- Delivery

External domains request reservations but never manipulate them directly.

---

# 17. Audit

Every lifecycle transition records:

- previous state;
- new state;
- timestamp;
- responsible user;
- triggering event.

Audit records are immutable.

---

# 18. Dependencies

Depends on:

- RFC-5000 - Inventory Architecture
- RFC-5001 - Inventory Core
- RFC-5002 - Inventory Operations
- RFC-5003 - Stock Movements

Referenced by:

- RFC-5005 - Inventory Ledger
- RFC-5009 - Physical Counting
- RFC-5010 - Inventory Workspace
- RFC-5012 - Inventory Event Model

---

# 19. Principles

The Stock Reservations module follows these principles:

- Reservation is not inventory movement.
- Reservation does not change physical stock.
- Reservations belong to Inventory Operations.
- Reserved inventory remains physically available until movement execution.
- Consumption occurs only during stock movement.
- Every reservation is fully traceable.

---

# 20. Final Considerations

Stock Reservations provide a reliable mechanism for allocating inventory before physical execution.

By separating reservation from movement, the platform supports advanced warehouse operations, prevents inventory conflicts and improves planning without compromising inventory integrity.

The module reinforces the platform principle:

> **Simple is always better than complex.**
