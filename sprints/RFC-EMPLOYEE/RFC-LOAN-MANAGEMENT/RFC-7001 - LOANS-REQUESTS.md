# RFC-7001 - Loan Requests

| Field | Value |
|--------|-------|
| RFC | 7001 |
| Name | Loan Requests |
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

This RFC defines the loan request process within the Loan Management domain.

Every loan begins with a request.

The request captures the business intent before any approval, release or settlement occurs.

---

# 2. Motivation

Organizations require a controlled process before transferring value.

A loan request standardizes this process regardless of the loan type.

Examples include:

- payroll advance;
- employee purchase through payroll deduction;
- equipment loan;
- product demonstration;
- inter-branch loan;
- temporary asset allocation.

Using a common request model simplifies business operations and improves traceability.

---

# 3. Responsibilities

Loan Requests are responsible for:

- initiating a loan;
- identifying the involved parties;
- defining the requested loan item;
- validating mandatory information;
- recording the business reason;
- starting the approval workflow.

---

# 4. Non Responsibilities

Loan Requests do not:

- approve loans;
- release assets;
- reserve inventory;
- process payroll;
- generate financial installments;
- create accounting entries.

These responsibilities belong to other RFCs.

---

# 5. Request Information

A request should contain, at minimum:

## General Information

- Request Number
- Request Date
- Requested By
- Business Unit
- Company

---

## Recipient

The receiving party.

Examples:

- Employee
- Customer
- Supplier
- Branch
- Company
- Department
- Partner

---

## Loan Item

The requested value.

Examples:

- Money
- Product
- Equipment
- Vehicle
- Tool
- Other Business Asset

---

## Quantity

Applicable when the loan item represents physical goods.

---

## Estimated Value

Business value associated with the loan.

---

## Business Reason

Reason explaining why the loan is requested.

Examples:

- Payroll Advance
- Product Purchase
- Temporary Use
- Demonstration
- Operational Support
- Replacement Equipment
- Other

---

## Requested Period

When applicable:

- Start Date
- Expected End Date

---

## Settlement Policy

Desired settlement method.

Examples:

- Return
- Payroll Deduction
- Financial Payment
- Internal Compensation
- Write-off

---

# 6. Validation

Before entering the approval process, the request should validate:

- mandatory fields;
- recipient existence;
- loan item existence;
- settlement policy compatibility;
- business rules defined by Loan Policies.

Validation rules remain configurable.

---

# 7. Request States

Typical request states include:

- Draft
- Submitted
- Under Validation
- Pending Approval
- Rejected
- Approved
- Cancelled

After approval, the request becomes a Loan.

---

# 8. Loan Creation

Approval creates a new Loan.

The original request remains immutable.

This guarantees complete business traceability.

---

# 9. Audit

Every request must record:

- creation date;
- requester;
- modifications;
- validation results;
- approval history;
- rejection reasons.

No critical action may occur without audit information.

---

# 10. Integrations

Loan Requests may interact with:

Loan Policies

- business rule validation.

Identity

- requester authentication.

Organization

- company;
- branch;
- department.

Inventory

- item availability (when applicable).

The request never performs these operations directly.

---

# 11. Architecture Principles

Loan Requests follow the principles defined in RFC-7000.

In particular:

- Every loan starts with a request.
- Requests capture business intent.
- Approval is independent from request creation.
- Validation occurs before approval.
- Requests remain immutable after loan creation.

---

# 12. Roadmap

The following RFCs continue the workflow:

- RFC-7002 - Loan Policies
- RFC-7003 - Loan Approval
- RFC-7004 - Loan Settlement
- RFC-7005 - Loan Ledger

---

# 13. Final Considerations

Loan Requests provide the controlled entry point into the Loan Management domain.

By separating request creation from approval and execution, the architecture remains auditable, extensible and independent from inventory, payroll, finance and accounting.

This separation reinforces the platform principle:

> **Simple is always better than complex.**
