# RFC-9003 - Operation Types

| Field | Value |
|--------|-------|
| RFC | 9003 |
| Name | Operation Types |
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

This RFC defines the Operation Type architecture within the WMS Core domain.

Operation Types define standardized warehouse behaviors and operational workflows.

The objective is to provide a flexible mechanism for controlling warehouse processes.

---

# 2. Motivation

Warehouses execute different types of physical operations.

Examples:

- receiving products;
- shipping orders;
- transferring inventory;
- sending products for repair;
- processing returns;
- performing inventory counts.

Each operation has different rules.

Operation Types provide the operational definition required by WMS.

---

# 3. Core Concept

An Operation Type defines:


What operation happens?

Where does it happen?

Which documents authorize it?

Which workflow should execute?


---

# 4. Operation Type Model


Operation Type

↓

Operation Workflow

↓

Warehouse Tasks

↓

Stock Movement

↓

Stock Ledger


---

# 5. Operation Type Responsibilities

Operation Types define:

- operation behavior;
- source location rules;
- destination location rules;
- required documents;
- task generation;
- validation rules;
- execution workflow.

---

# 6. Non Responsibilities

Operation Types do not:

- move stock directly;
- calculate costs;
- create accounting entries;
- replace business documents.

They only define operational behavior.

---

# 7. Standard Operation Types

The system provides common operation templates.

---

## 7.1 Purchase Receipt

Purpose:

Receive products from suppliers.

Flow:


Supplier

↓

Receiving Area

↓

Quality Check

↓

Storage Location


Required document:


Purchase Order
or
Supplier Invoice


---

## 7.2 Customer Shipment

Purpose:

Deliver products to customers.

Flow:


Storage Location

↓

Picking Area

↓

Packing Area

↓

Customer


Required document:


Sales Order


---

## 7.3 Internal Transfer

Purpose:

Move products between warehouses.

Flow:


Warehouse A

↓

Transit

↓

Warehouse B


Example:


Distribution Center

↓

Retail Store


---

## 7.4 Repair Shipment

Purpose:

Send products for technical service.

Flow:


Stock Location

↓

Repair Location

↓

Return Stock


Important:

The company still owns the product.

---

## 7.5 Customer Return

Purpose:

Process returned products.

Flow:


Customer

↓

Return Area

↓

Inspection

↓

Available Stock

or

Repair

or

Scrap


---

## 7.6 Inventory Adjustment

Purpose:

Correct physical differences.

Example:


Physical Count

↓

System Adjustment


Requires authorization.

---

## 7.7 Cross Docking

Purpose:

Move products directly from receiving to shipping.

Flow:


Supplier

↓

Receiving

↓

Customer Shipment


Without storage.

---

# 8. Operation Direction

Each operation defines movement direction.

Types:


Incoming

Internal

Outgoing


Examples:

Incoming:


Purchase Receipt


Internal:


Transfer


Outgoing:


Customer Delivery


---

# 9. Document Requirement

Every operation may define required documents.

Examples:

Purchase Receipt:


Purchase Order
NF-e


Shipment:


Sales Order
Invoice


Repair:


Repair Request


---

# 10. Workflow Configuration

Operation Types define workflow steps.

Example:

Receiving:


Receive

↓

Inspect

↓

Put Away


Shipment:


Pick

↓

Pack

↓

Ship


---

# 11. Validation Rules

Examples:

Receiving:

- supplier document required;
- quantity validation;
- product validation.

Shipment:

- customer order required;
- stock availability;
- reservation validation.

---

# 12. Custom Operation Types

Companies may create specific operations.

Examples:


Store Display Transfer

Seasonal Storage

Promotional Stock Movement

Marketplace Fulfillment


---

# 13. Integration

Operation Types integrate with:

## Purchase


Purchase Order

↓

Receipt Operation


---

## Sales


Sales Order

↓

Shipment Operation


---

## Inventory


Operation

↓

Stock Movement


---

## Accounting


Valuation Event

↓

Accounting Integration


---

# 14. Traceability

Every operation records:

- operation type;
- document origin;
- warehouse;
- operator;
- execution time;
- generated movements.

---

# 15. Architecture Principles

Operation Types follow:

- operations are configurable;
- workflows are reusable;
- documents authorize movements;
- stock changes require operational context;
- simple is always better than complex.

---

# 16. Roadmap

Next RFCs:

- RFC-9004 - Warehouse Operations
- RFC-9005 - Warehouse Tasks
- RFC-9006 - Picking & Packing

---

# 17. Final Considerations

Operation Types are the operational language of the WMS.

They allow the system to understand not only that inventory moved, but why, how and under which business process.

A movement without an operation has no context.

The WMS must always know:


What happened?

Why happened?

Who executed?

Which document authorized?


> Simple is always better than complex.
