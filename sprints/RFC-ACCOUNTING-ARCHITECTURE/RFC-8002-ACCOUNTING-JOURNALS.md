# RFC-8002 - Accounting Journals

| Field | Value |
|--------|-------|
| RFC | 8002 |
| Name | Accounting Journals |
| Category | Accounting Core |
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

This RFC defines the Accounting Journals architecture within the Accounting Core domain.

Accounting Journals organize accounting transactions by their operational purpose, origin and accounting context.

A Journal provides structure, separation and control over accounting activities.

---

# 2. Motivation

A modern business platform generates accounting events from multiple domains:

- Sales;
- Purchasing;
- Receiving;
- Inventory;
- Cost & Valuation;
- Loan Management;
- Finance.

Without journal separation, accounting transactions become difficult to analyze, audit and manage.

Accounting Journals provide a clear classification layer before accounting entries are created.

---

# 3. Responsibilities

Accounting Journals are responsible for:

- grouping accounting transactions;
- defining accounting transaction categories;
- controlling journal configuration;
- maintaining journal numbering;
- defining default accounting behavior;
- supporting audit organization.

---

# 4. Non Responsibilities

Accounting Journals do not:

- create accounting entries;
- validate debit and credit balance;
- post transactions;
- define the chart of accounts;
- execute operational processes.

These responsibilities belong to other Accounting Core components.

---

# 5. Journal Concept

An Accounting Journal represents a logical accounting book.

Examples:

```
Sales Journal

Purchase Journal

Inventory Journal

Bank Journal

Cash Journal

General Journal
```

Each journal represents a specific business purpose.

---

# 6. Standard Journal Types

## Sales Journal

Used for:

- customer invoices;
- revenue transactions;
- sales adjustments.

---

## Purchase Journal

Used for:

- supplier invoices;
- purchase transactions;
- supplier obligations.

---

## Inventory Journal

Used for:

- stock valuation;
- inventory adjustments;
- cost movements.

---

## Bank Journal

Used for:

- receipts;
- payments;
- bank transactions.

---

## Cash Journal

Used for:

- cash movements;
- petty cash operations.

---

## General Journal

Used for:

- manual adjustments;
- corrections;
- exceptional accounting events.

---

# 7. Journal Structure

Each journal contains:

```
Journal

├── Identification
│
├── Configuration
│
├── Numbering
│
└── Security Rules
```

---

# 8. Journal Properties

A Journal contains:

- Journal Code;
- Journal Name;
- Journal Type;
- Company;
- Currency;
- Status;
- Sequence Configuration;
- Default Accounts;
- Allowed Users.

---

# 9. Journal Numbering

Each journal maintains its own sequence.

Example:

```
Sales Journal

INV-000001
INV-000002


Purchase Journal

BILL-000001
BILL-000002
```

Independent sequences improve:

- identification;
- auditing;
- reporting.

---

# 10. Default Accounts

Journals may define default accounts.

Examples:

Bank Journal:

```
Default Bank Account
```

Sales Journal:

```
Default Revenue Account
```

Purchase Journal:

```
Default Expense Account
```

Defaults simplify accounting operations.

---

# 11. Multi Company Support

Accounting Journals must support:

- company-specific journals;
- shared templates;
- independent sequences;
- different accounting configurations.

Example:

```
Global Journal Template

        ↓

Company Journal Instance
```

---

# 12. Journal Security

Access control may be defined by:

- company;
- user role;
- accounting responsibility.

Example:

```
Cash Journal

Only Finance Operators
```

---

# 13. Journal Lifecycle

Journals follow:

```
Draft

↓

Active

↓

Restricted

↓

Archived
```

A journal with accounting history cannot be deleted.

---

# 14. Integration

Other domains communicate with Accounting Core.

Examples:

Sales:

```
Sale Event

↓

Sales Journal
```

Inventory:

```
Stock Valuation Event

↓

Inventory Journal
```

Loan Management:

```
Loan Financial Event

↓

General Journal
```

The operational domains do not own accounting journals.

---

# 15. Audit

Journal changes must record:

- user;
- date;
- previous configuration;
- new configuration.

Accounting configuration must remain traceable.

---

# 16. Architecture Principles

Accounting Journals follow RFC-8000 principles:

- Accounting owns accounting organization.
- Journals classify accounting activity.
- Operational domains generate events only.
- Accounting structures must be auditable.
- Configuration should remain simple.

> **Simple is always better than complex.**

---

# 17. Roadmap

Next RFCs:

- RFC-8003 - Journal Entries
- RFC-8004 - Posting Engine
- RFC-8005 - Accounting Ledger
- RFC-8006 - Accounting Period Management
- RFC-8007 - Accounting Reports
- RFC-8008 - Accounting Integration

---

# 18. Final Considerations

Accounting Journals provide the organizational foundation for accounting transactions.

They separate different financial activities while keeping Accounting Core centralized and consistent.

The result is a modular accounting architecture where operational domains produce business facts and Accounting Core manages accounting truth.

> **Simple is always better than complex.**
