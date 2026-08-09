# RFC-7002 - Loan Policies

| Field | Value |
|--------|-------|
| RFC | 7002 |
| Name | Loan Policies |
| Category | Loan Management |
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

This RFC defines the policy management system of the Loan Management domain.

Loan Policies define the business rules that control how loans are requested, validated, approved and settled.

The purpose of Loan Policies is to allow organizations to configure loan behavior without changing the application logic.

---

# 2. Motivation

Different organizations have different rules regarding loans.

Examples:

- who can request a loan;
- what can be loaned;
- maximum values;
- required approvals;
- allowed settlement methods;
- loan duration;
- renewal conditions.

Embedding these rules directly into the workflow creates complexity and makes future changes difficult.

Loan Policies provide a controlled way to configure business decisions.

---

# 3. Responsibilities

Loan Policies are responsible for:

- defining eligibility rules;
- defining loan limits;
- defining approval requirements;
- defining allowed settlement methods;
- defining loan duration rules;
- validating business conditions;
- providing policy decisions to the loan workflow.

---

# 4. Non Responsibilities

Loan Policies do not:

- approve loans;
- release loan items;
- process payroll deductions;
- create financial transactions;
- update inventory;
- create accounting entries.

Policies only define decisions.

Execution belongs to the responsible workflow or domain.

---

# 5. Policy Scope

Loan Policies apply only to the Loan Management domain.

They do not define rules for:

- Inventory;
- Payroll;
- Finance;
- Accounting;
- Human Resources;
- Sales.

Each domain owns its own business rules.

---

# 6. Policy Types

## 6.1 Eligibility Policies

Define who can participate in a loan.

Examples:

- allowed recipients;
- allowed organizational units;
- employee eligibility;
- customer eligibility.

Example:

```text
Recipient:
Employee

Department:
Sales

Eligible:
Yes
```

---

## 6.2 Loan Item Policies

Define what can be loaned.

Examples:

- products;
- equipment;
- tools;
- vehicles;
- monetary values.

Example:

```text
Item:
Notebook

Allowed:
Employee

Maximum Duration:
180 days
```

---

## 6.3 Value Policies

Define limits based on value.

Examples:

- maximum loan amount;
- automatic approval threshold;
- management approval threshold.

Example:

```text
Value <= 1000

Approval:
Automatic
```

---

## 6.4 Approval Policies

Define approval requirements.

Examples:

- required approver;
- approval hierarchy;
- number of approvals.

Example:

```text
Loan Value > 5000

Required Approval:
Manager
```

---

## 6.5 Settlement Policies

Define permitted loan completion methods.

Examples:

- return;
- financial payment;
- payroll deduction;
- internal compensation.

Example:

```text
Item:
TV

Settlement:

Payroll Deduction

or

Return
```

---

## 6.6 Duration Policies

Define time limitations.

Examples:

- maximum loan period;
- expiration rules;
- renewal permissions.

Example:

```text
Equipment Loan

Maximum Duration:
365 days
```

---

# 7. Policy Evaluation

When a Loan Request is created, applicable policies are evaluated.

The evaluation determines:

- if the request is valid;
- if approval is required;
- which settlement methods are available;
- additional restrictions.

Example:

```text
Loan Request

+

Applicable Policies

↓

Policy Decision
```

---

# 8. Policy Versioning

Policies must support version control.

Each policy change must record:

- version;
- effective date;
- creator;
- modification history.

Previous versions remain available for audit purposes.

---

# 9. Policy Priority

Multiple policies may apply to the same loan.

The system must support policy priority.

Example:

```text
Company Policy

overrides

Default Policy
```

---

# 10. Audit

Every policy decision must record:

- applied policies;
- policy versions;
- evaluation result;
- date and time;
- responsible user.

No policy decision may occur without traceability.

---

# 11. Configuration

Loan Policies are configured inside:

```text
Loan Management

↓

Configuration

↓

Policies
```

The configuration belongs exclusively to the Loan Management domain.

---

# 12. Architecture Principles

Loan Policies follow the principles defined in RFC-7000.

In particular:

- Policies define decisions, not actions.
- Business rules belong to their domain.
- Policy changes must not require code changes.
- Policy evaluation must be auditable.
- Simple is always better than complex.

---

# 13. Roadmap

The following RFCs continue the Loan Management workflow:

- RFC-7003 - Loan Approval
- RFC-7004 - Loan Settlement
- RFC-7005 - Loan Ledger
- RFC-7006 - Loan Integrations
- RFC-7007 - Loan Analytics
- RFC-7008 - Loan Workspace

---

# 14. Final Considerations

Loan Policies provide the decision layer of Loan Management.

They allow organizations to configure loan behavior while keeping the workflow simple, predictable and independent from external domains.

By keeping policies inside Loan Management, the architecture preserves clear ownership of business rules and maintains domain independence.

> **Simple is always better than complex.**
