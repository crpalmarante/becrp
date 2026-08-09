# RFC-5007 - Storage Locations

| Field | Value |
|--------|-------|
| RFC | 5007 |
| Name | Storage Locations |
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

This RFC defines the **Storage Locations** module of the Inventory domain.

A Storage Location represents the physical or logical place where inventory exists.

Every inventory movement transfers products from one Storage Location to another.

Storage Locations belong to exactly one Warehouse.

---

# 2. Motivation

Warehouses are composed of multiple storage areas.

Examples include:

- Receiving Area
- Quality Inspection
- Storage
- Picking
- Packing
- Shipping
- Returns
- Scrap

Representing these areas explicitly enables complete inventory traceability and flexible warehouse operations.

---

# 3. Responsibilities

The Storage Locations module is responsible for:

- defining storage locations;
- organizing warehouse hierarchy;
- validating location relationships;
- exposing locations to inventory operations;
- publishing structural events.

---

# 4. Non Responsibilities

The module does not:

- move inventory;
- reserve inventory;
- calculate balances;
- execute warehouse workflows;
- validate business documents.

These responsibilities belong to other Inventory modules.

---

# 5. Storage Location Concept

A Storage Location is the smallest inventory container managed by the Inventory domain.

Products always exist inside a Storage Location.

A Warehouse is a collection of Storage Locations.

---

# 6. Location Structure

Each Storage Location contains:

```
StorageLocation

----------------------------

id

warehouse_id

parent_location

code

name

location_type

status
```

Each location belongs to exactly one Warehouse.

---

# 7. Hierarchy

Locations are hierarchical.

Example:

```
Warehouse

├── Receiving

├── Storage

│   ├── Aisle A

│   │   ├── Shelf 01

│   │   └── Shelf 02

│   └── Aisle B

├── Picking

├── Packing

└── Shipping
```

Hierarchy depth is configurable.

---

# 8. Location Types

Supported location types include:

Internal

- Receiving
- Storage
- Picking
- Packing
- Shipping
- Production
- Quality

External

- Supplier
- Customer
- Transit

Virtual

- Inventory Adjustment
- Scrap
- Lost
- Returns

Additional types may be introduced without changing the Inventory Core.

---

# 9. Status

Every Storage Location follows a lifecycle.

```
Active

↓

Suspended

↓

Closed
```

Closed locations cannot receive new inventory movements.

---

# 10. Business Rules

The Inventory domain validates:

- warehouse ownership;
- valid parent hierarchy;
- unique location code within a warehouse;
- valid location type;
- valid status transition.

---

# 11. Inventory Relationship

Inventory always belongs to one Storage Location.

Example:

```
Warehouse

↓

Storage Location

↓

Inventory Ledger

↓

Inventory Projection
```

Balances are calculated per Storage Location.

Warehouse balances are aggregated projections.

---

# 12. Internal Movements

Moving inventory inside the same Warehouse still requires Stock Movements.

Example:

```
Receiving

↓

Storage

↓

Picking

↓

Packing

↓

Shipping
```

Every physical movement is explicitly recorded.

---

# 13. External Locations

External locations represent entities outside the organization.

Examples:

```
Supplier

↓

Receiving
```

```
Shipping

↓

Customer
```

Inventory movements involving external locations remain fully traceable.

---

# 14. Events

Published events include:

```
storage.location.created

storage.location.updated

storage.location.suspended

storage.location.closed
```

Events describe structural changes only.

---

# 15. Traceability

Each Storage Location records:

- warehouse;
- hierarchy;
- configuration;
- status changes;
- responsible user;
- timestamps.

History is immutable.

---

# 16. Audit

Every structural modification records:

- previous value;
- new value;
- timestamp;
- responsible user.

Audit records are immutable.

---

# 17. Dependencies

Depends on:

- RFC-5000 - Inventory Architecture
- RFC-5001 - Inventory Core
- RFC-5003 - Stock Movements
- RFC-5005 - Inventory Ledger
- RFC-5006 - Warehouse Management

Referenced by:

- RFC-5008 - Lots and Serials
- RFC-5009 - Physical Counting
- RFC-5010 - Inventory Workspace
- RFC-5011 - Replenishment Engine
- RFC-5012 - Inventory Event Model

---

# 18. Principles

Storage Locations follow these principles:

- Products always exist inside Storage Locations.
- Warehouses organize Storage Locations.
- Every movement changes Storage Locations.
- Every location belongs to exactly one Warehouse.
- Hierarchies are configurable.
- Every structural change is auditable.

---

# 19. Final Considerations

Storage Locations provide the physical structure of the Inventory domain.

By explicitly modeling every inventory location, the platform supports simple warehouses, advanced distribution centers and manufacturing environments while preserving complete traceability and operational consistency.

This RFC reinforces the platform principle:

> **Simple is always better than complex.**
