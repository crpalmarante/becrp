# RFC-18103 - Delivery Planning Board

| Field           | Value                                                                                                                 |
| --------------- | --------------------------------------------------------------------------------------------------------------------- |
| RFC             | RFC-18103                                                                                                             |
| Title           | Delivery Planning Board                                                                                               |
| Status          | Done                                                                                                                 |
| Version         | 1.0                                                                                                                   |
| Domain          | Delivery Platform                                                                                                     |
| Depends On      | RFC-18001 Delivery Orders, RFC-18003 Dispatch Management, RFC-18004 Delivery Resources, RFC-18005 Delivery Scheduling |
| Integrates With | Delivery Queue, Delivery Workspace, Tracking, Analytics                                                               |
| UI              | BusinessUI                                                                                                            |
| Author          | Business Platform Team                                                                                                |

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

This RFC defines the Delivery Planning Board.

The Delivery Planning Board is the visual planning interface used to organize delivery operations before execution.

It allows dispatchers and supervisors to allocate deliveries, balance workloads and prepare the daily delivery operation.

---

# 2. Objectives

The Planning Board answers:

* Which deliveries are not assigned?
* Which driver has available capacity?
* Which vehicle is overloaded?
* Which delivery should be moved?
* Is today's operation balanced?

---

# 3. Core Principle

Planning precedes execution.

```text
Delivery Queue

        │

        ▼

Planning Board

        │

        ▼

Dispatch

        │

        ▼

Execution
```

The Planning Board changes operational assignments but never changes the commercial transaction.

---

# 4. Board Layout

```text
+-----------------------------------------------------------------------+

Filters

--------------------------------------------------------------------------

Unassigned

------------------------------------------------------

DO-001

DO-002

DO-003

--------------------------------------------------------------------------

Driver Carlos

DO-010

DO-011

--------------------------------------------------------------------------

Driver Maria

DO-020

DO-021

--------------------------------------------------------------------------

Driver João

(empty)

--------------------------------------------------------------------------
```

Each column represents a delivery resource or dispatch group.

---

# 5. Planning Modes

The board supports:

* Driver View
* Team View
* Vehicle View
* Dispatch View
* Delivery Zone View
* Time Window View

Users may switch between modes.

---

# 6. Drag and Drop

The board supports:

* assign delivery;
* move delivery;
* reorder delivery;
* change priority;
* reassign driver;
* change dispatch.

Every movement generates an audit event.

---

# 7. Unassigned Panel

Displays deliveries waiting for planning.

Typical reasons:

* no driver assigned;
* no vehicle assigned;
* waiting approval;
* recently created.

---

# 8. Driver Columns

Each driver column displays:

* assigned deliveries;
* workload;
* delivery count;
* estimated finish time;
* capacity usage.

Example:

```text
Driver

Carlos


Deliveries

12


Capacity

80%
```

---

# 9. Vehicle View

Vehicle mode displays:

* assigned vehicle;
* estimated load;
* occupied capacity;
* remaining capacity.

Example:

```text
Truck 05


Deliveries

14


Load

75%
```

---

# 10. Delivery Zone View

Planning by delivery region.

Example:

```text
Downtown

15 Deliveries


North Zone

22 Deliveries


South Zone

9 Deliveries
```

---

# 11. Time Window View

Planning according to customer commitments.

Example:

```text
08:00–12:00

12 Deliveries


13:00–18:00

18 Deliveries
```

---

# 12. Capacity Indicators

Each planning column displays:

* delivery count;
* estimated workload;
* occupancy percentage;
* overload warning.

Visual colors:

* Green
* Yellow
* Red

---

# 13. Operational Warnings

Planning warnings include:

* overloaded driver;
* overloaded vehicle;
* schedule conflict;
* insufficient capacity;
* delayed delivery;
* resource unavailable.

Warnings never prevent planning but require user acknowledgement when configured.

---

# 14. Planning Actions

Available actions:

* Assign Delivery
* Remove Assignment
* Move Delivery
* Split Deliveries
* Merge Dispatch
* Change Schedule
* View Delivery Details
* Open Tracking

---

# 15. Integration With Dispatch

Planning generates dispatch assignments.

```text
Planning Board

        │

        ▼

Dispatch Assignment

        │

        ▼

Dispatch Ready
```

---

# 16. Integration With Scheduling

Scheduling defines available delivery windows.

Planning must respect confirmed customer appointments unless explicitly overridden by an authorized user.

---

# 17. Integration With Tracking

After execution starts:

```text
Planning

↓

Dispatch

↓

Tracking

↓

Execution
```

Planning becomes read-only for deliveries already in execution, except for authorized exception handling.

---

# 18. Filters

Planning filters:

* Company
* Branch
* Warehouse
* Dispatch
* Driver
* Vehicle
* Region
* Priority
* Status
* Date
* Time Window

Filters apply instantly.

---

# 19. Business Rules

## Rule 1

Only active deliveries may be planned.

---

## Rule 2

Completed deliveries cannot return to planning.

---

## Rule 3

Every assignment change must be audited.

---

## Rule 4

Planning does not modify Sales Orders.

---

## Rule 5

Planning does not modify invoices.

---

# 20. Future Enhancements

Possible future capabilities:

* AI workload balancing
* Automatic planning suggestions
* Route optimization integration
* Traffic-aware planning
* Driver performance recommendations
* Multi-day planning board

---

# 21. Final Architecture Rule

The Delivery Planning Board is the visual operational planning layer of the Delivery Platform.

It transforms the Delivery Queue into an executable operational plan by allocating deliveries to available resources while respecting scheduling, capacity and business rules.

The Planning Board must optimize operational efficiency without compromising customer commitments.

> **Simple is always better than complex.**
