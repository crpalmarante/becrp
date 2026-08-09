# RFC-18108 - Delivery Stops

| Field           | Value                                                                          |
| --------------- | ------------------------------------------------------------------------------ |
| RFC             | RFC-18108                                                                      |
| Title           | Delivery Stops                                                                 |
| Status          | Done                                                                          |
| Version         | 1.0                                                                            |
| Domain          | Delivery Platform                                                              |
| Depends On      | RFC-18001 Delivery Orders, RFC-18106 Delivery Trip, RFC-18107 Driver Workspace |
| Integrates With | Tracking, Proof of Delivery, Party Core, Scheduling                            |
| UI              | BusinessUI Mobile                                                              |
| Author          | Business Platform Team                                                         |

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

This RFC defines the Delivery Stop model.

A Delivery Stop represents one physical destination visited during a Delivery Trip.

Each stop has its own lifecycle, execution data and delivery confirmation.

---

# 2. Core Principle

A Trip is composed of one or more Stops.

```text
Delivery Trip

        │

        ├── Stop 1

        ├── Stop 2

        ├── Stop 3

        └── Stop N
```

Each Stop is independently executable.

---

# 3. Objectives

The Delivery Stop answers:

* Where is the next destination?
* Which customer will be served?
* Which items belong to this stop?
* Has this stop been completed?
* Was delivery accepted?

---

# 4. Stop Entity

Each stop contains:

* Stop Number
* Delivery Order
* Sequence
* Customer
* Delivery Address
* Contact
* Planned Time
* Arrival Time
* Departure Time
* Current Status

---

# 5. Relationship

```text
Delivery Trip

        1

        │

        ▼

Delivery Stops

        N
```

---

# 6. Stop Lifecycle

```text
Created

↓

Planned

↓

Waiting

↓

Arrived

↓

Servicing

↓

Completed

↓

Confirmed
```

Alternative endings:

```text
Failed

Cancelled

Skipped
```

---

# 7. Stop Sequence

Stops have an execution order.

Example:

```text
Trip 00045

1

Customer A

↓

2

Customer B

↓

3

Customer C
```

The sequence may be changed before execution according to business rules.

---

# 8. Multiple Deliveries Per Stop

One stop may contain multiple Delivery Orders.

Example:

```text
Stop

Shopping Mall


Delivery

DO-101


Delivery

DO-115


Delivery

DO-118
```

---

# 9. Multiple Stops Per Delivery

One Delivery Order may generate multiple stops.

Example:

```text
Delivery Order

↓

Stop 1

Home


↓

Stop 2

Office


↓

Stop 3

Warehouse
```

This supports partial and multi-address deliveries.

---

# 10. Stop Actions

Available actions:

* Navigate
* Arrive
* Start Service
* Deliver Items
* Capture Signature
* Take Photos
* Add Notes
* Finish Stop
* Skip Stop
* Report Problem

---

# 11. Arrival

When arriving:

The system records:

* arrival timestamp;
* optional GPS position;
* responsible resource.

---

# 12. Departure

When leaving:

The system records:

* departure timestamp;
* service duration;
* completion result.

---

# 13. Exceptions

Possible exceptions:

* customer absent;
* incorrect address;
* access denied;
* damaged goods;
* partial delivery;
* refused delivery.

Each exception creates a Tracking Event.

---

# 14. Integration With Proof of Delivery

Each completed stop may produce:

* recipient name;
* signature;
* photos;
* delivery notes;
* attachments.

Proof is stored per Stop.

---

# 15. Business Rules

## Rule 1

Every Trip must contain at least one Stop.

---

## Rule 2

Every completed Stop must have a final status.

---

## Rule 3

Skipping a Stop does not automatically cancel the Trip.

---

## Rule 4

Completing all Stops automatically qualifies the Trip for completion.

---

# 16. Future Enhancements

Possible future capabilities:

* QR code check-in
* Geofencing validation
* Customer arrival notification
* Time-on-site analysis
* Stop optimization
* Dynamic stop insertion

---

# 17. Final Architecture Rule

The Delivery Stop is the smallest operational execution unit of the Delivery Platform.

Planning creates Trips.

Trips organize Stops.

Stops generate Tracking.

Tracking produces Proof of Delivery.

```text
Trip

↓

Stop

↓

Tracking

↓

Proof

↓

Analytics
```

Every customer interaction during delivery occurs at the Stop level, making it the fundamental execution entity of the Delivery domain.

> **Simple is always better than complex.**
