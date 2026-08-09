# RFC-9018 - Carrier Coordination

| Field       | Value                                  |
| ----------- | -------------------------------------- |
| RFC         | RFC-9018                               |
| Title       | Carrier Coordination                   |
| Status      | Draft                                  |
| Version     | 1.0                                    |
| Category    | WMS                                    |
| Authors     | Business Platform Team                 |
| Depends On  | RFC-9000, RFC-9008, RFC-9015, RFC-9016 |
| Required By | RFC-9019                               |
| Updated     | 2026-08-01                             |

---

## Platform Philosophy

> **Simple is always better than complex.**
> Simples é sempre melhor do que complexo.

Design systems that are easy to understand, easy to maintain, easy to extend, and easy to use.
Avoid unnecessary abstractions. Prefer explicit behavior over hidden magic.
Every feature should solve a real business problem.
Performance and maintainability always come first.

---

# Table of Contents

1. Abstract
2. Motivation
3. Objectives
4. Non-Objectives
5. Core Principles
6. Business Concept
7. Carrier Coordination Lifecycle
8. Coordination Workflow
9. Assignment Policies
10. Exception Handling
11. Integrations
12. Analytics
13. Security
14. Design Principles
15. Future Evolution

---

# 1. Abstract

This RFC defines the Carrier Coordination architecture for the Warehouse Management System (WMS).

Carrier Coordination is responsible for coordinating warehouse operations with external transportation providers.

Its purpose is to synchronize warehouse execution with carrier activities, ensuring that goods are available at the correct dock, at the correct time, for the correct transportation operation.

Carrier Coordination manages operational synchronization.

It does not manage transportation.

---

# 2. Motivation

Warehouse efficiency alone is insufficient.

A warehouse may complete all shipping activities on time while transportation remains delayed due to poor coordination.

Typical problems include:

* carrier delays;
* incorrect dock assignment;
* premature loading;
* missed appointments;
* vehicle congestion;
* shipment prioritization conflicts.

Carrier Coordination minimizes these operational gaps.

---

# 3. Objectives

Carrier Coordination shall:

* coordinate warehouse operations with carriers;
* synchronize shipment readiness;
* monitor transportation appointments;
* improve loading efficiency;
* reduce carrier waiting time;
* increase operational visibility;
* support multiple transportation providers.

---

# 4. Non-Objectives

Carrier Coordination does not:

* create transportation routes;
* calculate freight;
* dispatch vehicles;
* optimize delivery routes;
* manage drivers;
* manage fleets;
* replace a Transportation Management System (TMS).

Those responsibilities belong to the future Logistics/TMS domain.

---

# 5. Core Principles

## Principle 1

Transportation remains an external domain.

---

## Principle 2

Warehouse Operations remain independent.

---

## Principle 3

Synchronization replaces direct dependency.

---

## Principle 4

Every coordination event is auditable.

---

## Principle 5

Simple is always better than complex.

---

# 6. Business Concept

The operational sequence is:

```text
Sales Order

↓

Warehouse Tasks

↓

Picking

↓

Packing

↓

Shipment Ready

↓

Carrier Coordination

↓

Dock Assignment

↓

Loading

↓

Departure
```

Carrier Coordination begins only after the shipment becomes operationally ready.

---

# 7. Carrier Coordination Lifecycle

```text
Planned

↓

Carrier Assigned

↓

Appointment Confirmed

↓

Vehicle Arrived

↓

Dock Assigned

↓

Loading

↓

Released

↓

Completed
```

Exception states:

```text
Delayed

Waiting Carrier

Blocked

Cancelled
```

Every state transition is recorded.

---

# 8. Coordination Workflow

```text
Shipment Ready

↓

Carrier Confirmation

↓

Arrival Monitoring

↓

Dock Scheduling

↓

Loading Authorization

↓

Departure Confirmation

↓

Operation Completed
```

Carrier Coordination synchronizes all events without controlling warehouse execution itself.

---

# 9. Assignment Policies

Carrier assignment may consider:

### Operational Priority

* emergency;
* express;
* standard.

---

### Appointment Window

Scheduled loading period.

---

### Dock Availability

Integration with RFC-9016.

---

### Shipment Characteristics

* volume;
* weight;
* hazardous goods;
* refrigeration;
* oversized cargo.

---

### Carrier Capability

Capability requirements are provided by the future TMS.

The WMS consumes these capabilities without managing them.

---

# 10. Exception Handling

Examples:

* carrier delay;
* missed appointment;
* vehicle unavailable;
* dock unavailable;
* shipment not ready;
* loading interruption;
* documentation pending.

Every exception generates an auditable operational event.

---

# 11. Integrations

### Input

* RFC-9008 – Shipping Process
* RFC-9015 – Yard Management
* RFC-9016 – Dock Scheduling

### Output

* RFC-9009 – Warehouse Analytics
* RFC-9019 – Warehouse Optimization Rules
* Future Logistics/TMS Domain

Carrier Coordination exchanges operational events with the future TMS but does not own transportation data.

---

# 12. Analytics

Operational indicators include:

* carrier punctuality;
* average waiting time;
* loading start delay;
* loading completion time;
* dock occupancy by carrier;
* carrier utilization;
* missed appointments;
* on-time departures.

These indicators improve warehouse and transportation coordination.

---

# 13. Security

Carrier Coordination respects:

* company permissions;
* warehouse permissions;
* shipment permissions;
* dock permissions;
* supervisor approvals.

Carrier events remain fully auditable.

---

# 14. Design Principles

Carrier Coordination follows these principles:

* separate warehouse operations from transportation management;
* synchronize operational events;
* maximize loading efficiency;
* preserve traceability;
* configure behavior through business policies;
* remain independent from future TMS implementations.

---

# 15. Future Evolution

Future capabilities may include:

* native TMS integration;
* EDI carrier communication;
* GPS shipment tracking;
* ETA prediction;
* automatic carrier notifications;
* AI-based carrier selection;
* autonomous loading coordination.

These capabilities extend Carrier Coordination without modifying the WMS Core architecture.

---

# Final Considerations

Carrier Coordination is the integration layer between warehouse execution and transportation.

It is intentionally limited to operational synchronization.

Transportation planning, fleet management, freight calculation and route optimization belong to the future Logistics/TMS domain.

This separation keeps the Warehouse Management System focused on warehouse execution while allowing seamless integration with specialized transportation solutions.

```text
Warehouse

        │

        ▼

Carrier Coordination

        │

        ▼

Transportation (Future TMS)
```

The WMS knows **when** a shipment is ready.

The TMS knows **how** it will be transported.

Each domain remains independent while cooperating through well-defined operational events.

> **Carrier Coordination synchronizes warehouse execution with transportation. Transportation Management plans transportation.**

> **Simple is always better than complex.**
