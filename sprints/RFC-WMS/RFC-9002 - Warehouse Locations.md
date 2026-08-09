# RFC-9002 - Warehouse Locations

| Field | Value |
|--------|-------|
| RFC | 9002 |
| Name | Warehouse Locations |
| Category | WMS Core |
| Status | Draft |
| Version | 1.0 |

---

## Platform Philosophy

> **Simple is always better than complex.**
> Simples é sempre melhor do que complexo.

Design systems that are easy to understand, easy to maintain, easy to extend, and easy to use.
Avoid unnecessary abstractions. Prefer explicit behavior over hidden magic.
Every feature should solve a real business problem.
Performance and maintainability always come first.

---

# 1. Objective

This RFC defines the warehouse location model within the WMS Core domain.

Warehouse Locations provide the detailed physical and logical addressing system required for warehouse operations.

---

# 2. Motivation

A warehouse is composed of thousands of inventory positions.

Effective warehouse management requires precise location control.

The system must answer:

- where inventory is stored;
- where products should be picked;
- where products are received;
- where products are moving;
- where products are waiting for processing.

---

# 3. Responsibilities

Warehouse Locations are responsible for:

- representing physical storage positions;
- defining location hierarchy;
- controlling inventory placement;
- supporting warehouse operations;
- enabling optimization strategies.

---

# 4. Non Responsibilities

Warehouse Locations do not:

- execute movements;
- reserve inventory;
- create warehouse tasks;
- calculate costs;
- create accounting records.

Locations provide the physical context.

---

# 5. Location Hierarchy

Locations follow a hierarchical model:
Warehouse

↓

Area

↓

Zone

↓

Aisle

↓

Rack

↓

Level

↓

Position


Example:


DC-SP-01

Storage Area

    Aisle A01

        Rack 03

            Level 02

                Position 05

---

# 6. Location Types

The system supports different location behaviors.

---

## Receiving Location

Temporary location for incoming goods.

Example:


Receiving Dock


Purpose:

- unloading;
- inspection;
- validation.

---

## Quality Inspection Location

Used for products awaiting approval.

Example:


Quality Hold Area


---

## Storage Location

Permanent inventory storage.

Example:


A01-03-02


---

## Picking Location

Optimized for order preparation.

Example:


Picking Zone


---

## Packing Location

Used before shipment.

---

## Shipping Location

Temporary area before dispatch.

---

## Transit Location

Used during internal movement.

Example:


Transfer In Progress


---

## Virtual Location

Logical locations.

Examples:


Supplier

Customer

Inventory Adjustment

Scrap

Repair Center


---

# 7. Fixed vs Dynamic Storage

The system supports two strategies.

---

## Fixed Location

A product has a predefined location.

Example:


Product:

Samsung Refrigerator

Location:

REFRIGERATION-A01


Advantages:

- easy operation;
- predictable picking.

---

## Dynamic Location

The system determines placement.

Example:


Incoming Product

↓

WMS Calculates Best Location


Based on:

- available space;
- product category;
- weight;
- turnover.

---

# 8. Location Attributes

Each location may contain:

- code;
- description;
- type;
- warehouse;
- capacity;
- weight limit;
- volume limit;
- status;
- allowed products.

---

# 9. Capacity Management

Locations may control:

## Quantity

Example:


Maximum:

20 units


---

## Weight

Example:


Maximum:

1000 kg


---

## Volume

Example:


Maximum:

10 m³


---

# 10. Storage Rules

WMS may define placement rules.

Examples:

## Product Category


Large Appliances

↓

Furniture Zone


---

## Temperature


Frozen Products

↓

Cold Storage


---

## Hazard Classification


Special Products

↓

Restricted Area


---

# 11. Location Status

Locations have lifecycle states:


Available

↓

Restricted

↓

Blocked

↓

Inactive


---

# 12. Location Blocking

A location may be temporarily blocked.

Reasons:

- maintenance;
- inventory counting;
- safety issue;
- contamination;
- organization.

---

# 13. Inventory Visibility

The system can provide:

Example:


Product:

TV 55"

Locations:

DC-SP

A01-02-03

    15 units

Store Campinas

    5 units

---

# 14. Integration

Warehouse Locations integrate with:

## Stock Movement


Source Location

↓

Destination Location


---

## Picking


Order

↓

Picking Route

↓

Locations


---

## Inventory Counting


Location

↓

Count Task


---

# 15. Traceability

Every location change must maintain:

- previous location;
- new location;
- date;
- responsible user;
- related operation.

---

# 16. Architecture Principles

Warehouse Locations follow:

- physical reality must be represented;
- locations are operational assets;
- inventory position must always be known;
- movements require origin and destination;
- simple is always better than complex.

---

# 17. Roadmap

Next RFCs:

- RFC-9003 - Operation Types
- RFC-9004 - Warehouse Operations
- RFC-9005 - Warehouse Tasks

---

# 18. Final Considerations

Warehouse Locations provide the addressing foundation of the WMS.

They enable:

- precise inventory control;
- efficient picking;
- traceability;
- warehouse optimization;
- future automation.

A warehouse without locations is only a stock container.

A WMS begins when the system understands space.

> **Simple is always better than complex.**
