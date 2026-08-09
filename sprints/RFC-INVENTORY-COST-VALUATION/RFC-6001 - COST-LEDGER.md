# RFC-6001 - Cost Ledger

| Field | Value |
|--------|-------|
| RFC | 6001 |
| Name | Cost Ledger |
| Category | Cost & Valuation |
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

This RFC defines the **Cost Ledger** of the Retail Platform.

The Cost Ledger is the permanent and immutable financial history of inventory costs.

It records every cost-related event affecting inventory valuation and serves as the authoritative source for inventory cost history.

The Cost Ledger does not replace the Accounting General Ledger.

---

# 2. Motivation

Inventory quantities and inventory values evolve independently.

While the Inventory Ledger records physical inventory movements, the Cost Ledger records the financial impact of those movements.

This separation enables:

- complete cost traceability;
- reproducible cost calculations;
- multiple costing methods;
- financial auditing;
- historical inventory valuation.

---

# 3. Responsibilities

The Cost Ledger is responsible for:

- recording inventory cost events;
- maintaining immutable cost history;
- supporting cost reconstruction;
- providing historical valuation;
- supplying financial information to valuation services.

---

# 4. Non Responsibilities

The Cost Ledger does not:

- move inventory;
- reserve inventory;
- calculate inventory balances;
- execute accounting entries;
- manage warehouses;
- manage storage locations.

Those responsibilities belong to other domains.

---

# 5. Ledger Principles

The Cost Ledger follows these principles.

## Append Only

Ledger entries are never updated.

Corrections generate new entries.

---

## Immutable

Published entries cannot be modified.

---

## Event Driven

Entries originate from completed business events.

---

## Auditable

Every financial change is permanently recorded.

---

## Rebuildable

Inventory cost can always be reconstructed from Ledger history.

---

# 6. Ledger Entry

Every cost-related event generates one Cost Ledger Entry.

```
Completed Business Event

↓

Valuation Engine

↓

Cost Ledger Entry
```

Ledger persistence occurs only after successful valuation.

---

# 7. Ledger Structure

Each Cost Ledger Entry contains:

```
CostLedgerEntry

----------------------------

id

ledger_entry_id

inventory_operation_id

stock_movement_id

product_id

warehouse_id

cost_method

quantity

unit_cost

total_cost

currency

occurred_at

recorded_at
```

The structure may be extended without breaking compatibility.

---

# 8. Cost Projection

The Cost Ledger is the source for inventory valuation.

```
Cost Ledger

↓

Valuation Projection

↓

Inventory Value
```

Financial reports consume projections instead of raw Ledger entries.

---

# 9. Cost Corrections

Historical records are never modified.

Corrections generate additional Ledger Entries.

Example:

```
Original Cost

100 × 20.00

↓

Cost Adjustment

+150.00

↓

Updated Inventory Value
```

The complete history remains preserved.

---

# 10. Traceability

Every Cost Ledger Entry references:

- Inventory Operation;
- Stock Movement;
- Inventory Ledger Entry;
- Product;
- Warehouse;
- Cost Method;
- Business Timestamp;
- Recording Timestamp.

The financial origin of every inventory value is traceable.

---

# 11. Historical Reconstruction

Inventory valuation can be rebuilt for any historical date.

Example:

```
Cost Ledger

↓

Replay

↓

Inventory Value

↓

2026-07-31
```

Historical valuation is deterministic.

---

# 12. Performance

The Cost Ledger is optimized for writes.

Financial projections may be:

- calculated on demand;
- cached;
- materialized;
- periodically refreshed.

Projection strategy never changes Ledger history.

---

# 13. Integrations

The Cost Ledger receives information from:

- Inventory Ledger;
- Valuation Engine;
- Landed Costs;
- Inventory Revaluation.

The Cost Ledger supplies information to:

- Inventory Valuation;
- Accounting Integration;
- Financial Reporting;
- Analytics;
- Cost Dashboards.

External modules never modify Ledger entries.

---

# 14. Events

Published events include:

```
cost.ledger.entry.created

inventory.cost.updated

inventory.value.projected
```

Events represent completed financial facts.

---

# 15. Audit

Every Cost Ledger Entry records:

- originating event;
- valuation method;
- responsible process;
- timestamps;
- immutable financial values.

The Cost Ledger forms part of the financial audit trail.

---

# 16. Dependencies

Depends on:

- RFC-5005 - Inventory Ledger
- RFC-5012 - Inventory Event Model
- RFC-6000 - Cost & Valuation Architecture

Referenced by:

- RFC-6002 - Costing Methods
- RFC-6003 - Cost Layers
- RFC-6004 - Inventory Valuation
- RFC-6005 - Landed Costs
- RFC-6006 - Inventory Revaluation
- RFC-6007 - Accounting Integration
- RFC-6008 - Cost Analytics

---

# 17. Principles

The Cost Ledger follows these principles:

- Financial history is immutable.
- Cost changes create new Ledger entries.
- Inventory quantities remain independent from inventory values.
- Cost reconstruction is deterministic.
- Ledger entries are append-only.
- Every financial value is traceable.

---

# 18. Final Considerations

The Cost Ledger is the permanent financial history of inventory valuation.

By separating financial history from physical inventory history, the platform enables robust costing strategies, reliable auditing and independent financial evolution while preserving a clean separation of responsibilities.

The Cost Ledger reinforces the platform principle:

> **Simple is always better than complex.**
