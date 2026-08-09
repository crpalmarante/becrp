# RFC-18104 - Delivery Calendar

| Field           | Value                                                                                  |
| --------------- | -------------------------------------------------------------------------------------- |
| RFC             | RFC-18104                                                                              |
| Title           | Delivery Calendar                                                                      |
| Status          | Done                                                                                  |
| Version         | 1.0                                                                                    |
| Domain          | Delivery Platform                                                                      |
| Depends On      | RFC-18001 Delivery Orders, RFC-18005 Delivery Scheduling, RFC-18100 Delivery Workspace |
| Integrates With | Dispatch, Planning Board, Tracking, Sales, POS                                         |
| UI              | BusinessUI                                                                             |
| Author          | Business Platform Team                                                                 |

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

This RFC defines the Delivery Calendar.

The Delivery Calendar provides a time-oriented view of delivery operations.

Instead of organizing deliveries by operational resource, it organizes them by date and time.

The calendar is one of the primary operational planning tools for delivery supervisors.

---

# 2. Objectives

The Delivery Calendar answers:

* What deliveries are scheduled today?
* Which delivery windows are fully booked?
* Which periods still have capacity?
* Which deliveries require rescheduling?
* What is tomorrow's workload?

---

# 3. Core Principle

The Delivery Calendar is a scheduling visualization.

It never owns delivery information.

```text
Delivery Scheduling

        │

        ▼

Delivery Calendar

        │

        ▼

Operational Planning
```

---

# 4. Calendar Views

The calendar supports:

* Day View
* Week View
* Month View
* Timeline View

The default view is **Day View**.

---

# 5. Screen Layout

```text
+----------------------------------------------------------------+

Delivery Calendar

------------------------------------------------------------------

Today   Week   Month

------------------------------------------------------------------

08:00

DO-00123

Carlos

Downtown

------------------------------------------------------------------

10:00

DO-00140

Maria

North Zone

------------------------------------------------------------------

14:00

DO-00155

João

South Zone

------------------------------------------------------------------

17:00

DO-00180

Carrier ABC
```

---

# 6. Calendar Events

Each delivery appears as a calendar event.

Displayed information:

* Delivery Number
* Customer
* Time Window
* Driver
* Delivery Region
* Status

Colors indicate operational status.

---

# 7. Delivery Windows

Example:

```text
08:00–10:00

6 Deliveries


10:00–12:00

8 Deliveries


13:00–18:00

18 Deliveries
```

The calendar displays remaining capacity for each window.

---

# 8. Capacity Indicators

Each period displays:

* planned deliveries;
* available capacity;
* utilization percentage.

Example:

```text
Morning

Capacity

20


Scheduled

18


Available

2
```

---

# 9. Calendar Colors

Suggested color convention:

Green

* Scheduled

Blue

* Assigned

Orange

* In Transit

Gray

* Completed

Red

* Delayed

Dark Red

* Failed

BusinessUI themes may redefine colors while preserving semantic meaning.

---

# 10. Calendar Actions

Users may:

* open delivery;
* reschedule;
* assign driver;
* change delivery window;
* view tracking;
* open customer information.

---

# 11. Drag and Drop

Calendar supports:

* moving deliveries;
* changing time slots;
* changing delivery dates.

Every modification generates an audit event.

---

# 12. Conflict Detection

The calendar warns about:

* overloaded periods;
* unavailable resources;
* driver conflicts;
* duplicate assignments;
* exceeded capacity.

Warnings do not automatically block planning unless configured.

---

# 13. Multiple Delivery Stops

One Delivery Order may appear as:

Single event

or

Expanded event

Example:

```text
DO-00120

09:00

Stop 1


11:00

Stop 2


15:00

Stop 3
```

---

# 14. Filters

Available filters:

* Company
* Branch
* Warehouse
* Driver
* Vehicle
* Team
* Region
* Customer
* Delivery Status
* Priority
* Dispatch

Filters affect every calendar view.

---

# 15. Integration With Planning Board

Planning Board determines:

Who performs the work.

Calendar determines:

When the work occurs.

Both views represent the same Delivery Orders.

---

# 16. Integration With Tracking

Once execution begins:

```text
Scheduled

↓

In Transit

↓

Delivered
```

The calendar updates automatically.

---

# 17. Integration With Sales and POS

Sales and POS may display:

* requested delivery date;
* confirmed delivery date;
* confirmed delivery window.

These values originate from Delivery Scheduling.

---

# 18. Business Rules

## Rule 1

A confirmed delivery reserves calendar capacity.

---

## Rule 2

Changing the delivery date updates Scheduling.

---

## Rule 3

Completed deliveries become historical events.

---

## Rule 4

Cancelled deliveries disappear from active views.

---

# 19. Future Enhancements

Possible future features:

* Public holiday awareness
* Weather forecast integration
* Traffic prediction
* AI scheduling recommendations
* Recurring deliveries
* ICS calendar export

---

# 20. Final Architecture Rule

The Delivery Calendar is the temporal visualization layer of the Delivery Platform.

It organizes delivery execution by time without changing the underlying business data.

Together:

```text
Queue

↓

Planning Board

↓

Calendar

↓

Dispatch

↓

Execution

↓

Tracking
```

These components provide complete operational visibility while keeping responsibilities clearly separated.

> **Simple is always better than complex.**
