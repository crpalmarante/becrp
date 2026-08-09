# RFC-6005 - Landed Costs

| Field | Value |
|--------|-------|
| RFC | 6005 |
| Name | Landed Costs |
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

This RFC defines the **Landed Costs** module of the Retail Platform.

The module is responsible for allocating additional acquisition costs to inventory, producing a more accurate inventory valuation.

Landed Costs increase inventory value without changing inventory quantity.

---

# 2. Motivation

The purchase price alone rarely represents the real acquisition cost of inventory.

Additional expenses may include:

- Freight
- Insurance
- Customs Duties
- Import Fees
- Handling
- Storage
- Brokerage
- Other Acquisition Expenses

These costs must be distributed across inventory according to configurable allocation rules.

---

# 3. Responsibilities

The Landed Costs module is responsible for:

- registering additional acquisition costs;
- allocating costs to inventory;
- updating inventory valuation;
- creating Cost Ledger entries;
- preserving complete financial traceability.

---

# 4. Non Responsibilities

The Landed Costs module does not:

- receive inventory;
- execute inventory movements;
- modify inventory quantities;
- calculate inventory balances;
- generate supplier invoices.

Those responsibilities belong to other domains.

---

# 5. Principles

Landed Costs follow these principles.

## Financial Only

Landed Costs affect inventory value only.

Inventory quantities never change.

---

## Traceable

Every allocated amount can be traced back to its originating expense.

---

## Configurable

Allocation rules are configurable.

---

## Auditable

Every allocation is permanently recorded.

---

## Reproducible

Cost allocation must always produce deterministic results.

---

# 6. Cost Sources

Typical Landed Cost sources include:

- Freight
- Insurance
- Customs Duties
- Import Taxes
- Port Charges
- Warehouse Charges
- Brokerage Fees
- Packaging
- Other Acquisition Expenses

Organizations may define additional cost sources.

---

# 7. Allocation Rules

Supported allocation strategies include:

- Equal Distribution
- Quantity
- Weight
- Volume
- Purchase Value
- Manual Allocation

Additional allocation methods may be introduced.

---

# 8. Allocation Process

```
Purchase

↓

Inventory Received

↓

Landed Cost Registered

↓

Allocation Rule

↓

Cost Allocation

↓

Cost Ledger

↓

Inventory Valuation
```

Inventory quantity remains unchanged.

---

# 9. Cost Allocation

Each allocation records:

- originating expense;
- allocation rule;
- allocated amount;
- affected products;
- timestamps.

Allocated values become part of inventory cost.

---

# 10. Cost Ledger Integration

Every successful allocation generates Cost Ledger Entries.

Example:

```
Freight

$500

↓

Allocated

↓

Cost Ledger Entry
```

Historical records remain immutable.

---

# 11. Inventory Valuation

Allocated Landed Costs immediately affect inventory valuation.

Examples:

- Average Cost
- FIFO Layers
- Standard Cost Adjustments (when applicable)

The actual effect depends on the configured costing method.

---

# 12. Events

Published events include:

```
landed.cost.created

landed.cost.allocated

inventory.cost.updated
```

Events represent completed financial facts.

---

# 13. Audit

Every Landed Cost allocation records:

- originating document;
- allocation method;
- affected products;
- allocated values;
- responsible process;
- timestamps.

Allocation history is immutable.

---

# 14. Dependencies

Depends on:

- RFC-6000 - Cost & Valuation Architecture
- RFC-6001 - Cost Ledger
- RFC-6002 - Costing Methods
- RFC-6003 - Cost Layers
- RFC-6004 - Inventory Valuation

Referenced by:

- RFC-6006 - Inventory Revaluation
- RFC-6007 - Accounting Integration
- RFC-6008 - Cost Analytics

---

# 15. Principles

The Landed Costs module follows these principles:

- Additional acquisition costs become part of inventory value.
- Inventory quantities never change.
- Allocation is fully traceable.
- Allocation methods are configurable.
- Financial history is immutable.
- Cost allocation is reproducible.

---

# 16. Final Considerations

The Landed Costs module ensures that inventory valuation reflects the true acquisition cost of products rather than only their purchase price.

By separating operational inventory management from acquisition cost allocation, the platform provides accurate inventory valuation, stronger financial reporting and complete auditability while maintaining a clean separation of responsibilities.

This RFC reinforces the platform principle:

> **Simple is always better than complex.**
