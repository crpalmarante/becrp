# RFC-8003 - Journal Entries

| Field | Value |
|--------|-------|
| RFC | 8003 |
| Name | Journal Entries |
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

This RFC defines the Journal Entry structure within the Accounting Core domain.

Journal Entries represent the official accounting representation of business events using the double-entry accounting principle.

---

# 2. Motivation

Business domains generate operational events:

- sales;
- purchases;
- inventory movements;
- loans;
- payments;
- asset transactions.

These events must be converted into balanced accounting transactions.

The Journal Entry is the accounting document that represents this conversion.

---

# 3. Responsibilities

Journal Entries are responsible for:

- representing accounting transactions;
- maintaining debit and credit lines;
- ensuring accounting balance;
- linking accounting events to business origins;
- supporting posting workflows;
- maintaining accounting traceability.

---

# 4. Non Responsibilities

Journal Entries do not:

- decide accounting rules;
- create operational events;
- calculate taxes;
- manage inventory;
- process payments.

Those responsibilities belong to other domains.

---

# 5. Journal Entry Structure

A Journal Entry contains:

```text
Journal Entry

├── Header

└── Lines
      ├── Debit Lines
      └── Credit Lines
```

---

# 6. Entry Header

The header contains:

- Entry Number
- Journal
- Company
- Date
- Accounting Period
- Reference
- Source Document
- Description
- Status

Example:

```text
Entry:

INV-2026-00001

Journal:

Inventory

Date:

2026-08-01

Reference:

Receiving Document #5001
```

---

# 7. Entry Lines

Each accounting line contains:

- Account
- Debit Amount
- Credit Amount
- Currency
- Description
- Analytic Dimensions
- Source Reference

Example:

```text
Debit:

Inventory Asset

Amount:

10,000


Credit:

Supplier Liability

Amount:

10,000
```

---

# 8. Double Entry Validation

Every Journal Entry must satisfy:

```text
Total Debits = Total Credits
```

Example:

Valid:

```text
Debit:

1000

Credit:

1000
```

Invalid:

```text
Debit:

1000

Credit:

900
```

Invalid entries cannot be posted.

---

# 9. Entry Lifecycle

Journal Entries follow:

```text
Draft

↓

Validated

↓

Posted

↓

Locked
```

---

# 10. Draft State

Draft entries may:

- be reviewed;
- be modified;
- receive additional information.

Draft entries are not part of official accounting records.

---

# 11. Validated State

Validation confirms:

- balanced debit and credit;
- valid accounts;
- valid period;
- required dimensions;
- accounting rules satisfied.

---

# 12. Posted State

A posted entry becomes part of official accounting history.

After posting:

- values cannot be changed;
- deletion is forbidden;
- corrections require reversal entries.

---

# 13. Reversal Entries

Corrections must generate new accounting events.

Example:

Original:

```text
Inventory Adjustment

Debit Inventory

Credit Adjustment Account
```

Correction:

```text
Reverse Entry

Debit Adjustment Account

Credit Inventory
```

The original remains preserved.

---

# 14. Source Traceability

Every Journal Entry must reference its origin.

Examples:

```text
Sales Order

Receiving Document

Loan Contract

Payment

Inventory Movement
```

This allows complete navigation:

```text
Business Event

↓

Journal Entry

↓

General Ledger
```

---

# 15. Multi-Currency Support

Journal Entries must support:

- transaction currency;
- company currency;
- exchange rate;
- conversion date.

---

# 16. Analytic Dimensions

Journal Entries may include analytical information:

Examples:

- cost center;
- department;
- project;
- branch;
- business unit.

Analytic dimensions do not replace the Chart of Accounts.

---

# 17. Integration

Journal Entries receive information from:

Sales:

- revenue events.

Purchasing:

- supplier transactions.

Inventory:

- valuation movements.

Loan Management:

- loan financial impacts.

Finance:

- payments.

Operational domains provide facts.
Accounting Core creates accounting records.

---

# 18. Audit

Every Journal Entry must record:

- creator;
- creation date;
- validation history;
- posting user;
- posting date;
- reversal references.

---

# 19. Architecture Principles

Journal Entries follow RFC-8000 principles:

- Accounting records are immutable after posting.
- Every transaction must be balanced.
- Accounting owns financial representation.
- Operational modules do not create accounting entries directly.
- Historical truth must be preserved.
- Simple is always better than complex.

---

# 20. Roadmap

Next RFCs:

- RFC-8004 - Posting Engine
- RFC-8005 - Accounting Ledger
- RFC-8006 - Accounting Period Management
- RFC-8007 - Accounting Reports
- RFC-8008 - Accounting Integration

---

# 21. Final Considerations

Journal Entries are the bridge between operational events and accounting truth.

They provide the formal accounting representation of business activity while maintaining separation between operational domains and Accounting Core.

> **Simple is always better than complex.**
