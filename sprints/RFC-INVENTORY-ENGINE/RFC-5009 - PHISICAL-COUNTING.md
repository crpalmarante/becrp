# RFC-5009 - Physical Counting

| Field | Value |
|--------|-------|
| RFC | 5009 |
| Name | Physical Counting |
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

This RFC defines the **Physical Counting** module of the Inventory domain.

The module is responsible for measuring the physical inventory available in storage locations and comparing it with the projected inventory maintained by the Inventory domain.

Physical Counting never changes inventory directly.

Inventory corrections are performed through Inventory Operations.

---

# 2. Motivation

Inventory discrepancies are inevitable.

Typical causes include:

- Human errors
- Damaged goods
- Theft
- Losses
- Counting mistakes
- Receiving errors
- Shipping errors

The platform must detect, record and reconcile these differences while preserving complete inventory history.

---

# 3. Responsibilities

The Physical Counting module is responsible for:

- creating counting sessions;
- assigning counting areas;
- recording counted quantities;
- comparing physical and projected inventory;
- generating discrepancy reports;
- requesting inventory adjustments.

---

# 4. Non Responsibilities

The module does not:

- update inventory balances;
- execute stock movements;
- modify ledger entries;
- reserve inventory;
- execute replenishment.

These responsibilities belong to other Inventory modules.

---

# 5. Counting Session

Every counting activity occurs inside a Counting Session.

```
Counting Session

↓

Counting Tasks

↓

Count Results

↓

Difference Analysis

↓

Adjustment Request
```

A session provides the business context for the inventory count.

---

# 6. Counting Types

Supported counting types include:

- Full Inventory
- Cycle Count
- Spot Count
- Location Count
- Product Count
- Lot Count
- Serial Count

Additional counting strategies may be introduced without changing the Inventory Core.

---

# 7. Counting Structure

Each Counting Session contains:

```
CountingSession

----------------------------

id

warehouse_id

status

counting_type

started_at

completed_at

responsible_user
```

---

# 8. Counting Task

A Counting Session is divided into one or more Counting Tasks.

Each task may represent:

- one warehouse;
- one storage location;
- one aisle;
- one shelf;
- one product group.

Tasks enable parallel counting.

---

# 9. Counting Result

Each counting result records:

- product;
- storage location;
- counted quantity;
- unit of measure;
- lot;
- serial number;
- counting timestamp;
- responsible user.

Results are immutable after confirmation.

---

# 10. Difference Analysis

The platform compares:

```
Projected Quantity

↓

Physical Quantity

↓

Difference
```

Possible outcomes:

- Match
- Gain
- Loss

Differences are recorded but do not immediately affect inventory.

---

# 11. Inventory Adjustment

Inventory discrepancies generate Adjustment Requests.

Example:

```
Difference Detected

↓

Adjustment Request

↓

Inventory Operation

↓

Stock Movement

↓

Inventory Ledger

↓

Updated Projection
```

Inventory history remains preserved.

---

# 12. Double Counting

The platform may require multiple independent counts.

Example:

First Count

↓

Second Count

↓

Supervisor Review

↓

Approval

↓

Adjustment Request

Required counting strategy is configurable.

---

# 13. Events

Published events include:

```
inventory.count.started

inventory.count.completed

inventory.count.review.required

inventory.adjustment.requested

inventory.adjustment.approved
```

Events represent completed business facts.

---

# 14. Traceability

Every counting session records:

- warehouse;
- storage locations;
- counted products;
- counted quantities;
- differences;
- responsible users;
- timestamps.

The complete history remains available.

---

# 15. Audit

Every counting action records:

- user;
- timestamp;
- device (optional);
- counting result;
- approval history.

Audit records are immutable.

---

# 16. Dependencies

Depends on:

- RFC-5000 - Inventory Architecture
- RFC-5002 - Inventory Operations
- RFC-5003 - Stock Movements
- RFC-5005 - Inventory Ledger
- RFC-5006 - Warehouse Management
- RFC-5007 - Storage Locations
- RFC-5008 - Lots and Serials

Referenced by:

- RFC-5010 - Inventory Workspace
- RFC-5011 - Replenishment Engine
- RFC-5012 - Inventory Event Model

---

# 17. Principles

Physical Counting follows these principles:

- Counting measures reality.
- Counting never changes inventory.
- Differences generate Adjustment Requests.
- Inventory corrections occur through Inventory Operations.
- Every count is auditable.
- Every adjustment is traceable.

---

# 18. Final Considerations

Physical Counting provides an accurate comparison between physical inventory and the inventory projection maintained by the platform.

By separating counting from inventory adjustment, the platform preserves immutable inventory history while ensuring operational flexibility and complete traceability.

This RFC reinforces the platform principle:

> **Simple is always better than complex.**
