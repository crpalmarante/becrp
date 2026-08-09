# RFC-9007 - Receiving Process

| Field | Value |
|--------|-------|
| RFC | 9007 |
| Name | Receiving Process |
| Category | WMS Core |
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

This RFC defines the inbound receiving process within the WMS Core domain.

The objective is to control the physical reception of products from external and internal sources, ensuring traceability, validation and inventory accuracy.

---

# 2. Motivation

Receiving is one of the most critical warehouse processes.

Errors during receiving generate:

- incorrect inventory;
- wrong costs;
- fiscal inconsistencies;
- operational problems.

A modern WMS must control the complete inbound lifecycle.

---

# 3. Core Concept

Receiving represents the controlled transition from external ownership/location into company inventory.
External Source

    ↓

Receiving Process

    ↓

Warehouse Inventory


---

# 4. Receiving Sources

The WMS supports multiple inbound origins.

## Supplier Receiving

Example:


Supplier

↓

Purchase Receipt


---

## Internal Transfer Receiving

Example:


Warehouse A

↓

Warehouse B


---

## Customer Return

Example:


Customer

↓

Return Area


---

## Repair Return

Example:


Technical Service

↓

Warehouse


---

# 5. Receiving Architecture


Business Document

    ↓

Receiving Operation

    ↓

Receiving Tasks

    ↓

Inspection

    ↓

Put Away

    ↓

Stock Available


---

# 6. Receiving Responsibilities

Receiving manages:

- unloading;
- document validation;
- quantity checking;
- product identification;
- quality inspection;
- storage preparation.

---

# 7. Non Responsibilities

Receiving does not:

- create purchase orders;
- calculate taxes;
- create accounting entries;
- define supplier contracts.

---

# 8. Receiving Lifecycle

The process follows:


Expected

↓

Arrived

↓

Unloading

↓

Checking

↓

Inspection

↓

Put Away

↓

Completed


---

# 9. Expected State

The system knows that a delivery is expected.

Example:


Purchase Order #5001

Expected:

20 Refrigerators


---

# 10. Arrival State

Physical delivery arrives.

Recorded:

- date;
- carrier;
- supplier;
- vehicle;
- operator.

---

# 11. Unloading

Products are physically removed from transport.

Tasks:

- unload;
- identify packages;
- move to receiving area.

---

# 12. Checking Process

The system validates:

## Product


Expected:

Refrigerator Model X

Received:

Refrigerator Model X


---

## Quantity


Expected:

10

Received:

10


---

## Document

Examples:

- Purchase Order;
- Supplier Invoice;
- NF-e.

---

# 13. Quality Inspection

Products may require inspection.

Examples:

- damaged packaging;
- technical validation;
- serial verification.

Possible outcomes:


Approved

↓

Available Stock

Rejected

↓

Return / Exception Area


---

# 14. Put Away Process

After validation:


Receiving Area

    ↓

Storage Location


The WMS determines:

- destination location;
- storage rules;
- capacity.

---

# 15. Put Away Strategies

Supported strategies:

## Fixed Location

Product always goes to the same location.

---

## Dynamic Location

System selects the best location.

Criteria:

- available capacity;
- product category;
- turnover;
- warehouse rules.

---

# 16. Serial and Lot Control

Receiving supports:

- serial numbers;
- batches;
- expiration dates.

Example:


Product:

TV

Serial:

ABC123456


---

# 17. Receiving Exceptions

Examples:

## Quantity Difference

Expected:


100 units


Received:


95 units


---

## Product Difference

Wrong item received.

---

## Damaged Product

Product blocked for analysis.

---

# 18. Integration

## Purchase


Purchase Order

↓

Receiving Operation


---

## Fiscal


NF-e

↓

Document Validation


---

## Inventory


Receiving Completion

↓

Stock Movement


---

## Cost


Received Value

↓

Inventory Valuation


---

## Accounting


Stock Increase

↓

Accounting Event


---

# 19. Audit Trail

Every receiving process records:

- source document;
- supplier;
- products;
- quantities;
- users;
- timestamps;
- exceptions;
- validations.

---

# 20. Receiving Dashboard

Possible indicators:

- pending receipts;
- average receiving time;
- supplier accuracy;
- quantity differences;
- rejected products.

---

# 21. Architecture Principles

Receiving follows:

- no undocumented inventory entry;
- physical events require traceability;
- documents originate processes;
- validation happens before availability;
- simple is always better than complex.

---

# 22. Roadmap

Next RFCs:

- RFC-9008 - Shipping Process
- RFC-9009 - Warehouse Analytics

---

# 23. Final Considerations

Receiving is the foundation of inventory reliability.

The WMS must guarantee:


What arrived?

From whom?

Based on which document?

Where was stored?

Who validated?


Only after this process the inventory becomes available.

> Simple is always better than complex.
