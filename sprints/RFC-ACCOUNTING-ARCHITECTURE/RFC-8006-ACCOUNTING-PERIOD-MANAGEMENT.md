# RFC-8006 - Accounting Period Management

| Field | Value |
|--------|-------|
| RFC | 8006 |
| Name | Accounting Period Management |
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

This RFC defines the accounting period management architecture within the Accounting Core domain.

Accounting Period Management controls fiscal years, accounting periods and posting availability.

Its purpose is to protect accounting integrity by controlling when accounting transactions can be created and posted.

---

# 2. Motivation

Accounting requires temporal control.

Organizations need to:

- define fiscal years;
- close monthly periods;
- prevent unauthorized retroactive postings;
- perform financial closing procedures;
- maintain historical accuracy.

Without period control, accounting data can become inconsistent.

---

# 3. Responsibilities

Accounting Period Management is responsible for:

- creating fiscal years;
- creating accounting periods;
- opening periods;
- closing periods;
- locking periods;
- controlling posting permissions;
- managing period status.

---

# 4. Non Responsibilities

Accounting Period Management does not:

- create accounting entries;
- calculate balances;
- generate financial reports;
- define accounting rules;
- modify Ledger records.

It only controls accounting availability.

---

# 5. Fiscal Year Concept

A Fiscal Year represents the official accounting year.

Example:

```
Fiscal Year:

2026

Periods:

January
February
March
...
December
```

---

# 6. Accounting Period Concept

An Accounting Period represents a controlled accounting interval.

Examples:

```
2026-01

2026-02

2026-03
```

Each period controls whether accounting transactions can be posted.

---

# 7. Period States

Accounting periods follow:

```
Open

↓

Closing

↓

Closed

↓

Locked
```

---

# 8. Open Period

An open period allows:

- journal posting;
- accounting adjustments;
- normal operations.

Example:

```
August 2026

Status:

Open
```

---

# 9. Closing Period

The closing state indicates that accounting review is occurring.

During closing:

- new postings may be restricted;
- validations may increase;
- authorized users may perform adjustments.

---

# 10. Closed Period

A closed period prevents normal posting.

Example:

```
July 2026

Status:

Closed
```

A new transaction cannot affect this period without authorization.

---

# 11. Locked Period

A locked period represents final accounting closure.

After locking:

- no normal posting;
- no modifications;
- only controlled correction procedures.

---

# 12. Retroactive Posting Control

The system must control backdated transactions.

Example:

Current date:

```
September 2026
```

User attempts:

```
Posting Date:

January 2026
```

The system checks:

```
January Period Status
```

If closed:

```
Posting Blocked
```

---

# 13. Period Reopening

Reopening must be controlled.

Requirements:

- authorized user;
- reason required;
- audit record;
- approval when necessary.

Example:

```
Period Reopened

Reason:

Audit Adjustment
```

---

# 14. Period Closing Process

Typical flow:

```
Review Transactions

↓

Validate Balances

↓

Generate Reports

↓

Close Period

↓

Lock Period
```

---

# 15. Multi Company Support

Each company may have:

- different fiscal years;
- different closing schedules;
- independent periods.

Example:

```
Company A

Fiscal Year 2026


Company B

Fiscal Year 2026
```

---

# 16. Integration

Accounting Period Management integrates with:

## Posting Engine

Before posting:

```
Journal Entry

↓

Check Period

↓

Allow / Block Posting
```

---

## Accounting Ledger

Ledger entries reference:

- fiscal year;
- accounting period.

---

## Reporting

Reports use period boundaries.

Examples:

- monthly reports;
- quarterly reports;
- annual reports.

---

# 17. Audit

Period changes must record:

- user;
- date;
- previous status;
- new status;
- reason.

Examples:

```
Open → Closed

Closed → Reopened
```

---

# 18. Security

Period operations require controlled permissions.

Examples:

Operator:

- view periods.

Accountant:

- close periods.

Controller:

- reopen periods.

---

# 19. Architecture Principles

Accounting Period Management follows RFC-8000 principles:

- Accounting time must be controlled.
- Closed history cannot be rewritten.
- Exceptions require authorization.
- Auditability is mandatory.
- Simple is always better than complex.

> **Simple is always better than complex.**

---

# 20. Roadmap

Next RFCs:

- RFC-8007 - Accounting Reports
- RFC-8008 - Accounting Integration

---

# 21. Final Considerations

Accounting Period Management protects the integrity of Accounting Core.

By controlling fiscal time, the platform ensures that the Accounting Ledger remains reliable, auditable and consistent.

Periods define not only dates, but accounting authority.

> **Simple is always better than complex.**
