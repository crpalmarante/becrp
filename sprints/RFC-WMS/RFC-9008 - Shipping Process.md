# RFC-9008 - Shipping Process

| Field | Value |
|--------|-------|
| RFC | 9008 |
| Name | Shipping Process |
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

This RFC defines the outbound shipping process within the WMS Core domain.

The objective is to control product dispatch from warehouse facilities to customers, stores, carriers or other destinations.

---

# 2. Motivation

Shipping is the final physical step before inventory leaves the warehouse.

Incorrect shipping creates:

- customer dissatisfaction;
- inventory errors;
- fiscal inconsistencies;
- financial losses.

A modern WMS must guarantee that the correct product reaches the correct destination.

---

# 3. Core Concept

Shipping represents the controlled transition from company inventory to an external destination.
Warehouse Inventory

    ↓

Shipping Process

    ↓

External Destination


---

# 4. Shipping Sources

Shipping may originate from:

## Customer Orders

Example:


Sales Order

↓

Customer Delivery


---

## Internal Transfers

Example:


Distribution Center

↓

Store


---

## Repair Shipments

Example:


Warehouse

↓

Technical Service


---

## Other Logistics Processes

Examples:

- marketplace fulfillment;
- promotional transfers;
- sample shipments.

---

# 5. Shipping Architecture


Business Document

    ↓

Shipping Operation

    ↓

Picking Tasks

    ↓

Packing Tasks

    ↓

Loading

    ↓

Shipment Confirmation

    ↓

Stock Movement


---

# 6. Shipping Responsibilities

Shipping manages:

- order preparation;
- product separation;
- verification;
- packaging;
- loading;
- dispatch confirmation.

---

# 7. Non Responsibilities

Shipping does not:

- create sales orders;
- calculate taxes;
- issue fiscal documents;
- calculate accounting entries.

Those belong to other domains.

---

# 8. Shipping Lifecycle

The process follows:


Created

↓

Planned

↓

Picking

↓

Checking

↓

Packing

↓

Loading

↓

Dispatched

↓

Completed


---

# 9. Shipping Creation

A shipping operation is generated from a document.

Examples:


Sales Order #5000

↓

Shipping Operation


or


Transfer Request #200

↓

Internal Shipping


---

# 10. Picking Phase

The WMS generates picking tasks.

Example:


Order:

Customer A

Tasks:

Pick Refrigerator

Location:

A01-03-02


---

# 11. Picking Validation

Validation may require:

- barcode scan;
- serial verification;
- quantity confirmation;
- location confirmation.

Example:


Expected:

1 Refrigerator

Confirmed:

1 Refrigerator


---

# 12. Checking Phase

Before shipment:

The system validates:

- products;
- quantities;
- customer;
- documents;
- reservations.

---

# 13. Packing Phase

Packing creates shipment units.

Examples:


Box

Pallet

Container


Information recorded:

- dimensions;
- weight;
- contents;
- identification.

---

# 14. Loading Process

Loading controls the transition from warehouse to transportation.

Records:

- vehicle;
- carrier;
- driver;
- route;
- loading sequence.

---

# 15. Shipment Confirmation

Only after confirmation:


Warehouse Stock

↓

Stock Movement

↓

Stock Ledger Update


The physical inventory changes officially.

---

# 16. Shipping Exceptions

## Missing Product

Expected:


10 units


Found:


9 units


---

## Damaged Product

Product blocked before dispatch.

---

## Wrong Destination

System prevents incorrect delivery.

---

## Customer Cancellation

Operation may be cancelled according to rules.

---

# 17. Large Product Delivery

Special handling for:

- furniture;
- refrigerators;
- appliances;
- bulky products.

Possible workflow:


Picking

↓

Assembly Area

↓

Quality Check

↓

Delivery Route

↓

Customer


---

# 18. Integration

## Sales


Sales Order

↓

Shipping Operation


---

## Delivery


Shipment

↓

Route Planning


---

## Fiscal


Shipment Confirmation

↓

Fiscal Document Process


---

## Inventory


Shipping Confirmation

↓

Stock Movement


---

## Accounting


Inventory Reduction

↓

Cost Accounting Event


---

# 19. Traceability

Every shipment records:

- source document;
- destination;
- products;
- quantities;
- serial numbers;
- warehouse;
- operators;
- carrier;
- timestamps.

---

# 20. Shipping Analytics

The WMS can measure:

- order preparation time;
- picking accuracy;
- shipping delays;
- carrier performance;
- fulfillment rate.

---

# 21. Architecture Principles

Shipping follows:

- inventory leaves only through controlled operations;
- documents authorize physical movement;
- every dispatch is traceable;
- execution is separated from business creation;
- simple is always better than complex.

---

# 22. Roadmap

Next RFC:

- RFC-9009 - Warehouse Analytics

---

# 23. Final Considerations

Shipping completes the outbound warehouse cycle.

The WMS guarantees:


Correct Product

Correct Quantity

Correct Destination

Correct Document

Complete Traceability


A warehouse does not simply send products.

It executes controlled logistics processes.

> Simple is always better than complex.
