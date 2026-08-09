# RFC-18000 - Delivery Core

| Field           | Value                                            |
| --------------- | ------------------------------------------------ |
| RFC             | RFC-18000                                        |
| Title           | Delivery Core                                    |
| Status          | Done                                            |
| Version         | 1.0                                              |
| Domain          | Delivery Platform                                |
| Depends On      | Party Core, Sales, Point of Sale, Inventory, WMS |
| Integrates With | Fiscal, Accounting, Customer Portal              |
| Author          | Business Platform Team                           |

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

This RFC defines the core architecture of the Delivery Domain.

Delivery Core provides the foundation for managing the delivery lifecycle generated from commercial transactions.

The module is responsible for coordinating the movement of sold products from an operational source location to one or multiple customer delivery destinations.

Delivery does not create sales.

Delivery does not replace warehouse operations.

Delivery executes the fulfillment process after the commercial decision.

---

# 2. Business Principle

The platform must separate three concepts:

```text
Sales

=
Commercial Transaction


Delivery

=
Physical Fulfillment


Invoice

=
Fiscal Transaction
```

A single sale may generate:

* one invoice;
* multiple deliveries;
* multiple delivery destinations.

---

# 3. Core Rule

## One Sale, Multiple Deliveries

The system must support:

```text
1 Sales Order

        |

        N Delivery Orders

        |

        N Delivery Stops
```

Example:

Customer buys:

```text
3 TVs
```

Commercial transaction:

```text
One Sales Order
```

Delivery:

```text
Stop 1
TV → Customer Home


Stop 2
TV → Son Address


Stop 3
TV → Mother Address
```

---

# 4. Domain Responsibilities

Delivery Core is responsible for:

* delivery lifecycle;
* delivery planning;
* delivery destinations;
* delivery status;
* delivery events;
* delivery pricing integration;
* delivery confirmation.

---

# 5. Non Responsibilities

Delivery Core does not:

* calculate product prices;
* create sales orders;
* calculate taxes;
* manage stock;
* perform picking;
* replace transportation systems.

---

# 6. Architecture Overview

```text
                    Customer

                       |

                       |

                 Sales Order

                       |

                       |

              Delivery Core

                       |

        +--------------+--------------+

        |                             |

 Delivery Order              Delivery Events


        |

        |

 Delivery Stops


        |

        |

 Delivery Address
```

---

# 7. Main Entities

## Delivery Order

Represents a delivery execution plan.

Example:

```
DO-000001

Source:
Store SP Centro

Customer:
João Silva

Status:
Ready
```

---

## Delivery Stop

Represents a destination point.

A Delivery Order can contain multiple stops.

Example:

```
Delivery Order

Stop 001
Address A

Stop 002
Address B

Stop 003
Address C
```

---

## Delivery Item

Represents products assigned to a delivery stop.

Example:

```
Stop 001

1x TV 55"
```

---

# 8. Delivery Lifecycle

## Delivery Order Status

```
Created

↓

Waiting Stock

↓

Ready

↓

Assigned

↓

Out For Delivery

↓

Delivered

↓

Completed

↓

Cancelled
```

---

# 9. Address Model

Delivery uses Party Core addresses.

A customer may have:

```
Customer

├── Invoice Address

├── Delivery Address

├── Other Addresses
```

Delivery always references:

```
Delivery Address
```

---

# 10. Sales Integration

Sales Order:

```
SO-000123

Customer:
John

Invoice Address:
Address A


Delivery Plan:

Delivery 1
Address B

Delivery 2
Address C
```

The Sales Order remains unique.

---

# 11. Point of Sale Integration

POS must support:

```
Sale

|
+-- Pickup
|
+-- Immediate Delivery
|
+-- Scheduled Delivery
|
+-- Multiple Delivery Addresses
```

Example:

```
3 TVs

Destination:

TV 1:
Customer

TV 2:
Son

TV 3:
Mother
```

---

# 12. WMS Integration

WMS prepares products.

Example:

```
Delivery Order

        |

        ▼

Warehouse Picking

        |

        ▼

Packed

        |

        ▼

Released For Delivery
```

Delivery does not perform inventory operations.

---

# 13. Delivery Source

Every delivery must have an origin.

Examples:

```
Store

Warehouse

Distribution Center

Branch
```

Example:

```
Source:

CD Guarulhos


Destination:

Pinheiros
```

---

# 14. Delivery Pricing Integration

Delivery price is based on:

```
Delivery Source

+

Delivery Destination

+

Delivery Rules
```

Example:

```
Store Centro SP

to

Pinheiros


Delivery Fee:

R$150,00
```

---

# 15. Delivery Events

Every action generates an event.

Examples:

```
Delivery Created

Delivery Assigned

Driver Started

Customer Received

Delivery Completed
```

Events must be auditable.

---

# 16. Future Extensions

Future RFCs:

```
RFC-18001 Delivery Orders

RFC-18002 Delivery Tasks

RFC-18003 Dispatch Management

RFC-18004 Delivery Resources

RFC-18005 Delivery Scheduling

RFC-18006 Delivery Tracking

RFC-18007 Proof of Delivery

RFC-18008 Delivery Analytics
```

---

# 17. Final Architecture Rule

The platform must preserve:

```
One Sale

Many Deliveries

Independent Invoice

Multiple Destinations
```

The commercial transaction, fiscal transaction and physical fulfillment are separate but connected domains.

---

# Conclusion

Delivery Core establishes the foundation for retail delivery operations.

It supports simple scenarios:

```
One sale

One delivery

One address
```

and advanced scenarios:

```
One sale

Multiple deliveries

Multiple destinations

Multiple schedules
```

without increasing complexity for basic users.

> **Simple is always better than complex.**
