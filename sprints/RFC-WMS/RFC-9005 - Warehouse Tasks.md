# RFC-9005 - Warehouse Tasks

| Field | Value |
|--------|-------|
| RFC | 9005 |
| Name | Warehouse Tasks |
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

This RFC defines the Warehouse Task architecture within the WMS Core domain.

Warehouse Tasks represent executable activities generated from warehouse operations.

The objective is to control, assign and track physical warehouse work.

---

# 2. Motivation

Warehouse operations are composed of multiple activities.

A shipment is not a single action.

It requires:

- picking;
- checking;
- packing;
- moving;
- loading.

Warehouse Tasks transform operational processes into executable work units.

---

# 3. Core Concept

A Warehouse Task is the smallest executable unit of warehouse work.

Example:
Operation:

Customer Shipment

Task:

Move Product

From:

A01-03-02

To:

Shipping Area


---

# 4. Architecture


Warehouse Operation

    ↓

Warehouse Tasks

    ↓

Operator Execution

    ↓

Stock Movement

    ↓

Stock Ledger


---

# 5. Responsibilities

Warehouse Tasks are responsible for:

- defining executable activities;
- assigning work;
- controlling execution;
- tracking productivity;
- recording completion.

---

# 6. Non Responsibilities

Warehouse Tasks do not:

- create business documents;
- define sales rules;
- calculate inventory value;
- create accounting entries.

---

# 7. Task Lifecycle

Tasks follow:


Created

↓

Assigned

↓

Started

↓

Executing

↓

Completed

↓

Validated

↓

Closed


---

# 8. Created State

Task generated from an operation.

Example:


Pick Product

Product:

Refrigerator 550L

Quantity:

1

Location:

A01-03-02


---

# 9. Assigned State

A task is assigned to:

- employee;
- team;
- workstation;
- device.

Example:


Assigned Operator:

Warehouse User 01


---

# 10. Started State

Operator begins execution.

Records:

- start time;
- operator;
- device;
- location.

---

# 11. Executing State

Task is currently being performed.

Examples:

- picking;
- moving;
- counting;
- checking.

---

# 12. Completed State

Operator confirms execution.

Example:


Product Collected

Quantity:

1

Destination:

Packing Area


---

# 13. Validated State

System verifies:

- quantity;
- product;
- location;
- rules.

---

# 14. Task Types

The system supports different task categories.

---

## Picking Task

Purpose:

Collect products.

Example:


Storage

↓

Picking Area


---

## Put Away Task

Purpose:

Store received products.

Example:


Receiving

↓

Storage Location


---

## Internal Move Task

Purpose:

Move products internally.

Example:


Location A

↓

Location B


---

## Counting Task

Purpose:

Physical inventory counting.

---

## Packing Task

Purpose:

Prepare shipment.

---

## Loading Task

Purpose:

Prepare dispatch.

---

# 15. Task Assignment

Assignment may be:

## Manual

Supervisor assigns.

---

## Automatic

System chooses based on:

- availability;
- location;
- workload;
- priority.

---

# 16. Task Priority

Tasks support:


Urgent

High

Normal

Low


Example:

Customer express delivery:


Priority:

Urgent


---

# 17. Mobile Execution

Tasks should support mobile devices.

Example workflow:


Scan Location

↓

Scan Product

↓

Confirm Quantity

↓

Complete Task


---

# 18. Barcode Integration

Warehouse Tasks may use:

- barcode;
- QR Code;
- RFID.

Example:


Scan Product

↓

System Validation

↓

Confirm Movement


---

# 19. Exception Handling

Tasks may generate exceptions.

Examples:

## Missing Product


Expected:

1

Found:

0


---

## Wrong Location


Product not found


---

## Quantity Difference


Expected:

10

Found:

8


---

# 20. Productivity Metrics

Tasks enable analysis:

- tasks completed;
- execution time;
- productivity;
- accuracy;
- operator performance.

---

# 21. Integration

Warehouse Operations:


Operation

↓

Tasks


Inventory:


Task Completion

↓

Stock Movement


Employees:


Task Assignment

↓

User Activity


Analytics:


Task Data

↓

Warehouse KPIs


---

# 22. Audit

Every task records:

- operator;
- timestamps;
- status history;
- device;
- exceptions;
- validation results.

---

# 23. Architecture Principles

Warehouse Tasks follow:

- work is divided into executable units;
- every action is traceable;
- operators execute, systems control;
- physical movements require confirmation;
- simple is always better than complex.

---

# 24. Roadmap

Next RFCs:

- RFC-9006 - Picking & Packing
- RFC-9007 - Receiving Process
- RFC-9008 - Shipping Process
- RFC-9009 - Warehouse Analytics

---

# 25. Final Considerations

Warehouse Tasks are the operational heartbeat of the WMS.

They transform warehouse processes into controlled human activities.

The WMS does not simply record movement.

It orchestrates work.

> Simple is always better than complex.
