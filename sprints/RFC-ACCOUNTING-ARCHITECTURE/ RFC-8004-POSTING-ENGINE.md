# RFC-8004 - Posting Engine

| Field | Value |
|--------|-------|
| RFC | 8004 |
| Name | Posting Engine |
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

This RFC defines the Posting Engine architecture within the Accounting Core domain.

The Posting Engine is responsible for validating and posting approved Journal Entries into the Accounting Ledger.

Its purpose is to guarantee accounting integrity, consistency and traceability.

---

# 2. Motivation

A Journal Entry represents an accounting transaction, but it should not immediately affect official accounting records.

Before becoming part of the General Ledger, the transaction must pass through controlled validation.

The Posting Engine provides this controlled transition.

---

# 3. Responsibilities

The Posting Engine is responsible for:

- validating Journal Entries;
- checking accounting integrity;
- verifying posting rules;
- confirming accounting periods;
- creating ledger records;
- changing entry status to posted;
- recording posting history.

---

# 4. Non Responsibilities

The Posting Engine does not:

- create business transactions;
- define accounting accounts;
- calculate taxes;
- generate sales documents;
- manage inventory;
- approve operational processes.

These responsibilities belong to other domains.

---

# 5. Posting Concept

Posting transforms:

```
Validated Journal Entry

        ↓

Official Accounting Record
```

Before posting:

```
Draft / Validated
```

After posting:

```
Accounting Truth
```

---

# 6. Posting Lifecycle

The posting lifecycle:

```
Journal Entry Created

        ↓

Validation

        ↓

Ready To Post

        ↓

Posting Execution

        ↓

Ledger Update

        ↓

Posted
```

---

# 7. Validation Rules

Before posting, the engine validates:

## Accounting Balance

Requirement:

```
Total Debit = Total Credit
```

---

## Account Validity

Checks:

- account exists;
- account is active;
- account allows posting.

---

## Period Validation

Checks:

- accounting period exists;
- period is open;
- posting is allowed.

---

## Company Validation

Checks:

- journal belongs to company;
- accounts are available;
- currency rules are valid.

---

# 8. Posting Execution

When validation succeeds:

```
Journal Entry

        ↓

Posting Engine

        ↓

General Ledger Entry
```

The posting operation must be atomic.

Either:

```
Complete Success
```

or:

```
No Accounting Impact
```

---

# 9. Posting States

Supported states:

```
Draft

↓

Validated

↓

Posted

↓

Reversed
```

---

# 10. Reversal Posting

Posted entries cannot be modified.

Corrections require reversal.

Example:

Original:

```
Inventory Adjustment

Debit Inventory

Credit Adjustment Account
```

Correction:

```
Reversal Entry

Debit Adjustment Account

Credit Inventory
```

The accounting history remains preserved.

---

# 11. Posting Queue

The engine may support asynchronous processing.

Example:

```
Journal Entry

↓

Posting Queue

↓

Posting Worker

↓

Ledger
```

Benefits:

- scalability;
- resilience;
- retry handling.

---

# 12. Error Handling

Posting failures must generate:

- error reason;
- failed entry reference;
- timestamp;
- retry information.

Example:

```
Posting Failed

Reason:

Closed Accounting Period
```

---

# 13. Audit

Every posting action records:

- entry identifier;
- posting user/system;
- date and time;
- validation result;
- ledger reference.

Posting history is immutable.

---

# 14. Integration

Posting Engine receives entries from:

- Sales;
- Purchase;
- Inventory;
- Cost Management;
- Loan Management;
- Finance.

Example:

```
Inventory Valuation Event

        ↓

Journal Entry

        ↓

Posting Engine

        ↓

General Ledger
```

---

# 15. Security

Posting permissions must respect:

- company access;
- accounting roles;
- period restrictions;
- authorization levels.

---

# 16. Architecture Principles

Posting Engine follows RFC-8000 principles:

- Accounting truth is created only through posting.
- Posted records are immutable.
- Validation happens before financial impact.
- Corrections create new records.
- Accounting ownership remains centralized.

> **Simple is always better than complex.**

---

# 17. Roadmap

Next RFCs:

- RFC-8005 - Accounting Ledger
- RFC-8006 - Accounting Period Management
- RFC-8007 - Accounting Reports
- RFC-8008 - Accounting Integration

---

# 18. Final Considerations

The Posting Engine is the control gate of Accounting Core.

It guarantees that only valid and balanced accounting transactions become official accounting records.

By separating entry creation from posting, the platform maintains flexibility, auditability and accounting integrity.

> **Simple is always better than complex.**
