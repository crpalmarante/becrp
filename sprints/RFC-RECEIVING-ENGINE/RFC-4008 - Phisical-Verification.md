# RFC-4008 - Physical Verification

| Field | Value |
|--------|-------|
| RFC | 4008 |
| Name | Physical Verification |
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

This RFC defines the **Physical Verification** module of the Retail ERP.

The module is responsible for validating that the physical goods received match the expected information before inventory processing begins.

Physical Verification confirms quantities, products and receiving conditions.

The module does not update inventory.

---

# 2. Motivation

Receiving documents represent expected information.

The physical shipment may differ from the document.

Examples include:

- missing items;
- additional items;
- damaged products;
- incorrect quantities;
- wrong products;
- packaging issues.

The system must validate the physical shipment before inventory movement.

---

# 3. Responsibilities

The Physical Verification module is responsible for:

- validating received quantities;
- confirming received products;
- recording discrepancies;
- registering damaged items;
- recording missing items;
- recording additional items;
- generating verification results;
- publishing verification events.

---

# 4. Non Responsibilities

The module does not:

- update inventory;
- calculate taxes;
- modify supplier information;
- create financial records;
- approve fiscal documents;
- create stock movements.

Those responsibilities belong to specialized modules.

---

# 5. Verification Workflow

Every verification follows the same workflow.

```
Receiving Ready

↓

Start Verification

↓

Inspect Items

↓

Register Differences

↓

Finish Verification

↓

Publish Result
```

---

# 6. Verification Modes

The module supports different verification modes.

## Manual

The operator manually confirms every item.

---

## Barcode Assisted

Products are verified using barcode scanning.

---

## RFID Assisted

Products are verified using RFID devices.

---

## Mobile Device

Verification is performed using handheld terminals or mobile devices.

New verification methods may be introduced without changing the module architecture.

---

# 7. Verification Result

Each item receives one verification result.

Supported results:

- Verified
- Quantity Difference
- Product Difference
- Damaged
- Missing
- Additional
- Rejected

Each result is recorded independently.

---

# 8. Difference Management

Detected differences generate structured records.

Examples:

### Quantity Difference

Expected:

10

Received:

8

Difference:

-2

---

### Product Difference

Expected:

Product A

Received:

Product B

---

### Damaged Item

Product:

Chair Model X

Condition:

Packaging Broken

Damage Level:

Medium

---

# 9. Verification Record

Each verification creates a record.

```
PhysicalVerification

-----------------------

id

receiving_id

warehouse_id

operator_id

started_at

completed_at

status
```

Each item is stored separately.

```
PhysicalVerificationItem

-------------------------

verification_id

product_id

expected_quantity

received_quantity

result

notes
```

---

# 10. Pending Generation

Differences may generate pending items.

Examples:

- Missing Product
- Quantity Difference
- Damaged Item
- Unknown Product

Pending management is handled by RFC-4007.

---

# 11. Audit

Every verification records:

- operator;
- timestamps;
- verified quantities;
- detected differences;
- observations;
- verification method.

The verification history is immutable.

---

# 12. Events

The module publishes:

```
physical.verification.started

physical.verification.completed

physical.verification.failed

physical.verification.cancelled

physical.verification.item.updated
```

When discrepancies are detected:

```
physical.verification.difference.detected
```

---

# 13. Integrations

## Receiving

Starts and tracks the verification process.

## Product Localization

Provides identified products.

## Inventory

Receives verified quantities after completion.

## Pending Items

Receives unresolved discrepancies.

## Fiscal

May receive verification results when fiscal review is required.

---

# 14. User Interface

The Physical Verification screen should provide:

- Receiving information;
- Supplier information;
- Item list;
- Expected quantity;
- Received quantity;
- Difference indicator;
- Notes;
- Verification status.

Barcode scanning should be supported whenever available.

---

# 15. Permissions

Typical permissions include:

Operator

- Start verification;
- Update quantities;
- Register observations.

Supervisor

- Resolve discrepancies;
- Approve verification;
- Reopen verification.

Administrator

- Full access;
- Configuration;
- Audit.

---

# 16. Principles

The module follows the platform principles:

- Physical goods are the source of truth.
- Verification precedes inventory movement.
- Every discrepancy is traceable.
- One verification belongs to one receiving process.
- Verification does not execute inventory logic.
- Modules communicate through events.

---

# 17. Roadmap

Next RFCs:

- RFC-4009 - Inventory Integration
- RFC-4010 - Finance Integration
- RFC-4011 - Fiscal Integration
- RFC-4012 - Receiving Event Model

---

# 18. Final Considerations

Physical Verification ensures that the goods physically received correspond to the expected business transaction before inventory processing begins.

By separating verification from inventory movement, the platform maintains clear responsibilities, simplifies maintenance and improves operational reliability.

The module follows the platform principle:

> **Simple is always better than complex.**
