# RFC-18005 - Delivery Scheduling

| Field           | Value                                                                                                           |
| --------------- | --------------------------------------------------------------------------------------------------------------- |
| RFC             | RFC-18005                                                                                                       |
| Title           | Delivery Scheduling                                                                                             |
| Status          | Done                                                                                                           |
| Version         | 1.0                                                                                                             |
| Domain          | Delivery Platform                                                                                               |
| Depends On      | RFC-18000 Delivery Core, RFC-18001 Delivery Orders, RFC-18003 Dispatch Management, RFC-18004 Delivery Resources |
| Integrates With | POS, Sales, WMS, Inventory, Calendar, Customer                                                                  |
| Author          | Business Platform Team                                                                                          |

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

This RFC defines the Delivery Scheduling module.

Delivery Scheduling manages the planning and reservation of delivery execution time.

It allows the platform to determine:

* when a delivery can occur;
* delivery capacity;
* available resources;
* customer preferred dates;
* operational constraints.

---

# 2. Core Principle

The system must separate:

```text
Sale Date

=

When customer bought
```

from:

```text
Delivery Date

=

When customer receives
```

---

# 3. Business Rule

A delivery promise must consider:

```text
Delivery Promise

=

Product Availability

+

Warehouse Readiness

+

Delivery Capacity

+

Customer Availability
```

---

# 4. Architecture Overview

```text
                 Sales / POS


                     |

                     ▼


          Delivery Scheduling


                     |

        +------------+------------+

        ▼                         ▼


 Availability              Delivery Slots


        |                         |


        ▼                         ▼


       WMS                 Customer Promise
```

---

# 5. Scheduling Entity

## Delivery Slot

Represents an available delivery window.

Example:

```text
Delivery Slot

Date:

2026-08-15


Period:

Morning


Capacity:

20 deliveries


Available:

8
```

---

# 6. Delivery Slot Types

Initial types:

## Same Day Delivery

Example:

```text
Order:

10:00


Delivery:

Today Afternoon
```

---

## Scheduled Delivery

Example:

```text
Order:

August 10


Delivery:

August 15
```

---

## Time Window Delivery

Example:

```text
08:00 - 12:00

or

13:00 - 18:00
```

---

# 7. Delivery Scheduling Flow

Example:

```text
POS Sale


Customer requests:

Saturday Morning


        |


        ▼


Scheduling Engine


        |


        ▼


Available Slot


        |


        ▼


Delivery Confirmed
```

---

# 8. POS Integration

POS must allow:

```text
Delivery Option:


Immediate


Scheduled


Customer Pickup
```

Example:

```text
Customer:

Maria


Delivery:

Saturday

Afternoon
```

---

# 9. Sales Integration

Sales Order stores:

```text
SO-000123


Requested Delivery Date:

2026-08-20


Confirmed Delivery Slot:

Morning
```

---

# 10. Capacity Management

Scheduling must consider:

```text
Daily Capacity


Available Drivers


Available Vehicles


Warehouse Preparation Capacity
```

Example:

```text
Saturday


Capacity:

50 deliveries


Booked:

45


Available:

5
```

---

# 11. Source Location Scheduling

Delivery capacity may depend on origin.

Example:

```text
Store Centro


Saturday:

20 deliveries


CD Guarulhos


Saturday:

80 deliveries
```

---

# 12. Product Constraints

Some products require special scheduling.

Examples:

```text
Large Furniture

Requires Installation


Heavy Equipment

Requires Special Vehicle
```

---

# 13. Multiple Delivery Destinations

The scheduler must support:

```text
One Sales Order


Delivery 1:

Monday


Delivery 2:

Wednesday


Delivery 3:

Friday
```

---

# 14. Rescheduling

The system must support changes.

Reasons:

```text
Customer Request

Stock Delay

Operational Issue

Vehicle Problem
```

All changes must generate events.

---

# 15. Delivery Promise

The customer-facing promise:

Example:

```text
Your order will be delivered:


August 20


Between:

08:00 - 12:00
```

---

# 16. Scheduling Status

```text
Requested

↓

Analyzing Capacity

↓

Scheduled

↓

Confirmed

↓

Rescheduled

↓

Cancelled
```

---

# 17. Integration With WMS

Scheduling checks:

```text
Product Available?


        ↓


Separated?


        ↓


Ready For Delivery?
```

A delivery cannot be promised without operational feasibility.

---

# 18. Business Rules

## Rule 1

A confirmed delivery slot reserves capacity.

---

## Rule 2

A delivery slot cannot exceed available capacity.

---

## Rule 3

Rescheduling must maintain history.

---

# 19. Future Extensions

Related RFCs:

```text
RFC-18006 Delivery Tracking

RFC-18007 Proof of Delivery

RFC-18008 Delivery Analytics
```

Future:

```text
Route Optimization

AI Delivery Forecast

Dynamic Capacity Planning
```

---

# 20. Final Architecture Rule

Delivery Scheduling connects customer expectation with operational reality.

```text
POS promises.

Sales records.

WMS prepares.

Scheduling organizes.

Delivery executes.
```

The goal is not only delivering products.

The goal is delivering the correct promise.

> **Simple is always better than complex.**
