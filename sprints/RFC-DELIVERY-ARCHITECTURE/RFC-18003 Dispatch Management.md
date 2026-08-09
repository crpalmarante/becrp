# RFC-18003 - Dispatch Management

| Field           | Value                                                                        |
| --------------- | ---------------------------------------------------------------------------- |
| RFC             | RFC-18003                                                                    |
| Title           | Dispatch Management                                                          |
| Status          | Done                                                                        |
| Version         | 1.0                                                                          |
| Domain          | Delivery Platform                                                            |
| Depends On      | RFC-18000 Delivery Core, RFC-18001 Delivery Orders, RFC-18002 Delivery Tasks |
| Integrates With | Sales, POS, WMS, Inventory, Driver Resource, Tracking                        |
| Author          | Business Platform Team                                                       |

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

This RFC defines the Dispatch Management module.

Dispatch Management is responsible for coordinating delivery execution by organizing Delivery Orders and assigning operational resources.

The Dispatch layer transforms prepared deliveries into executable delivery operations.

---

# 2. Core Principle

The platform must separate:

```text
Delivery Order

=
Customer Delivery Requirement
```

from:

```text
Dispatch

=
Operational Organization
```

and:

```text
Delivery Task

=
Execution Activity
```

---

# 3. Dispatch Responsibility

Dispatch Management controls:

* delivery queue;
* delivery grouping;
* assignment;
* operational release;
* workload balancing;
* dispatch status.

---

# 4. Non Responsibilities

Dispatch does not:

* create sales;
* calculate product prices;
* manage warehouse stock;
* replace route optimization systems;
* manage vehicle maintenance.

---

# 5. Architecture Overview

```text
                    Sales / POS

                        |

                        ▼

                Delivery Order

                        |

                        ▼

                  Dispatch

                        |

        +---------------+---------------+

        ▼                               ▼

 Delivery Tasks                 Resources


                        |

                        ▼

                  Execution
```

---

# 6. Dispatch Entity

## Dispatch Batch

A Dispatch Batch groups deliveries that will be executed together.

Example:

```text
Dispatch Batch:

DS-000001


Date:

2026-08-10


Source:

Store São Paulo Centro


Status:

Open
```

---

# 7. Dispatch Relationship

A Dispatch may contain multiple Delivery Orders.

```text
Dispatch Batch

        1

        |

        N

Delivery Orders
```

Example:

```text
Dispatch DS-000001


DO-001

Customer A


DO-002

Customer B


DO-003

Customer C
```

---

# 8. Dispatch Lifecycle

```text
Open

↓

Planning

↓

Assigned

↓

Released

↓

In Progress

↓

Completed

↓

Closed
```

---

# 9. Dispatch States

## Open

New dispatch operation created.

---

## Planning

Deliveries are being organized.

---

## Assigned

Resources have been allocated.

---

## Released

Operation authorized to start.

---

## In Progress

Deliveries are being executed.

---

## Completed

All deliveries finished.

---

# 10. Delivery Queue

Dispatch provides an operational queue.

Example:

```text
Pending Deliveries


DO-000101

Priority:
High


DO-000102

Priority:
Normal


DO-000103

Priority:
Low
```

---

# 11. Delivery Priorities

Initial priorities:

```text
Emergency

High

Normal

Low
```

Examples:

Emergency:

* customer waiting;
* failed previous delivery.

High:

* scheduled delivery.

Normal:

* standard delivery.

---

# 12. Resource Assignment

Dispatch assigns:

```text
Delivery Team

Driver

Vehicle

External Carrier
```

Example:

```text
Dispatch:

DS-000001


Driver:

Carlos


Vehicle:

Truck 05
```

---

# 13. Source-Based Dispatch

Dispatch must consider delivery origin.

Example:

```text
Store Centro

Dispatch A


CD Guarulhos

Dispatch B
```

Different sources may have:

* different schedules;
* different resources;
* different delivery rules.

---

# 14. POS Integration

POS flow:

```text
POS Sale

↓

Delivery Order

↓

Dispatch Queue

↓

Assignment

↓

Delivery
```

The cashier does not manage dispatch.

---

# 15. WMS Integration

WMS releases products.

Flow:

```text
Picking Completed

↓

Packing Completed

↓

Available For Dispatch

↓

Dispatch Assignment
```

---

# 16. Dispatch Board

The system should provide an operational view:

Example:

```text
TODAY DELIVERY BOARD


Waiting Assignment

DO-001
DO-002


Assigned

DO-003
Driver Carlos


In Transit

DO-004
Driver Maria
```

---

# 17. Dispatch Events

All actions must be recorded:

```text
Dispatch Created

Delivery Added

Resource Assigned

Dispatch Released

Dispatch Completed
```

---

# 18. Exception Management

Dispatch must handle:

```text
Delivery Delayed

Driver Unavailable

Vehicle Problem

Customer Request Change

Delivery Cancelled
```

---

# 19. Future Extensions

Possible future RFCs:

```text
RFC-18004 Delivery Resources

RFC-18005 Delivery Scheduling

RFC-18006 Delivery Tracking

RFC-18007 Proof of Delivery

RFC-18008 Delivery Analytics
```

---

# 20. Final Architecture Rule

Dispatch is the operational control center between planning and execution.

```text
Sales creates demand.

WMS prepares products.

Delivery Order defines destination.

Dispatch organizes execution.

Delivery Tasks perform the work.
```

> **Simple is always better than complex.**
