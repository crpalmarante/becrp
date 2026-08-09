# RFC-18110 - Trip Start

| Field           | Value                                                                            |
| --------------- | -------------------------------------------------------------------------------- |
| RFC             | RFC-18110                                                                        |
| Title           | Trip Start                                                                       |
| Status          | Done                                                                            |
| Version         | 1.0                                                                              |
| Domain          | Delivery Platform                                                                |
| Depends On      | RFC-18105 Delivery Manifest, RFC-18106 Delivery Trip, RFC-18107 Driver Workspace |
| Integrates With | Tracking, Fleet, HR (Future), WMS                                                |
| UI              | BusinessUI Mobile                                                                |
| Author          | Business Platform Team                                                           |

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

This RFC defines the Trip Start process.

Trip Start is the operational event that officially begins the execution of a Delivery Trip.

From this point forward, all delivery operations become active and operational tracking begins.

---

# 2. Objectives

Trip Start determines:

* when the trip actually begins;
* who started the trip;
* which vehicle is being used;
* the initial execution timestamp;
* the operational baseline for the trip.

---

# 3. Core Principle

A Trip is only considered active after the **Start Trip** event.

```text
Manifest Released

        │

        ▼

Trip Ready

        │

Start Trip

        ▼

Trip In Progress
```

---

# 4. Preconditions

Before starting a Trip:

* Manifest must be Released.
* Trip status must be Ready.
* Driver must be assigned.
* Vehicle must be assigned.
* Driver must be authenticated.

Optional validations:

* vehicle inspection completed;
* battery/fuel level recorded;
* required documents available.

---

# 5. Start Workflow

```text
Driver Login

        │

        ▼

Open Assigned Trip

        │

        ▼

Review Summary

        │

        ▼

Start Trip

        │

        ▼

Tracking Begins
```

---

# 6. Trip Summary

Before confirmation the driver sees:

* Trip Number
* Manifest Number
* Driver
* Vehicle
* Number of Stops
* Estimated Duration
* Estimated Distance
* Planned Departure Time

---

# 7. Confirmation

The driver confirms:

```text
Trip Ready

↓

Start Trip

↓

Confirmation

↓

Trip Started
```

Confirmation may require a PIN or biometric authentication according to company policy.

---

# 8. Recorded Information

The system records:

* Start Timestamp
* Driver
* Vehicle
* Device
* Optional GPS Position
* User Session
* Initial Trip Status

These values become immutable historical records.

---

# 9. Tracking Integration

Trip Start automatically creates:

* Trip Started event;
* Tracking Started event;
* first Trip Timeline entry.

---

# 10. Driver Workspace

After Trip Start the interface changes automatically.

The workspace focuses on:

* current stop;
* navigation;
* trip progress;
* operational actions.

Planning functions become unavailable.

---

# 11. WMS Integration

Starting a Trip confirms that the released goods have left the warehouse.

The WMS may register:

* goods dispatched;
* warehouse exit timestamp;
* loading completed.

---

# 12. Fleet Integration

Future integration may include:

* odometer reading;
* fuel level;
* vehicle inspection checklist;
* telematics activation.

---

# 13. Business Rules

## Rule 1

Only one active Trip is allowed per driver.

---

## Rule 2

Only one active Trip is allowed per vehicle.

---

## Rule 3

A Trip cannot be started twice.

---

## Rule 4

Trip Start generates an immutable audit event.

---

## Rule 5

Cancelling a started Trip requires an explicit operational reason.

---

# 14. Exception Handling

Trip Start may fail if:

* driver is unavailable;
* vehicle is unavailable;
* manifest is not released;
* trip already started;
* mandatory validations failed.

The system must clearly report the blocking condition.

---

# 15. Future Enhancements

Possible future capabilities:

* automatic start by geofencing;
* NFC vehicle identification;
* QR code trip activation;
* electronic pre-trip inspection;
* digital departure authorization.

---

# 16. Final Architecture Rule

Trip Start is the official beginning of operational execution.

Planning prepares the work.

Trip Start authorizes execution.

From this moment, every operational event belongs to the Trip history.

```text
Planning

↓

Manifest

↓

Trip Ready

↓

Trip Start

↓

Tracking

↓

Stops

↓

Proof of Delivery
```

The **Start Trip** event establishes the operational reference point for the entire delivery lifecycle.

> **Simple is always better than complex.**
