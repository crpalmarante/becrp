# RFC-8000 - Accounting Core Architecture

| Field | Value |
|--------|-------|
| RFC | 8000 |
| Name | Accounting Core Architecture |
| Category | Accounting |
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

This RFC defines the architecture of the Accounting Core domain.

Accounting Core is responsible for managing accounting principles, financial records and accounting lifecycle events across the platform.

The domain provides a centralized accounting foundation while keeping operational domains independent.

---

# 2. Motivation

Business operations generate financial and accounting impacts.

Examples:

- receiving goods;
- selling products;
- inventory valuation;
- asset movements;
- loans;
- payments.

However, operational domains should not create accounting logic directly.

Accounting Core receives business events and applies accounting rules.

---

# 3. Responsibilities

Accounting Core is responsible for:

- chart of accounts;
- accounting entries;
- journals;
- posting rules;
- accounting periods;
- fiscal years;
- ledger management;
- accounting reports.

---

# 4. Non Responsibilities

Accounting Core does not:

- control inventory;
- create sales orders;
- process purchases;
- manage payroll;
- calculate taxes;
- manage loans.

These domains publish business events.

---

# 5. Accounting Model

Accounting Core follows a double-entry accounting model.

Every accounting transaction contains:

```text
Debit

+

Credit

=

Balanced Entry
```

Example:

```text
Inventory Increase

Debit:
Inventory Asset

Credit:
Supplier Liability
```

---

# 6. Accounting Lifecycle

Accounting follows:

```text
Business Event

↓

Accounting Rule Evaluation

↓

Journal Entry Creation

↓

Posting

↓

Ledger Update
```

---

# 7. Core Components

Accounting Core contains:

## Chart of Accounts

Defines accounting accounts.

---

## Journals

Groups accounting transactions.

Examples:

- Sales Journal;
- Purchase Journal;
- Inventory Journal;
- General Journal.

---

## Accounting Entries

Represents financial transactions.

---

## General Ledger

Official accounting history.

---

## Accounting Periods

Controls:

- opening;
- closing;
- locked periods.

---

# 8. Integration Model

Accounting Core consumes business events.

Example:

```text
Receiving

↓

Goods Received

↓

Accounting Event

↓

Accounting Entry
```

---

# 9. Accounting Rules

Accounting rules determine:

- which accounts are affected;
- debit account;
- credit account;
- posting conditions.

Rules belong to Accounting Core.

---

# 10. Audit

Accounting records must be immutable.

Corrections occur through:

- reversal entries;
- adjustment entries.

Original postings remain preserved.

---

# 11. Architecture Principles

Accounting Core follows:

- operational domains own operational logic;
- accounting owns accounting logic;
- events communicate business facts;
- accounting history is immutable;
- every entry must be balanced.

---

# 12. Roadmap

Future RFCs:

- RFC-8001 Chart of Accounts
- RFC-8002 Accounting Journals
- RFC-8003 Journal Entries
- RFC-8004 Posting Engine
- RFC-8005 Accounting Ledger
- RFC-8006 Period Management
- RFC-8007 Accounting Reports
- RFC-8008 Accounting Integration

---

# 13. Final Considerations

Accounting Core provides the financial foundation of the platform.

By separating accounting responsibilities from operational domains, the system remains modular, auditable and scalable.

Operational modules create business events.

Accounting Core transforms those events into accounting truth.

> **Simple is always better than complex.**
