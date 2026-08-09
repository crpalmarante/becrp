# RFC-6002 - Costing Methods

| Field | Value |
|--------|-------|
| RFC | 6002 |
| Name | Costing Methods |
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

This RFC defines the **Costing Methods** architecture of the Retail Platform.

The Costing Methods module provides a standardized framework for calculating inventory costs using configurable costing strategies.

The architecture separates costing policies from inventory operations, allowing organizations to adopt different financial policies without affecting the Inventory domain.

---

# 2. Motivation

Different organizations apply different inventory costing methods.

Examples include:

- FIFO
- Moving Average
- Standard Cost
- Specific Cost
- Last Purchase Cost

The platform must support multiple costing methods without changing business operations or inventory management.

---

# 3. Responsibilities

The Costing Methods module is responsible for:

- selecting the costing strategy;
- calculating inventory cost;
- exposing costing services;
- ensuring deterministic calculations;
- supporting multiple costing policies.

---

# 4. Non Responsibilities

The module does not:

- manage inventory;
- execute inventory movements;
- maintain inventory balances;
- post accounting entries;
- manage warehouses;
- execute purchasing operations.

These responsibilities belong to other domains.

---

# 5. Architecture Principles

The Costing Methods architecture follows these principles.

## Strategy Based

Each costing method is implemented as an independent strategy.

---

## Configurable

Organizations choose the costing policy through configuration.

---

## Deterministic

The same inputs always produce the same calculated cost.

---

## Independent

Changing the costing method never modifies Inventory history.

---

## Extensible

New costing methods may be added without changing existing implementations.

---

# 6. Costing Engine

The Costing Engine coordinates all cost calculations.

```
Inventory Event

↓

Costing Engine

↓

Costing Method

↓

Calculated Cost
```

The engine delegates calculations to the selected strategy.

---

# 7. Supported Methods

The architecture supports:

- FIFO
- Moving Average
- Standard Cost
- Specific Cost
- Last Purchase Cost

Future methods may be added without affecting the Costing Engine.

---

# 8. Strategy Selection

Each legal entity, company or inventory policy may define its costing method.

Example:

```
Company A

↓

FIFO
```

```
Company B

↓

Moving Average
```

The Costing Engine automatically selects the configured strategy.

---

# 9. Cost Calculation

Every inventory valuation follows the same workflow.

```
Inventory Ledger

↓

Costing Engine

↓

Selected Strategy

↓

Cost Ledger

↓

Inventory Valuation
```

The workflow remains identical regardless of the costing method.

---

# 10. Cost Consistency

Cost calculations must be:

- reproducible;
- auditable;
- deterministic;
- versionable.

Historical calculations are preserved.

---

# 11. Strategy Independence

Each costing strategy operates independently.

Strategies never interact directly.

Each strategy owns its own calculation rules.

---

# 12. Events

Published events include:

```
cost.method.selected

cost.calculated

cost.recalculated
```

Events represent completed financial calculations.

---

# 13. Audit

Every calculation records:

- costing strategy;
- calculation inputs;
- calculation result;
- responsible process;
- timestamps.

Calculation history is immutable.

---

# 14. Dependencies

Depends on:

- RFC-6000 - Cost & Valuation Architecture
- RFC-6001 - Cost Ledger

Referenced by:

- RFC-6003 - Cost Layers
- RFC-6004 - Inventory Valuation
- RFC-6005 - Landed Costs
- RFC-6006 - Inventory Revaluation
- RFC-6007 - Accounting Integration

---

# 15. Principles

The Costing Methods module follows these principles:

- Costing strategies are independent.
- Inventory remains unaware of costing policies.
- Calculations are deterministic.
- Strategies are replaceable.
- Historical calculations remain reproducible.
- Costing is fully auditable.

---

# 16. Final Considerations

The Costing Methods module provides a flexible and extensible framework for inventory costing.

By isolating costing policies behind a common architecture, the platform enables organizations to adopt different financial practices while preserving a stable Inventory domain and a consistent Cost & Valuation model.

This RFC reinforces the platform principle:

> **Simple is always better than complex.**
