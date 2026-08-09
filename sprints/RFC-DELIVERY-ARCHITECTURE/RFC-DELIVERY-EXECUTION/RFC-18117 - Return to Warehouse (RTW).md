# RFC-18117 - Return to Warehouse (RTW)

| Field           | Value                                                     |
| --------------- | --------------------------------------------------------- |
| RFC             | RFC-18117                                                 |
| Title           | Return to Warehouse (RTW)                                 |
| Status          | Done                                                     |
| Version         | 1.0                                                       |
| Domain          | Delivery Platform                                         |
| Depends On      | RFC-18115 Failed Deliveries, RFC-18116 Customer Refusal   |
| Integrates With | WMS, Inventory, Tracking, Delivery Trip, Customer Service |
| UI              | BusinessUI                                                |
| Author          | Business Platform Team                                    |

---

## Platform Philosophy

> **Simple is always better than complex.**
> Simples é sempre melhor do que complexo.

Design systems that are easy to understand, easy to maintain, easy to extend, and easy to use.
Avoid unnecessary abstractions. Prefer explicit behavior over hidden magic.
Every feature should solve a real business problem.
Performance and maintainability always come first.

---

# 1. Abstract

This RFC defines the Return to Warehouse (RTW) process.

RTW represents the controlled transportation of undelivered goods back to the originating warehouse, depot or distribution center.

The Delivery Platform is responsible only for the transportation back to the warehouse.

Inventory reconciliation begins after warehouse receipt.

---

# 2. Objectives

Return to Warehouse answers:

* Which goods returned?
* Why did they return?
* Which Trip transported them back?
* Which warehouse will receive them?
* When did the return occur?

---

# 3. Core Principle

Returning goods is part of Delivery execution.

Receiving returned goods is part of WMS.

```text
Failed Delivery

or

Customer Refusal

        │

        ▼

Return to Warehouse

        │

        ▼

Warehouse Receiving (WMS)
```

---

# 4. RTW Entity

Each Return to Warehouse records:

* RTW Number
* Related Delivery Order
* Trip
* Driver
* Vehicle
* Destination Warehouse
* Return Timestamp
* Return Reason
* Current Status

---

# 5. Typical Reasons

Examples include:

* customer absent;
* customer refusal;
* damaged goods;
* incorrect address;
* operational interruption;
* vehicle issue;
* weather conditions.

Reason codes are configurable.

---

# 6. Workflow

```text
Delivery Failed

↓

Return Authorized

↓

Goods Loaded

↓

Trip Continues

↓

Warehouse Arrival

↓

RTW Completed

↓

WMS Receiving
```

---

# 7. Return Contents

The RTW records:

* products;
* quantities;
* packages;
* seals (if applicable);
* observations.

Returned quantities are compared with the original dispatched quantities.

---

# 8. Warehouse Arrival

Upon arrival, Delivery records:

* arrival timestamp;
* destination warehouse;
* driver confirmation.

Responsibility then transfers to the WMS receiving process.

---

# 9. Tracking Integration

Tracking events include:

* Return Started
* Goods In Transit
* Warehouse Arrived
* Return Completed

---

# 10. Inventory Integration

The Delivery Platform does not update inventory balances directly.

Inventory adjustments occur only after warehouse receiving and inspection according to WMS policies.

---

# 11. Business Rules

## Rule 1

Every RTW must reference an originating Delivery Order.

---

## Rule 2

Returned quantities must be fully traceable.

---

## Rule 3

RTW ends when the goods reach the designated warehouse.

---

## Rule 4

Warehouse receiving is outside the scope of the Delivery Platform.

---

## Rule 5

Every RTW generates an immutable audit history.

---

# 12. Performance Indicators

Operational KPIs include:

* return rate;
* average return time;
* returns by reason;
* returns by region;
* returns by driver;
* warehouse return volume.

---

# 13. Future Enhancements

Possible future capabilities:

* electronic warehouse handoff;
* return barcode scanning;
* automatic dock assignment;
* carrier return integration;
* reusable packaging tracking.

---

# 14. Final Architecture Rule

Return to Warehouse concludes the transportation responsibility of the Delivery Platform.

After warehouse arrival, responsibility transfers to the Warehouse Management System.

```text
Delivery

↓

Failed Delivery / Customer Refusal

↓

Return to Warehouse

↓

Warehouse Receiving (WMS)

↓

Inventory Processing
```

This separation preserves clear domain boundaries between Delivery execution and Warehouse inventory management.

> **Simple is always better than complex.**
