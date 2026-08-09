# RFC-18004 - Delivery Resources

| Field           | Value                                                                            |
| --------------- | -------------------------------------------------------------------------------- |
| RFC             | RFC-18004                                                                        |
| Title           | Delivery Resources                                                               |
| Status          | Done                                                                            |
| Version         | 1.0                                                                              |
| Domain          | Delivery Platform                                                                |
| Depends On      | RFC-18000 Delivery Core, RFC-18002 Delivery Tasks, RFC-18003 Dispatch Management |
| Integrates With | Party Core, HR, Fleet, WMS, Sales                                                |
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

This RFC defines the Delivery Resource model.

Delivery Resources represent the operational entities capable of executing delivery activities.

A resource may represent:

* an individual driver;
* a delivery team;
* an external carrier;
* a vehicle;
* an operational partner.

---

# 2. Core Principle

Delivery Resources are operational capabilities.

They are not the same concept as:

```text
Employee
```

or:

```text
Vehicle
```

or:

```text
Supplier
```

Delivery consumes resources from other domains when necessary.

---

# 3. Domain Separation

The platform must maintain:

```text
HR

=
Employee Management
```

```text
Fleet

=
Vehicle Management
```

```text
Party Core

=
People and Organizations
```

```text
Delivery

=
Operational Resource Usage
```

---

# 4. Resource Architecture

```text
                  Delivery Resource


                         |

        +----------------+----------------+

        ▼                ▼                ▼


     Person           Team          Organization


        |                                |

        ▼                                ▼


    Driver                       Carrier
```

---

# 5. Resource Types

## Driver Resource

Represents a person capable of performing deliveries.

Example:

```text
Driver:

Carlos Silva


Capabilities:

- Delivery
- Installation
- Customer Contact
```

---

## Delivery Team

Represents a group of people.

Example:

```text
Team:

Furniture Installation Team A


Members:

Carlos

João
```

---

## Carrier Resource

Represents an external delivery company.

Example:

```text
Carrier:

Transportadora ABC Ltda
```

---

## Vehicle Resource

Represents the operational vehicle used during delivery.

Example:

```text
Vehicle:

Truck 001


Capacity:

1000 kg
```

---

# 6. Resource Entity

Example:

```text
Delivery Resource


ID:

RES-00001


Type:

Driver


Party:

Carlos Silva


Status:

Available
```

---

# 7. Resource Status

Lifecycle:

```text
Available

↓

Assigned

↓

Busy

↓

Unavailable

↓

Inactive
```

---

# 8. Resource Assignment

A resource may be assigned to:

* Dispatch;
* Delivery Task;
* Delivery Order.

Example:

```text
Dispatch:

DS-000001


Driver:

Carlos


Vehicle:

Truck 10
```

---

# 9. Multiple Resources

A delivery may require multiple resources.

Example:

Large furniture delivery:

```text
Delivery Task


Resources:


Driver:

Carlos


Assistant:

João


Vehicle:

Truck 05
```

---

# 10. Resource Capability

Resources may have capabilities.

Examples:

```text
Driver Carlos


Capabilities:

✓ Standard Delivery

✓ Heavy Product

✓ Installation
```

---

# 11. Integration With HR

HR owns:

```text
Employee Record
```

Delivery consumes:

```text
Delivery Resource
```

Example:

```text
HR

Carlos Silva

Employee


        |

        ▼


Delivery

Carlos Silva

Driver Resource
```

---

# 12. Integration With Party Core

External carriers are organizations.

Example:

```text
Party:

Transportadora ABC


Role:

Carrier


Delivery Resource:

External Carrier
```

---

# 13. Integration With Fleet

Future Fleet module may provide:

```text
Vehicle

Maintenance

Capacity

Documents
```

Delivery only uses:

```text
Vehicle Availability
```

---

# 14. Dispatch Integration

Dispatch assigns resources:

```text
Dispatch


Delivery Orders


        |


        ▼


Resources Assigned


        |


        ▼


Execution
```

---

# 15. Resource Availability

The system must support:

```text
Available

Unavailable

Scheduled

On Delivery

Off Duty
```

---

# 16. Resource History

The system must record:

* assignments;
* completed deliveries;
* workload;
* exceptions.

Example:

```text
Carlos

Delivered:

125 orders

Month:

August
```

---

# 17. Business Rules

## Rule 1

A Delivery Resource cannot execute a task without assignment.

---

## Rule 2

A resource may execute multiple deliveries over time.

---

## Rule 3

A resource assignment must be auditable.

---

# 18. Future Extensions

Related RFCs:

```text
RFC-18005 Delivery Scheduling

RFC-18006 Delivery Tracking

RFC-18007 Proof of Delivery

RFC-18008 Delivery Analytics
```

Future domains:

```text
Fleet Management

Transportation Management

Route Optimization
```

---

# 19. Final Architecture Rule

Delivery Resources represent operational capability.

The platform must avoid duplicating:

* employees;
* vehicles;
* partners.

The resource layer connects Delivery with other business domains.

```text
Party Core

defines who


HR

defines employees


Fleet

defines vehicles


Delivery

uses operational resources
```

> **Simple is always better than complex.**
