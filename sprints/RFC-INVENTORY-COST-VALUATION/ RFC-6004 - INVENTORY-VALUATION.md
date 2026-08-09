# RFC-6004 - Inventory Valuation

| Field | Value |
|--------|-------|
| RFC | 6004 |
| Name | Inventory Valuation |
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

This RFC defines the **Inventory Valuation** module of the Retail Platform.

The Inventory Valuation module is responsible for determining the financial value of inventory based on inventory quantities and the configured costing method.

It provides a consistent and auditable financial representation of inventory without modifying inventory quantities.

---

# 2. Motivation

Inventory management records physical quantities.

Financial management requires inventory values.

Inventory Valuation bridges these two domains by converting inventory balances into financial information.

Typical business questions include:

- What is the current inventory value?
- What was the inventory value on a specific date?
- What is the inventory value by warehouse?
- What is the inventory value by product category?
- What is the company's invested capital?

---

# 3. Responsibilities

The Inventory Valuation module is responsible for:

- calculating inventory value;
- exposing inventory valuation services;
- supporting historical valuation;
- consolidating inventory values;
- providing financial information for reporting and accounting.

---

# 4. Non Responsibilities

The Inventory Valuation module does not:

- execute inventory movements;
- calculate inventory quantities;
- create cost layers;
- define costing methods;
- manage warehouses;
- execute accounting postings.

Those responsibilities belong to their respective domains.

---

# 5. Principles

Inventory Valuation follows these principles.

## Read-Oriented

Inventory Valuation produces financial views without modifying inventory history.

---

## Deterministic

The same inventory state and costing policy always produce the same valuation.

---

## Independent

Inventory quantities remain independent from financial valuation.

---

## Auditable

Every valuation can be reproduced and verified.

---

## Configurable

Valuation respects the configured costing method.

---

# 6. Valuation Workflow

```
Inventory Ledger

↓

Inventory Balance

↓

Costing Method

↓

Cost Layers

↓

Inventory Valuation
```

The workflow remains identical regardless of the selected costing strategy.

---

# 7. Valuation Dimensions

Inventory may be valued by:

- Company
- Warehouse
- Storage Location
- Product
- Product Category
- Brand
- Supplier
- Lot
- Serial Number
- Date

Additional dimensions may be introduced.

---

# 8. Valuation Result

Each valuation includes:

```
Inventory Valuation

-------------------------

valuation_id

valuation_date

cost_method

currency

total_quantity

total_value

average_unit_cost

generated_at
```

The valuation is a calculated result.

It does not replace historical records.

---

# 9. Historical Valuation

Inventory value can be calculated for any historical date.

Example:

```
Inventory Value

↓

2026-07-31
```

Historical calculations are reproducible.

---

# 10. Financial Views

Typical valuation outputs include:

- Inventory Value by Warehouse
- Inventory Value by Category
- Inventory Value by Supplier
- Inventory Value by Product
- Inventory Value by Company
- Total Inventory Value

These views support operational and financial reporting.

---

# 11. Costing Independence

Inventory Valuation does not implement costing rules.

It consumes the result produced by the configured Costing Method.

Changing the costing policy does not require changes to the Inventory Valuation module.

---

# 12. Events

Published events include:

```
inventory.valuation.completed

inventory.value.updated

inventory.value.snapshot.created
```

Events represent completed valuation processes.

---

# 13. Audit

Every valuation records:

- valuation date;
- costing method;
- valuation scope;
- generated values;
- responsible process;
- timestamps.

Historical valuation remains reproducible.

---

# 14. Dependencies

Depends on:

- RFC-5005 - Inventory Ledger
- RFC-6000 - Cost & Valuation Architecture
- RFC-6001 - Cost Ledger
- RFC-6002 - Costing Methods
- RFC-6003 - Cost Layers

Referenced by:

- RFC-6005 - Landed Costs
- RFC-6006 - Inventory Revaluation
- RFC-6007 - Accounting Integration
- RFC-6008 - Cost Analytics

---

# 15. Principles

Inventory Valuation follows these principles:

- Inventory quantities remain unchanged.
- Financial valuation is deterministic.
- Valuation is reproducible.
- Costing strategies remain independent.
- Financial history is immutable.
- Inventory and financial domains remain decoupled.

---

# 16. Final Considerations

The Inventory Valuation module provides the financial interpretation of inventory without interfering with inventory operations.

By separating valuation from costing, inventory management and accounting, the platform achieves a modular architecture where each domain has a single responsibility.

Inventory remains responsible for physical quantities.

Cost & Valuation remains responsible for financial value.

This RFC reinforces the platform principle:

> **Simple is always better than complex.**
