# RFC-8005 - Accounting Ledger

| Field | Value |
|--------|-------|
| RFC | 8005 |
| Name | Accounting Ledger |
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

This RFC defines the Accounting Ledger architecture within the Accounting Core domain.

The Accounting Ledger is the official and immutable repository of posted accounting transactions.

Its purpose is to preserve accounting truth, provide auditability and support financial reporting.

---

# 2. Motivation

Accounting requires a permanent historical record.

After a transaction is posted, the system must always be able to answer:

- What happened?
- When did it happen?
- Which accounts were affected?
- Which business event generated it?
- Who posted it?

The Accounting Ledger provides this historical foundation.

---

# 3. Responsibilities

Accounting Ledger is responsible for:

- storing posted accounting entries;
- maintaining debit and credit history;
- preserving accounting chronology;
- supporting financial reports;
- enabling audits;
- providing accounting balances.

---

# 4. Non Responsibilities

Accounting Ledger does not:

- create accounting rules;
- approve transactions;
- generate journal entries;
- modify posted records;
- execute business operations.

The Ledger only stores official accounting facts.

---

# 5. Ledger Concept

The Accounting Ledger contains only posted transactions.

Flow:

```
Business Event

↓

Journal Entry

↓

Posting Engine

↓

Accounting Ledger
```

Only after posting does a transaction become accounting truth.

---

# 6. Ledger Structure

The Ledger is composed of:

```
Accounting Ledger

├── Ledger Header

└── Ledger Lines
        ├── Debit
        └── Credit
```

---

# 7. Ledger Header

Contains:

- Ledger Entry ID;
- Journal Entry Reference;
- Company;
- Accounting Date;
- Posting Date;
- Journal;
- Source Document;
- Transaction Reference.

Example:

```
Entry:

GL-2026-000001

Source:

Receiving Document #5001

Journal:

Inventory
```

---

# 8. Ledger Lines

Each line contains:

- Account;
- Debit Amount;
- Credit Amount;
- Currency;
- Analytic Dimensions;
- Company;
- Source Reference.

Example:

```
Account:

Inventory Asset

Debit:

10,000


Account:

Supplier Liability

Credit:

10,000
```

---

# 9. Immutability

Posted ledger records cannot be:

- edited;
- deleted;
- replaced.

Corrections must occur through new accounting entries.

Example:

Original:

```
Inventory Increase
```

Correction:

```
Inventory Reversal
```

The original event remains preserved.

---

# 10. Balance Calculation

Account balances are derived from ledger movements.

Example:

```
Inventory Account

Opening Balance

+

Debit Movements

-

Credit Movements

=

Current Balance
```

---

# 11. Accounting Period Support

Ledger records must reference:

- fiscal year;
- accounting period;
- accounting date.

Closed periods cannot receive new postings.

---

# 12. Multi Company Support

The Ledger supports:

- multiple companies;
- independent accounting structures;
- company-specific reporting.

Accounting data must remain isolated by company.

---

# 13. Audit Trail

Every ledger record must maintain:

- creation timestamp;
- posting reference;
- source document;
- originating domain;
- responsible system/user.

The history must be fully traceable.

---

# 14. Source Traceability

The Ledger must allow navigation:

Example:

```
General Ledger

↓

Journal Entry

↓

Business Event

↓

Source Document
```

Examples:

```
Inventory Movement

Receiving Document

Sales Order

Loan Settlement
```

---

# 15. Reporting Foundation

The Accounting Ledger supports:

- Trial Balance;
- Balance Sheet;
- Income Statement;
- Account Statements;
- Audit Reports.

---

# 16. Integration

The Ledger receives posted transactions from:

- Sales;
- Purchase;
- Inventory;
- Cost Management;
- Loan Management;
- Finance.

External domains consume accounting information but do not modify the Ledger.

---

# 17. Performance Considerations

The Ledger must support:

- large transaction volumes;
- historical queries;
- period-based reporting;
- indexing by account and date.

---

# 18. Architecture Principles

Accounting Ledger follows RFC-8000 principles:

- Posted accounting records are immutable.
- Accounting history is permanent.
- Corrections create new facts.
- The Ledger is the source of accounting truth.
- Operational domains remain independent.

> **Simple is always better than complex.**

---

# 19. Roadmap

Next RFCs:

- RFC-8006 - Accounting Period Management
- RFC-8007 - Accounting Reports
- RFC-8008 - Accounting Integration

---

# 20. Final Considerations

The Accounting Ledger is the foundation of financial integrity.

It provides a permanent, auditable and reliable history of every accounting event processed by the platform.

By separating Ledger storage from operational workflows, the architecture remains modular, scalable and compliant.

> **Simple is always better than complex.**
