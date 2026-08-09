# RFC-6003 - Cost Layers

| Field | Value |
|--------|-------|
| RFC | 6003 |
| Name | Cost Layers |
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

This RFC defines the **Cost Layers** module of the Retail Platform.

Cost Layers represent the financial composition of inventory by preserving the origin, quantity and unit cost of inventory entries.

They provide the foundation for advanced costing methods such as FIFO and Specific Cost.

---

# 2. Motivation

Inventory value is not always represented by a single unit cost.

Different inventory entries may have different acquisition costs.

Example:

```
10 units × $100

20 units × $110

15 units × $95
```

Each inventory entry creates an independent Cost Layer.

Costing methods determine how these layers are consumed.

---

# 3. Responsibilities

The Cost Layers module is responsible for:

- creating cost layers;
- maintaining remaining quantities;
- supporting layer consumption;
- preserving historical costs;
- supplying data to costing methods.

---

# 4. Non Responsibilities

The Cost Layers module does not:

- execute inventory movements;
- calculate inventory balances;
- select costing methods;
- generate accounting entries;
- manage warehouses.

These responsibilities belong to other modules.

---

# 5. Layer Principles

Cost Layers follow these principles.

## Immutable Origin

A Cost Layer always preserves its original acquisition cost.

---

## Partial Consumption

A layer may be partially consumed.

Remaining quantity continues available.

---

## Historical Integrity

Consumed quantities remain historically traceable.

---

## Independent

Each layer evolves independently.

---

## Auditable

Every consumption is permanently recorded.

---

# 6. Layer Creation

A Cost Layer is created whenever inventory enters the organization.

Typical origins include:

- Purchase
- Manufacturing
- Customer Return
- Inventory Adjustment
- Transfer with Cost Impact

Each origin creates one or more Cost Layers.

---

# 7. Layer Structure

Each Cost Layer contains:

```
CostLayer

----------------------------

id

product_id

warehouse_id

origin_reference

cost_method

original_quantity

remaining_quantity

unit_cost

currency

created_at

status
```

Layers are immutable except for remaining quantity.

---

# 8. Layer Consumption

Costing Methods consume Cost Layers according to their own rules.

Example (FIFO):

```
Layer 1

10 × $100

↓

Consumed

↓

0 Remaining
```

```
Layer 2

20 × $110

↓

Remaining

20
```

Consumption never modifies historical unit cost.

---

# 9. Remaining Quantity

Each layer tracks:

- original quantity;
- consumed quantity;
- remaining quantity.

A layer is considered closed when its remaining quantity reaches zero.

---

# 10. Layer Lifecycle

```
Created

↓

Available

↓

Partially Consumed

↓

Fully Consumed

↓

Archived
```

Archived layers remain available for historical analysis.

---

# 11. Cost Traceability

Every Cost Layer references:

- originating Inventory Operation;
- Inventory Ledger Entry;
- Cost Ledger Entry;
- product;
- warehouse;
- timestamps.

Complete financial traceability is preserved.

---

# 12. Cost Reconstruction

Inventory valuation may be reconstructed by replaying Cost Layers.

Example:

```
Cost Layers

↓

Replay

↓

Inventory Value
```

Historical valuation remains deterministic.

---

# 13. Events

Published events include:

```
cost.layer.created

cost.layer.partially_consumed

cost.layer.closed
```

Events represent completed financial facts.

---

# 14. Audit

Every Cost Layer records:

- originating event;
- responsible process;
- remaining quantity;
- timestamps.

Historical information is immutable.

---

# 15. Dependencies

Depends on:

- RFC-6000 - Cost & Valuation Architecture
- RFC-6001 - Cost Ledger
- RFC-6002 - Costing Methods

Referenced by:

- RFC-6004 - Inventory Valuation
- RFC-6005 - Landed Costs
- RFC-6006 - Inventory Revaluation
- RFC-6007 - Accounting Integration

---

# 16. Principles

Cost Layers follow these principles:

- Every inventory entry creates financial history.
- Historical unit cost never changes.
- Cost Layers may be partially consumed.
- Remaining quantity is tracked independently.
- Financial traceability is mandatory.
- Layer history is immutable.

---

# 17. Final Considerations

Cost Layers provide the financial foundation required by advanced inventory costing strategies.

By separating cost composition from inventory movements, the platform supports deterministic valuation, historical reconstruction and flexible costing policies while maintaining a clean separation between operational inventory management and financial valuation.

This RFC reinforces the platform principle:

> **Simple is always better than complex.**
