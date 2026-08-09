# RFC-6000 - Cost & Valuation Architecture

| Field | Value |
|--------|-------|
| RFC | 6000 |
| Name | Cost & Valuation Architecture |
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

This RFC defines the **Cost & Valuation** domain of the Retail Platform.

The domain is responsible for determining, maintaining and reporting the financial value of inventory.

It operates independently from the Inventory domain while consuming inventory events and business transactions.

The Cost & Valuation domain never manages physical inventory.

---

# 2. Motivation

Inventory management answers operational questions such as:

- How many items exist?
- Where are they located?
- Which lot or serial number do they belong to?

Financial management answers different questions:

- What is the inventory worth?
- What is the cost of each unit?
- What is the value of inventory by warehouse?
- What is the company's invested capital?
- What is the cost of goods sold?

These concerns belong to different business domains and must evolve independently.

---

# 3. Responsibilities

The Cost & Valuation domain is responsible for:

- inventory valuation;
- product costing;
- cost history;
- cost layers;
- landed costs;
- inventory revaluation;
- accounting integration;
- financial reporting.

---

# 4. Non Responsibilities

The Cost & Valuation domain does not:

- receive inventory;
- move inventory;
- reserve inventory;
- calculate inventory balances;
- manage warehouses;
- manage storage locations;
- validate inventory operations.

These responsibilities belong to the Inventory domain.

---

# 5. Domain Principles

The Cost & Valuation domain follows these principles.

## Financial Independence

Inventory quantities and inventory values are independent concepts.

---

## Immutable History

Every cost change generates a new historical record.

Historical values are never modified.

---

## Event Driven

Cost calculations are triggered by completed business events.

---

## Configurable Costing

Different organizations may adopt different costing methods.

The architecture must support multiple costing strategies without changing the Inventory domain.

---

## Auditability

Every valuation decision must be fully traceable.

---

# 6. Domain Model

```
Inventory

↓

Inventory Ledger

↓

Cost & Valuation

├── Cost Ledger

├── Cost Layers

├── Valuation Engine

├── Landed Costs

├── Revaluation

└── Accounting Integration
```

Inventory remains the owner of physical quantities.

Cost & Valuation becomes the owner of financial values.

---

# 7. Inputs

The domain consumes information from:

- Inventory Ledger;
- Inventory Operations;
- Purchasing;
- Manufacturing;
- Accounting Policies;
- Configuration.

No direct modification of Inventory data is allowed.

---

# 8. Outputs

The domain provides:

- inventory value;
- product cost;
- warehouse value;
- inventory valuation reports;
- accounting entries;
- financial analytics.

---

# 9. Costing Strategies

The architecture supports multiple costing methods.

Examples include:

- FIFO
- Moving Average
- Standard Cost
- Specific Cost
- Last Purchase Cost

Additional strategies may be introduced without affecting existing implementations.

---

# 10. Integration

Cost & Valuation integrates with:

Inventory

- Inventory Ledger
- Inventory Events

Purchasing

- Purchase Documents
- Supplier Costs

Manufacturing

- Production Costs
- Consumption

Accounting

- General Ledger
- Financial Statements

Analytics

- Dashboards
- Reports
- KPIs

---

# 11. Audit

Every valuation process records:

- originating event;
- costing method;
- calculated values;
- responsible process;
- timestamps.

Financial history is immutable.

---

# 12. Dependencies

Depends on:

- RFC-5000 - Inventory Architecture
- RFC-5005 - Inventory Ledger
- RFC-5012 - Inventory Event Model

Referenced by:

- RFC-6001 - Cost Ledger
- RFC-6002 - Costing Methods
- RFC-6003 - Cost Layers
- RFC-6004 - Inventory Valuation
- RFC-6005 - Landed Costs
- RFC-6006 - Inventory Revaluation
- RFC-6007 - Accounting Integration
- RFC-6008 - Cost Analytics

---

# 13. Principles

The Cost & Valuation Architecture follows these principles:

- Inventory owns quantities.
- Cost & Valuation owns financial values.
- Cost history is immutable.
- Cost calculations are reproducible.
- Multiple costing methods are supported.
- Business rules remain independent from accounting policies.

---

# 14. Final Considerations

The Cost & Valuation domain complements the Inventory domain by providing the financial interpretation of physical inventory.

By separating operational inventory management from financial valuation, the platform achieves greater flexibility, clearer business boundaries and stronger auditability.

This architecture allows organizations to adopt different costing policies without impacting inventory operations, while remaining aligned with the platform principle:

> **Simple is always better than complex.**
