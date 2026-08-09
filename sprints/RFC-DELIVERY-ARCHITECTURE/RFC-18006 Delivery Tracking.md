# RFC-18006 - Delivery Tracking

| Field           | Value                                                                                                                                      |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| RFC             | RFC-18006                                                                                                                                  |
| Title           | Delivery Tracking                                                                                                                          |
| Status          | Done                                                                                                                                      |
| Version         | 1.0                                                                                                                                        |
| Domain          | Delivery Platform                                                                                                                          |
| Depends On      | RFC-18000 Delivery Core, RFC-18001 Delivery Orders, RFC-18002 Delivery Tasks, RFC-18003 Dispatch Management, RFC-18005 Delivery Scheduling |
| Integrates With | POS, Sales, Customer Portal, Mobile Delivery App, Maps, Notifications                                                                      |
| Author          | Business Platform Team                                                                                                                     |

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

This RFC defines the Delivery Tracking module.

Delivery Tracking provides visibility into the execution lifecycle of deliveries.

The module records delivery progress, operational events, customer communication and optional location information.

---

# 2. Core Principle

Tracking is not only location.

Tracking represents:

```text
Delivery State

+

Operational Events

+

Execution History

+

Customer Visibility
```

---

# 3. Responsibilities

Delivery Tracking manages:

* delivery status updates;
* delivery events;
* execution timeline;
* location updates;
* customer notifications;
* operational visibility.

---

# 4. Non Responsibilities

Delivery Tracking does not:

* create deliveries;
* assign resources;
* calculate routes;
* replace GPS platforms;
* replace Dispatch.

---

# 5. Architecture Overview

```text
Delivery Order

       |

       ▼

Delivery Tasks

       |

       ▼

Tracking Engine

       |

 +-----+------+------+

 ▼     ▼      ▼      ▼

Events GPS Notifications Customer View
```

---

# 6. Tracking Entity

## Delivery Tracking Record

Represents the current delivery execution state.

Example:

```text
Tracking:

Delivery:

DO-000123


Current Status:

Out For Delivery


Last Update:

10:30
```

---

# 7. Tracking Lifecycle

Delivery tracking follows:

```text
Created

↓

Scheduled

↓

Prepared

↓

Assigned

↓

Departed

↓

In Transit

↓

Arrived

↓

Delivered

↓

Confirmed
```

---

# 8. Tracking Events

Every change generates an event.

Example:

```text
Event:

Driver Started Delivery


Date:

2026-08-10 09:00


Resource:

Carlos
```

---

# 9. Event Types

Initial events:

## Delivery Created

Delivery generated.

---

## Delivery Scheduled

Time confirmed.

---

## Delivery Prepared

Products ready.

---

## Delivery Assigned

Driver/resource assigned.

---

## Driver Started

Execution started.

---

## In Transit

Delivery moving.

---

## Arrived At Destination

Reached customer location.

---

## Delivered

Customer received products.

---

## Delivery Failed

Problem occurred.

---

# 10. Tracking Timeline

The system should provide:

Example:

```text
Delivery DO-000123


08:00

Products prepared


09:00

Driver assigned


10:15

Driver departed


11:20

Arrived at customer


11:35

Delivery completed
```

---

# 11. Multiple Delivery Stops Tracking

A Delivery Order may contain multiple destinations.

Example:

```text
Delivery Order


Stop 1

Completed


Stop 2

In Progress


Stop 3

Pending
```

The global delivery status is calculated from stops.

---

# 12. Location Tracking

The platform may support:

* GPS coordinates;
* manual status updates;
* mobile application updates.

Example:

```text
Driver Mobile App

       |

       ▼

Location Update

       |

       ▼

Delivery Tracking
```

---

# 13. Customer Visibility

Customer may see:

```text
Order Status:

Preparing


Scheduled:

Saturday Morning


Current:

Out For Delivery
```

---

# 14. POS Integration

POS can display:

```text
Customer Order


Delivery Status:

Out For Delivery


Expected:

Today 14:00
```

---

# 15. Sales Integration

Sales users can view:

```text
Sales Order


Delivery:

Completed


Delivered:

2026-08-10
```

---

# 16. Exception Tracking

Tracking must record problems.

Examples:

```text
Customer unavailable

Wrong address

Product damaged

Delivery delayed

Vehicle problem
```

---

# 17. Audit Trail

Tracking history must be immutable.

Each event stores:

```text
Event Type

Date/Time

User/System

Location

Related Delivery
```

---

# 18. Notification Integration

Future notifications:

```text
Delivery Scheduled

Driver Leaving

Arriving Soon

Delivered
```

Channels:

* SMS;
* Email;
* WhatsApp;
* Customer Portal.

---

# 19. Mobile Delivery Integration

Future driver application:

```text
Driver App


Receive Task


Start Delivery


Update Status


Capture Proof


Complete
```

---

# 20. Final Architecture Rule

Delivery Tracking provides operational transparency.

```text
Scheduling

defines when


Dispatch

organizes


Resources

execute


Tracking

shows what happened
```

A complete delivery is not only performed.

It must be visible and auditable.

> **Simple is always better than complex.**
