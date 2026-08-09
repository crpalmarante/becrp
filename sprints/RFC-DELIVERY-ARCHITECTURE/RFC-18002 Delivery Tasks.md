# RFC-18002 - Delivery Tasks

| Field           | Value                                              |
| --------------- | -------------------------------------------------- |
| RFC             | RFC-18002                                          |
| Title           | Delivery Tasks                                     |
| Status          | Done                                              |
| Version         | 1.0                                                |
| Domain          | Delivery Platform                                  |
| Depends On      | RFC-18000 Delivery Core, RFC-18001 Delivery Orders |
| Integrates With | WMS, Sales, POS, Driver Resource, Tracking         |
| Author          | Business Platform Team                             |

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

This RFC defines the Delivery Task entity.

Delivery Tasks represent the operational activities required to complete a Delivery Order.

A Delivery Order describes the delivery requirement.

A Delivery Task describes the execution work.

---

# 2. Core Principle

The platform must separate:

```text
Delivery Order

=
Business Delivery Document
```

from:

```text
Delivery Task

=
Operational Execution Unit
```

---

# 3. Relationship Model

The relationship is:

```text
Delivery Order

        1

        |

        N

Delivery Tasks
```

Example:

```text
Delivery Order DO-000123

        |

        +-- Task 001
        |
        +-- Task 002
        |
        +-- Task 003
```

---

# 4. Why Delivery Tasks Exist

A delivery is not a single action.

A real delivery may require:

* verify availability;
* load vehicle;
* assign driver;
* travel;
* arrive at destination;
* unload;
* collect signature;
* register proof.

---

# 5. Example Scenario

Customer purchases:

```text
3 TVs
```

Delivery:

```text
DO-000123
```

Execution:

```text
Task 001

Prepare delivery


Task 002

Load vehicle


Task 003

Transport to address 1


Task 004

Unload and install


Task 005

Confirm customer receipt
```

---

# 6. Delivery Task Entity

Example:

```text
Delivery Task

Number:
DT-000001


Type:
Delivery Execution


Related Delivery:
DO-000123


Status:
Assigned


Responsible:
Driver João
```

---

# 7. Task Types

Initial task types:

## Preparation Task

Responsible for preparing delivery.

Example:

* validate products;
* check documents.

---

## Loading Task

Vehicle loading.

Example:

* load products;
* verify quantities.

---

## Transportation Task

Movement to destination.

Example:

* start trip;
* navigate route.

---

## Delivery Stop Task

Execution at customer location.

Example:

* arrive;
* unload;
* deliver.

---

## Confirmation Task

Proof completion.

Example:

* signature;
* photo;
* customer confirmation.

---

# 8. Task Lifecycle

```text
Created

↓

Assigned

↓

Accepted

↓

Started

↓

Completed

↓

Cancelled
```

---

# 9. Task Assignment

A task may be assigned to:

* driver;
* delivery team;
* external carrier;
* operational user.

Example:

```text
Delivery Task

Assigned To:

Driver:
Carlos


Vehicle:
Truck 10
```

---

# 10. Delivery Task Status

## Created

Task generated.

---

## Assigned

Responsible defined.

---

## Accepted

Executor accepted task.

---

## Started

Execution started.

---

## Completed

Execution finished.

---

## Cancelled

Execution stopped.

---

# 11. Multiple Destinations

Delivery Tasks support multiple stops.

Example:

```text
Delivery Order


Task 001

Load truck


Task 002

Deliver Stop 1
Customer Home


Task 003

Deliver Stop 2
Son Address


Task 004

Deliver Stop 3
Mother Address
```

---

# 12. Integration With WMS

The relationship:

```text
WMS

Warehouse Task

        |

        ▼

Product Ready


        |

        ▼


Delivery Task
```

WMS prepares.

Delivery executes.

---

# 13. Integration With POS

POS does not create tasks directly.

Flow:

```text
POS Sale

↓

Sales Order

↓

Delivery Order

↓

Delivery Tasks
```

---

# 14. Task Events

Every task generates events.

Example:

```text
Task Created

Task Assigned

Task Started

Task Completed
```

Events are immutable.

---

# 15. Failure Handling

A task may fail.

Examples:

```text
Customer Not Available

Wrong Address

Vehicle Problem

Product Damage

Access Problem
```

Failure must generate:

* reason;
* timestamp;
* user;
* corrective action.

---

# 16. Future Integration

Delivery Tasks can later integrate with:

* mobile driver application;
* GPS tracking;
* route optimization;
* customer notifications.

---

# 17. Relationship With Other Modules

```text
Sales

creates demand


WMS

prepares goods


Delivery Order

defines delivery


Delivery Task

executes work


Customer

receives product
```

---

# 18. Final Architecture Rule

The platform must maintain:

```text
One Delivery Order

Many Delivery Tasks

Many Delivery Stops

Many Execution Events
```

The Delivery Task is the operational heartbeat of the Delivery Platform.

> **Simple is always better than complex.**
