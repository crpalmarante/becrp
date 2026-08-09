# RFC-18001 - Delivery Orders

| Field           | Value                                  |
| --------------- | -------------------------------------- |
| RFC             | RFC-18001                              |
| Title           | Delivery Orders                        |
| Status          | Done                                  |
| Version         | 1.0                                    |
| Domain          | Delivery Platform                      |
| Depends On      | RFC-18000 Delivery Core                |
| Integrates With | Sales, POS, WMS, Inventory, Party Core |
| Author          | Business Platform Team                 |

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

This RFC defines the Delivery Order entity and its operational lifecycle.

A Delivery Order represents the execution request responsible for moving products from an operational source location to customer destinations.

A Delivery Order is generated from commercial transactions but operates independently from Sales Orders.

---

# 2. Core Principle

A Sales Order represents:

```text
What was sold
```

A Delivery Order represents:

```text
How the product will be delivered
```

---

# 3. Relationship Model

The platform supports:

```text
Sales Order

        1

        |

        N

Delivery Orders
```

Example:

A customer buys:

```text
SO-000100

10 products
```

The system may create:

```text
DO-000101

Delivery tomorrow


DO-000102

Delivery next week
```

---

# 4. Delivery Order Responsibilities

Delivery Order manages:

* delivery execution;
* source location;
* customer destination plan;
* delivery status;
* assigned resources;
* delivery events;
* operational tracking.

---

# 5. Non Responsibilities

Delivery Order does not:

* calculate sales prices;
* manage customer payments;
* issue invoices;
* reserve inventory;
* execute warehouse picking.

---

# 6. Main Entity

## Delivery Order

Example:

```text
Delivery Order

Number:
DO-000001


Customer:
John Smith


Source:
Store SP Centro


Status:
Ready


Scheduled Date:
2026-08-10
```

---

# 7. Delivery Order Structure

```text
Delivery Order

├── Header
│
├── Source
│
├── Customer
│
├── Delivery Stops
│
├── Delivery Items
│
├── Schedule
│
├── Status History
│
└── Events
```

---

# 8. Delivery Order Header

Required fields:

```text
delivery_order_id

number

company_id

customer_id

source_location_id

status

created_date
```

---

# 9. Delivery Source

Every Delivery Order must have an origin.

Examples:

```text
Store

Warehouse

Distribution Center

Branch
```

Example:

```text
Source:

WH-001

CD Guarulhos
```

---

# 10. Delivery Stops

A Delivery Order may contain multiple destinations.

Example:

```text
DO-000001


Stop 001

Customer Home

Products:
TV


Stop 002

Son Address

Products:
TV


Stop 003

Mother Address

Products:
TV
```

---

# 11. Delivery Items

Products are assigned at stop level.

Example:

```text
Delivery Stop


Items:

Product:
TV 55"

Quantity:
1
```

This allows:

* partial delivery;
* split delivery;
* multiple addresses.

---

# 12. Delivery Status

Lifecycle:

```text
Draft

↓

Confirmed

↓

Waiting Stock

↓

Ready

↓

Assigned

↓

In Transit

↓

Delivered

↓

Completed
```

---

# 13. Status Rules

## Draft

Delivery created but not confirmed.

---

## Confirmed

Delivery plan approved.

---

## Waiting Stock

Products unavailable.

Waiting for WMS.

---

## Ready

Products available and prepared.

---

## Assigned

Delivery resource assigned.

---

## In Transit

Delivery started.

---

## Delivered

Customer received products.

---

## Completed

All validations finished.

---

# 14. Integration With Sales

Example:

```text
Sales Order

SO-000123


Lines:

3 TVs


Delivery Plan:


DO-000001

TV
Customer Address


DO-000002

TV
Son Address


DO-000003

TV
Mother Address
```

---

# 15. Integration With POS

POS creates Delivery Order when:

```text
Delivery Required = Yes
```

Example:

```text
POS Sale

Payment completed

        |

        ▼

Delivery Order Created
```

---

# 16. Integration With WMS

Delivery Order requests warehouse execution.

Flow:

```text
Delivery Order

        |

        ▼

Warehouse Picking

        |

        ▼

Packing

        |

        ▼

Ready For Delivery
```

---

# 17. Cancellation

Delivery Order cancellation requires:

* authorization;
* reason;
* audit event.

Examples:

```text
Customer Cancelled

Wrong Address

Stock Issue

Operational Problem
```

---

# 18. Audit Trail

Every Delivery Order stores:

* creation user;
* modifications;
* status changes;
* assignment changes;
* completion events.

---

# 19. Future Extensions

Related RFCs:

```text
RFC-18002 Delivery Tasks

RFC-18003 Dispatch Management

RFC-18004 Delivery Resources

RFC-18005 Delivery Scheduling

RFC-18006 Delivery Tracking

RFC-18007 Proof of Delivery

RFC-18008 Delivery Analytics
```

---

# Final Architecture Rule

The Delivery Order is the operational bridge between commerce and logistics.

```text
Sales creates demand.

WMS prepares products.

Delivery executes fulfillment.

Customer receives.
```

> **One sale can create many delivery orders.**

> **Simple is always better than complex.**
