# RFC-9006 - Picking & Packing

| Field | Value |
|--------|-------|
| RFC | 9006 |
| Name | Picking & Packing |
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

This RFC defines the Picking and Packing architecture within the WMS Core domain.

The objective is to manage product separation, checking, consolidation and preparation for shipment.

---

# 2. Motivation

Customer fulfillment requires more than simply reducing inventory.

A modern warehouse must control:

- which products are picked;
- from which locations;
- by which operator;
- in what sequence;
- how products are consolidated;
- how shipments are prepared.

---

# 3. Core Concept

Picking and Packing are execution phases of warehouse operations.
Warehouse Operation

    ↓

Picking

    ↓

Packing

    ↓

Shipment


---

# 4. Picking Responsibilities

Picking is responsible for:

- selecting products;
- confirming quantities;
- validating locations;
- generating picking routes;
- recording execution.

---

# 5. Packing Responsibilities

Packing is responsible for:

- product consolidation;
- packaging;
- weight validation;
- volume creation;
- shipment preparation.

---

# 6. Picking Types

The WMS supports multiple picking strategies.

---

## 6.1 Single Order Picking

One operator handles one order.

Example:


Order #5001

↓

Pick all products

↓

Pack


Suitable for:

- small stores;
- low volume operations.

---

## 6.2 Batch Picking

Multiple orders are picked together.

Example:


Orders:

5001
5002
5003

↓

Single Picking Route


Suitable for:

- e-commerce;
- high volume operations.

---

## 6.3 Wave Picking

Orders are grouped into execution waves.

Example:


Morning Wave

100 customer orders

↓

Picking Tasks

↓

Packing Area


Suitable for:

- distribution centers.

---

## 6.4 Zone Picking

Operators work in specific warehouse zones.

Example:


Zone A

Electronics

Zone B

Furniture


---

# 7. Picking Route

The system may optimize routes.

Considerations:

- shortest path;
- location sequence;
- product availability;
- priority.

Example:


Start

↓

A01

↓

A05

↓

B02

↓

Packing


---

# 8. Picking Validation

Picking confirmation may require:

- barcode scan;
- product confirmation;
- quantity confirmation;
- location confirmation.

Example:


Scan Location

↓

Scan Product

↓

Confirm Quantity


---

# 9. Picking Exceptions

Possible exceptions:

## Product Missing

Expected:


10 units


Found:


8 units


---

## Wrong Product

System detects mismatch.

---

## Wrong Location

Operator accesses incorrect position.

---

# 10. Packing Process

Packing workflow:


Picked Products

    ↓

Consolidation

    ↓

Packaging

    ↓

Weight Check

    ↓

Label Generation

    ↓

Ready for Shipping


---

# 11. Package Management

The system manages:

- packages;
- boxes;
- pallets;
- containers.

Example:


Shipment #5000

Package 1

Product A

Package 2

Product B

---

# 12. Weight and Volume

Packing may validate:

- total weight;
- package dimensions;
- carrier requirements.

Example:


Package:

80 kg

Carrier Limit:

100 kg

Approved


---

# 13. Serial and Lot Control

For controlled products:

The system supports:

- serial numbers;
- batches;
- expiration dates.

Example:


Product:

Refrigerator

Serial:

SN123456


---

# 14. Furniture and Large Products

Special handling is supported.

Example:


Furniture Order

↓

Picking

↓

Assembly Area

↓

Delivery


Important for:

- furniture stores;
- appliances;
- large items.

---

# 15. Integration

## Sales


Sales Order

↓

Picking Operation


---

## Inventory


Picking Confirmation

↓

Stock Movement


---

## Delivery


Packed Shipment

↓

Shipping Process


---

## Accounting


Stock Valuation

↓

Accounting Integration


---

# 16. Productivity Analysis

Picking and Packing provide metrics:

- picks per hour;
- average picking time;
- packing time;
- error rate;
- operator productivity.

---

# 17. Mobile Execution

The process supports:

- handheld devices;
- barcode scanners;
- warehouse terminals.

Example:


Task Received

↓

Navigate

↓

Scan

↓

Confirm

↓

Complete


---

# 18. Architecture Principles

Picking & Packing follows:

- warehouse work is orchestrated;
- human actions are validated;
- errors are captured;
- physical reality is synchronized;
- simple is always better than complex.

---

# 19. Roadmap

Next RFCs:

- RFC-9007 - Receiving Process
- RFC-9008 - Shipping Process
- RFC-9009 - Warehouse Analytics

---

# 20. Final Considerations

Picking and Packing represent the execution intelligence of the WMS.

The objective is not only to move products faster.

It is to move the correct product, from the correct location, with complete traceability.

> Simple is always better than complex.
