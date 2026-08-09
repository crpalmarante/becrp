# RFC-30100 — Opportunity Management

**Status:** Draft

**Version:** 1.0

**Category:** Vendor Bidding Platform

**Priority:** Critical

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

Manage all business opportunities originating from public or private procurement processes.

An Opportunity represents any commercial possibility that may result in a proposal, contract, or supply agreement.

It is the starting point of the entire Vendor Bidding Platform lifecycle.

---

# 2. Scope

This RFC defines:

- Opportunity registration
- Classification
- Pipeline
- Qualification
- Ownership
- Deadlines
- History
- Metrics

---

# 3. Concept

An Opportunity may evolve into:

- Public Tender
- Private Bid
- RFQ
- RFP
- RFI
- Framework Agreement
- Accreditation
- Direct Corporate Sale

---

# 4. Origin

An Opportunity may originate from:

- Government Portal
- Private Portal
- CRM
- Customer
- Sales Representative
- Integration
- Import
- Manual Entry

---

# 5. Classification

Each Opportunity shall contain:

- Type
- Category
- Segment
- Market
- Company
- Business Unit
- Region
- Customer

---

# 6. General Information

Typical attributes:

- Number
- Title
- Description
- Customer
- Public Agency
- Procurement Method
- Owner
- Opening Date
- Submission Deadline
- Estimated Value
- Currency
- Status

---

# 7. Pipeline

```text
New
↓
Under Analysis
↓
Qualified
↓
Preparing Proposal
↓
Proposal Submitted
↓
Negotiation
↓
Awarded
↓
Contract
↓
Closed Won

or

Closed Lost
```

All state transitions shall be enforced by COBOL business rules.

---

# 8. Business Rules

An Opportunity:

- belongs to one company;
- has one owner;
- may have multiple collaborators;
- may contain multiple documents;
- may contain multiple items;
- may generate multiple proposal versions;
- may generate one or more contracts.

---

# 9. Calendar

Track:

- Meetings
- Site Visits
- Clarification Sessions
- Requests
- Public Sessions
- Negotiations

---

# 10. Checklist

Example:

- Tender received
- Documents validated
- Certificates valid
- Pricing completed
- Commercial approval
- Legal approval
- Financial approval

---

# 11. KPIs

- Total Opportunities
- Potential Revenue
- Conversion Rate
- Win Rate
- Average Preparation Time
- Won Value
- Lost Value

---

# 12. Audit

Every change records:

- User
- Date/Time
- Operation
- Changed Field
- Previous Value
- New Value

---

# 13. Security

Permissions by:

- Company
- Business Unit
- Department
- Team
- User
- Role

---

# 14. Integrations

- CRM
- Party
- Documents
- Proposal
- Pricing
- Workflow
- Calendar
- Notification
- Contract

---

# 15. Architecture

## Frontend

HTML + CSS + JavaScript

## Backend

All business rules and CRUD operations shall be implemented in COBOL.

Includes:

- CRUD
- Validation
- Workflow
- Audit
- State transitions
- Security rules

## Python

Used only for:

- BI
- Dashboards
- OCR
- AI
- Integrations
- Analytics

---

# 16. Conceptual Relationship

```text
Opportunity
    ├── Tender
    ├── Private Bid
    ├── Proposal
    ├── Pricing
    ├── Documents
    ├── Evaluation
    ├── Contract
    └── Contract Execution
```

---

# Principle

> Simple is always better than complex.
