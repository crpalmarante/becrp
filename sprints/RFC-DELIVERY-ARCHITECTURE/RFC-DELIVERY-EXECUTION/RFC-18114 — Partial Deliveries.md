# RFC-18114 - Partial Deliveries

| Field           | Value                                                                                                        |
| --------------- | ------------------------------------------------------------------------------------------------------------ |
| RFC             | RFC-18114                                                                                                    |
| Title           | Partial Deliveries                                                                                           |
| Status          | Done                                                                                                        |
| Version         | 1.0                                                                                                          |
| Domain          | Delivery Platform                                                                                            |
| Depends On      | RFC-18001 Delivery Orders, RFC-18108 Delivery Stops, RFC-18111 Stop Execution, RFC-18113 Delivery Exceptions |
| Integrates With | Sales, POS, WMS, Inventory, Tracking, Customer Portal                                                        |
| UI              | BusinessUI                                                                                                   |
| Author          | Business Platform Team                                                                                       |

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

This RFC defines the Partial Delivery process.

A Partial Delivery occurs when only part of the requested items are delivered during a Stop while the remaining items stay pending for future fulfillment.

Partial Delivery is a normal business process and must not be treated as an operational exception.

---

# 2. Objectives

Partial Deliveries answer:

* Which items were delivered?
* Which quantities remain pending?
* Why was the delivery partial?
* What is the remaining delivery balance?
* Is another delivery required?

---

# 3. Core Principle

A Partial Delivery never changes the original commercial document.

The Sales Order and Delivery Order remain intact.

Only execution progress changes.

```text
Sales Order

        │

        ▼

Delivery Order

        │

        ▼

Stop Execution

        │

        ├── Delivered Quantity

        └── Remaining Quantity
```

---

# 4. Delivery Balance

The platform maintains a Delivery Balance for every delivery line.

```text
Ordered

100

Delivered

70

Remaining

30
```

The balance is updated after every Stop execution.

---

# 5. Partial Delivery Entity

Each Partial Delivery records:

* Delivery Order
* Delivery Stop
* Product
* Ordered Quantity
* Delivered Quantity
* Remaining Quantity
* Reason Code
* Execution Timestamp

---

# 6. Common Reasons

Typical reasons include:

* insufficient stock;
* customer requested split delivery;
* vehicle capacity limitation;
* damaged goods removed before delivery;
* operational planning;
* supplier backorder.

Reason codes are configurable.

---

# 7. Workflow

```text
Delivery Started

↓

Items Verified

↓

Partial Delivery

↓

Delivery Balance Updated

↓

Pending Quantity Created

↓

Future Delivery Planned
```

---

# 8. Multiple Partial Deliveries

The same Delivery Order may generate multiple partial deliveries.

Example:

```text
Delivery Order

↓

Day 1

40 Items


↓

Day 2

35 Items


↓

Day 3

25 Items
```

The Delivery Balance reaches zero only after all quantities have been delivered or otherwise resolved.

---

# 9. Multi-Address Deliveries

Partial Deliveries are independent of delivery addresses.

Example:

```text
Sales Order

↓

Address A

Delivered

↓

Address B

Partial

↓

Address C

Pending
```

Each Stop maintains its own execution history.

---

# 10. Integration With Inventory

Inventory reflects only the quantities physically delivered.

Pending quantities remain available for future warehouse planning according to inventory policies.

---

# 11. Integration With WMS

Remaining quantities may generate:

* new picking tasks;
* replenishment requests;
* future dispatch planning.

The original Delivery Order remains the business reference.

---

# 12. Customer Communication

Customers may be informed of:

* delivered quantities;
* pending quantities;
* expected completion date;
* reason for partial delivery.

Notifications are configurable.

---

# 13. Tracking Integration

Tracking events include:

* Partial Delivery Started
* Partial Delivery Confirmed
* Remaining Quantity Registered
* Future Delivery Scheduled

---

# 14. Business Rules

## Rule 1

Partial Delivery is a normal business process.

It is not a Delivery Exception.

---

## Rule 2

The original Sales Order is never modified.

---

## Rule 3

The original Delivery Order is never duplicated.

---

## Rule 4

Delivery Balance must always satisfy:

```text
Ordered

=

Delivered

+

Remaining
```

---

## Rule 5

Every quantity movement must be auditable.

---

## Rule 6

Remaining quantities may generate additional Stops, Trips or Delivery Orders according to company policy, while preserving the reference to the original Delivery Order.

---

# 15. Performance Indicators

Operational KPIs include:

* partial delivery rate;
* average remaining quantity;
* average completion time;
* split delivery frequency;
* fulfillment percentage.

---

# 16. Future Enhancements

Possible future capabilities:

* automatic rescheduling;
* customer delivery preferences;
* AI split-delivery recommendations;
* warehouse stock prediction;
* automatic consolidation of pending balances.

---

# 17. Final Architecture Rule

Partial Delivery represents execution progress, not document modification.

Business documents remain immutable.

Execution updates only the Delivery Balance.

```text
Sales Order

↓

Delivery Order

↓

Delivery Balance

↓

Stop Execution

↓

Remaining Balance

↓

Future Delivery
```

This architecture preserves document integrity while allowing unlimited partial deliveries throughout the fulfillment lifecycle.

> **Simple is always better than complex.**
