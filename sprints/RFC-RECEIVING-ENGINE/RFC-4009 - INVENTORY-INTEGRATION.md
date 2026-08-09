# RFC-4009 - Inventory Integration

| Field | Value |
|--------|-------|
| RFC | 4009 |
| Name | Inventory Integration |
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

This RFC defines the integration between the **Receiving** domain and the **Inventory** domain.

Its purpose is to provide a clear and decoupled mechanism for transferring validated receiving information into inventory operations.

Receiving remains responsible for business coordination.

Inventory remains responsible for all stock operations.

---

# 2. Motivation

Receiving and Inventory solve different business problems.

Receiving answers:

- What has arrived?
- Is the shipment valid?
- Has it been verified?

Inventory answers:

- Where should it be stored?
- Which stock should be updated?
- Which lot or serial number is assigned?
- Which inventory movements must be created?

Separating these responsibilities keeps both domains independent.

---

# 3. Responsibilities

The integration layer is responsible for:

- transferring verified receiving data;
- requesting inventory processing;
- tracking processing status;
- receiving inventory results;
- publishing integration events.

---

# 4. Non Responsibilities

The integration layer does not:

- create stock movements;
- calculate inventory balances;
- assign storage locations;
- reserve inventory;
- update lots;
- update serial numbers.

Those responsibilities belong exclusively to the Inventory module.

---

# 5. Integration Flow

```
Receiving Completed

↓

Physical Verification Completed

↓

Inventory Integration

↓

Inventory Processing

↓

Inventory Result

↓

Receiving Updated
```

---

# 6. Integration Trigger

Inventory processing begins only after:

- receiving is confirmed;
- physical verification is completed;
- required pending items are resolved.

Partial processing may be supported according to business configuration.

---

# 7. Data Exchange

Receiving provides:

- Receiving ID
- Warehouse
- Supplier
- Product List
- Verified Quantities
- Document Reference
- Receiving Date

Inventory returns:

- Processing Status
- Inventory Transaction IDs
- Stock Movement IDs
- Errors
- Warnings

---

# 8. Inventory Request

Each request represents one inventory operation.

```
InventoryRequest

----------------------

id

receiving_id

warehouse_id

requested_at

requested_by

status
```

Status:

- New
- Processing
- Completed
- Failed
- Cancelled

---

# 9. Inventory Response

Inventory returns a structured response.

```
InventoryResponse

-----------------------

request_id

status

processed_items

warnings

errors

completed_at
```

Receiving stores only the response metadata.

Inventory remains the owner of inventory records.

---

# 10. Error Handling

Inventory processing errors never modify Receiving history.

Examples:

- warehouse closed;
- invalid storage location;
- inventory configuration missing;
- serial number required;
- lot assignment required.

Errors create Pending Items when business intervention is required.

---

# 11. Partial Processing

The integration may support partial completion.

Example:

```
10 Items Received

↓

8 Successfully Stored

↓

2 Waiting Serial Number

↓

Receiving Status

Partially Processed
```

Partial processing must be fully traceable.

---

# 12. Events

Receiving publishes:

```
receiving.inventory.requested
```

Inventory publishes:

```
inventory.processing.started

inventory.processing.completed

inventory.processing.failed

inventory.processing.partial
```

Receiving reacts to these events but does not execute inventory logic.

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

Inventory audit remains independent.

---

# 14. User Interface

The Receiving Workspace displays:

Inventory Status

Examples:

- Waiting
- Processing
- Completed
- Partially Completed
- Failed

Users may navigate directly to the related Inventory transaction.

---

# 15. Principles

This integration follows the platform principles:

- Domain boundaries are preserved.
- Receiving never owns inventory.
- Inventory never owns receiving.
- Communication occurs through well-defined interfaces.
- Events are preferred over direct dependencies.
- Every operation is traceable.

---

# 16. Dependencies

Depends on:

- RFC-4001 - Receiving
- RFC-4007 - Receiving Pending Items
- RFC-4008 - Physical Verification

Consumes services from:

- Inventory Domain

---

# 17. Roadmap

Next RFCs:

- RFC-4010 - Finance Integration
- RFC-4011 - Fiscal Integration
- RFC-4012 - Receiving Event Model

---

# 18. Final Considerations

Inventory Integration defines the contract between the Receiving and Inventory domains.

By exchanging only validated business information, both domains remain independent, maintainable and extensible.

Receiving coordinates the business process.

Inventory owns every stock operation.

This separation reinforces the platform architecture and the principle:

> **Simple is always better than complex.**
