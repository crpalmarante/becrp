# RFC-8007 - Accounting Reports

| Field | Value |
|--------|-------|
| RFC | 8007 |
| Name | Accounting Reports |
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

This RFC defines the reporting architecture within the Accounting Core domain.

Accounting Reports provide financial views, statements and analysis based on posted accounting data.

The purpose is to transform accounting records into meaningful financial information.

---

# 2. Motivation

Accounting data alone is not enough for decision-making.

Organizations need visibility into:

- financial position;
- profitability;
- obligations;
- movements;
- account balances;
- historical evolution.

Accounting Reports provide structured interpretation of accounting truth.

---

# 3. Responsibilities

Accounting Reports are responsible for:

- generating accounting statements;
- providing financial views;
- presenting account analysis;
- supporting management decisions;
- supporting audits;
- providing historical comparisons.

---

# 4. Non Responsibilities

Accounting Reports do not:

- create accounting entries;
- modify Ledger records;
- calculate accounting rules;
- change periods;
- approve transactions.

Reports only consume accounting information.

---

# 5. Data Sources

The primary source is:

```
Accounting Ledger
```

Additional sources:

- Chart of Accounts;
- Accounting Periods;
- Journals;
- Analytic Dimensions.

---

# 6. Core Financial Reports

## 6.1 Trial Balance

Provides account balances.

Example:

```
Account              Debit       Credit

Cash                 50,000

Suppliers                        20,000

Revenue                          80,000
```

Purpose:

- validation;
- accounting review;
- reconciliation.

---

# 6.2 General Ledger Report

Shows detailed movements by account.

Example:

```
Account:

Inventory

Opening Balance

+

Movements

=

Closing Balance
```

---

# 6.3 Journal Report

Shows accounting transactions grouped by journal.

Examples:

- Sales Journal;
- Purchase Journal;
- Inventory Journal;
- General Journal.

---

# 6.4 Balance Sheet

Shows financial position.

Structure:

```
Assets

-

Liabilities

+

Equity
```

Examples:

Assets:

- Cash;
- Inventory;
- Receivables.

Liabilities:

- Suppliers;
- Loans.

---

# 6.5 Income Statement

Shows operational performance.

Structure:

```
Revenue

-

Expenses

=

Profit / Loss
```

---

# 6.6 Cash Flow Report

Provides financial movement analysis.

Examples:

- operating activities;
- investment activities;
- financing activities.

---

# 7. Management Reports

Accounting Reports may provide:

## Account Analysis

Examples:

- account evolution;
- movements;
- balances.

---

## Cost Analysis

Examples:

- expenses by department;
- cost centers;
- projects.

---

## Company Comparison

Examples:

- branch comparison;
- business unit comparison.

---

# 8. Period Analysis

Reports must support:

- fiscal year;
- monthly comparison;
- quarterly analysis;
- custom date ranges.

Example:

```
January 2026

vs

January 2025
```

---

# 9. Analytic Dimensions

Reports may include:

- company;
- branch;
- department;
- cost center;
- project.

Analytic information provides management visibility without changing accounting structure.

---

# 10. Report Filters

Reports should support dynamic filters:

Examples:

- date range;
- company;
- journal;
- account;
- analytic dimension;
- currency.

---

# 11. Multi Company Reporting

The system must support:

- individual company reports;
- consolidated reports;
- company comparison.

Example:

```
Group Report

Company A

+

Company B

+

Company C
```

---

# 12. Export

Reports may support:

- PDF;
- spreadsheet;
- structured data export.

Exported information must respect user permissions.

---

# 13. Security

Reports must respect:

- company access;
- accounting permissions;
- analytic visibility.

Example:

Branch manager:

- sees own branch.

Controller:

- sees consolidated data.

---

# 14. Audit

Reports must maintain:

- generation date;
- user;
- filters applied;
- source period.

This allows reproduction of historical analysis.

---

# 15. Architecture Principles

Accounting Reports follow RFC-8000 principles:

- Reports consume accounting truth.
- Reports never modify accounting data.
- The Ledger is the single source of accounting facts.
- Complexity belongs in data interpretation, not data storage.
- Simple is always better than complex.

> **Simple is always better than complex.**

---

# 16. Roadmap

Next RFC:

- RFC-8008 - Accounting Integration

---

# 17. Final Considerations

Accounting Reports transform accounting records into business intelligence.

They allow organizations to understand financial reality while preserving the separation between accounting processing and information analysis.

The Accounting Core remains:

```
Events

↓

Accounting Truth

↓

Reports
```

> **Simple is always better than complex.**
