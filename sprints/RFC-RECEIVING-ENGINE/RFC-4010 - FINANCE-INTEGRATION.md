# RFC-4010 - Finance Integration

| Field | Value |
|--------|-------|
| RFC | 4010 |
| Name | Finance Integration |
| Category | Receiving |
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

This RFC defines the integration between the **Receiving** domain and the **Finance** domain.

Its purpose is to transfer validated receiving information required for creating financial obligations resulting from supplier transactions.

Receiving coordinates the business process.

Finance owns all financial operations.

---

# 2. Motivation

Receiving identifies that goods have been accepted.

Finance determines the financial impact.

Typical examples include:

- Accounts Payable
- Payment Schedule
- Installments
- Due Dates
- Cost Allocation
- Financial Approval

Keeping these responsibilities separated improves maintainability and allows both domains to evolve independently.

---

# 3. Responsibilities

The integration layer is responsible for:

- requesting financial processing;
- transferring receiving data;
- tracking financial processing;
- receiving processing results;
- publishing integration events.

---

# 4. Non Responsibilities

The integration layer does not:

- create Accounts Payable;
- calculate taxes;
- generate accounting entries;
- schedule payments;
- reconcile invoices;
- process payments.

Those responsibilities belong exclusively to the Finance domain.

---

# 5. Integration Flow

```
Receiving Completed

↓

Physical Verification Completed

↓

Finance Integration

↓

Financial Processing

↓

Finance Result

↓

Receiving Updated
```

Financial processing begins only after the receiving process has been successfully completed.

---

# 6. Integration Trigger

Finance processing starts when:

- Receiving is completed;
- Required approvals have been granted;
- Business rules allow financial processing.

The trigger may be automatic or manual depending on system configuration.

---

# 7. Data Exchange

Receiving provides:

- Receiving ID
- Supplier
- Company
- Document Number
- Document Series
- Access Key
- Receiving Date
- Total Amount
- Currency
- Payment Terms (if available)

Finance returns:

- Processing Status
- Accounts Payable ID
- Installment IDs
- Errors
- Warnings

Finance owns all generated financial records.

---

# 8. Finance Request

Each request represents a financial processing operation.

```
FinanceRequest

-----------------------

id

receiving_id

supplier_id

company_id

requested_at

requested_by

status
```

Supported status:

- New
- Processing
- Completed
- Failed
- Cancelled

---

# 9. Finance Response

Finance returns:

```
FinanceResponse

-----------------------

request_id

status

accounts_payable_id

warnings

errors

completed_at
```

Receiving stores only the integration metadata.

Financial records remain owned by the Finance domain.

---

# 10. Error Handling

Financial processing failures never invalidate the receiving operation.

Examples:

- Missing payment terms
- Supplier financial configuration missing
- Currency not configured
- Financial period closed
- Cost center required

Errors may generate Receiving Pending Items for user intervention.

---

# 11. Partial Processing

Finance may partially complete processing.

Example:

```
Invoice Imported

↓

Accounts Payable Created

↓

Installments Failed

↓

Financial Status

Partially Processed
```

All partial operations must be auditable.

---

# 12. Events

Receiving publishes:

```
receiving.finance.requested
```

Finance publishes:

```
finance.processing.started

finance.processing.completed

finance.processing.failed

finance.processing.partial
```

Receiving listens to these events but never executes financial logic.

---

# 13. Audit

The integration records:

- request creation;
- processing start;
- processing completion;
- returned status;
- returned errors;
- timestamps;
- requesting user.

Financial audit remains the responsibility of the Finance domain.

---

# 14. User Interface

The Receiving Workspace displays financial processing information.

Typical status:

- Waiting
- Processing
- Completed
- Partially Completed
- Failed

Users may open the related Accounts Payable record directly from the workspace.

---

# 15. Principles

This integration follows the platform architecture:

- Domain boundaries are preserved.
- Receiving never owns financial records.
- Finance never owns receiving operations.
- Communication occurs through explicit interfaces.
- Events are preferred over direct dependencies.
- Every operation is traceable.

---

# 16. Dependencies

Depends on:

- RFC-4001 - Receiving
- RFC-4007 - Receiving Pending Items
- RFC-4008 - Physical Verification

Consumes services from:

- Finance Domain

---

# 17. Roadmap

Next RFCs:

- RFC-4011 - Fiscal Integration
- RFC-4012 - Receiving Event Model

---

# 18. Final Considerations

Finance Integration establishes the contract between the Receiving and Finance domains.

Receiving determines **what has been accepted**.

Finance determines **how the financial obligation is created and managed**.

By keeping both domains independent, the platform remains modular, scalable and easier to maintain.

This RFC follows the architectural principle:

> **Simple is always better than complex.**
