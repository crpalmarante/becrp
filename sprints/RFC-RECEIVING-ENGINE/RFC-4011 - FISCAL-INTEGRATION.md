# RFC-4011 - Fiscal Integration

| Field | Value |
|--------|-------|
| RFC | 4011 |
| Name | Fiscal Integration |
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

This RFC defines the integration between the **Receiving** domain and the **Fiscal** domain.

Its purpose is to provide a standardized interface for transferring validated receiving documents to the Fiscal domain for tax validation, bookkeeping and fiscal processing.

Receiving coordinates the business workflow.

Fiscal owns every fiscal operation.

---

# 2. Motivation

Receiving confirms that goods have been physically accepted.

Fiscal determines the fiscal consequences of that transaction.

Examples include:

- Fiscal document validation;
- Tax determination;
- Fiscal bookkeeping;
- Supplier invoice registration;
- Tax event generation;
- Compliance verification.

Separating these responsibilities allows each domain to evolve independently while preserving business consistency.

---

# 3. Responsibilities

The integration layer is responsible for:

- requesting fiscal processing;
- transferring validated receiving information;
- tracking fiscal processing;
- receiving fiscal results;
- publishing integration events.

---

# 4. Non Responsibilities

The integration layer does not:

- calculate taxes;
- validate fiscal rules;
- generate fiscal entries;
- determine CFOP;
- determine CST;
- determine tax regimes;
- communicate with government authorities.

These responsibilities belong exclusively to the Fiscal domain.

---

# 5. Integration Flow

```
Receiving Completed

↓

Physical Verification Completed

↓

Fiscal Integration

↓

Fiscal Processing

↓

Fiscal Result

↓

Receiving Updated
```

The Fiscal domain is invoked only after the receiving process reaches the required business state.

---

# 6. Integration Trigger

Fiscal processing starts when:

- Receiving is completed;
- Physical Verification is completed;
- Required business validations are satisfied;
- Mandatory pending items are resolved.

Trigger execution may be automatic or manual according to business configuration.

---

# 7. Data Exchange

Receiving provides:

- Receiving ID;
- Company;
- Supplier;
- Warehouse;
- Fiscal Document Reference;
- Document Number;
- Series;
- Access Key;
- Issue Date;
- Receiving Date;
- Product List;
- Verified Quantities;
- Total Amount.

Fiscal returns:

- Processing Status;
- Fiscal Document ID;
- Fiscal Entry ID;
- Warnings;
- Errors.

The Fiscal domain owns every fiscal record created during processing.

---

# 8. Fiscal Request

Each request represents one fiscal processing operation.

```
FiscalRequest

-----------------------

id

receiving_id

company_id

supplier_id

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

# 9. Fiscal Response

The Fiscal domain returns:

```
FiscalResponse

-----------------------

request_id

status

fiscal_document_id

bookkeeping_id

warnings

errors

completed_at
```

Receiving stores only the integration metadata.

Fiscal records remain under the ownership of the Fiscal domain.

---

# 10. Error Handling

Fiscal processing failures never modify the Receiving history.

Examples:

- Invalid fiscal configuration;
- Missing tax rules;
- Invalid fiscal document;
- Unsupported operation;
- Missing mandatory fiscal data.

Errors may generate Receiving Pending Items for user intervention.

---

# 11. Partial Processing

The Fiscal domain may complete only part of the requested work.

Example:

```
Supplier Invoice Validated

↓

Fiscal Bookkeeping Completed

↓

Government Submission Pending

↓

Fiscal Status

Partially Processed
```

Partial processing must always be traceable.

---

# 12. Events

Receiving publishes:

```
receiving.fiscal.requested
```

Fiscal publishes:

```
fiscal.processing.started

fiscal.processing.completed

fiscal.processing.failed

fiscal.processing.partial
```

Receiving reacts to these events without executing fiscal logic.

---

# 13. Audit

The integration records:

- request creation;
- processing start;
- processing completion;
- returned status;
- warnings;
- errors;
- timestamps;
- requesting user.

Fiscal audit remains the responsibility of the Fiscal domain.

---

# 14. User Interface

The Receiving Workspace displays fiscal processing information.

Typical status:

- Waiting
- Processing
- Completed
- Partially Completed
- Failed

Users may navigate directly to the corresponding Fiscal document.

---

# 15. Principles

This integration follows the Retail Platform architecture:

- Domain boundaries are preserved.
- Receiving never owns fiscal records.
- Fiscal never owns receiving operations.
- Communication occurs through explicit contracts.
- Events are preferred over direct dependencies.
- Every operation is fully traceable.
- Fiscal compliance belongs exclusively to the Fiscal domain.

---

# 16. Dependencies

Depends on:

- RFC-4001 - Receiving
- RFC-4007 - Receiving Pending Items
- RFC-4008 - Physical Verification

Consumes services from:

- Fiscal Domain

---

# 17. Roadmap

Next RFC:

- RFC-4012 - Receiving Event Model

---

# 18. Final Considerations

Fiscal Integration defines the contract between the Receiving and Fiscal domains.

Receiving confirms **what has been physically accepted**.

Fiscal determines **the fiscal consequences of that business event**.

This separation preserves domain independence, simplifies maintenance and supports future fiscal legislation changes without impacting the Receiving workflow.

The integration reinforces the platform principle:

> **Simple is always better than complex.**
