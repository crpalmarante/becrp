# RFC-4007 - Receiving Pending Items

| Field | Value |
|--------|-------|
| RFC | 4007 |
| Name | Receiving Pending Items |
| Category | Receiving |
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

This RFC defines the **Receiving Pending Items** module of the Retail ERP.

The module is responsible for managing every unresolved issue that prevents a receiving process from reaching completion.

A pending item represents a business condition that requires validation, correction or approval before the receiving workflow can continue.

---

# 2. Motivation

Receiving is composed of multiple independent processes.

Any of these processes may temporarily block the workflow.

Examples include:

- Product not found
- Supplier requires validation
- Invalid XML
- Duplicate document
- Missing warehouse
- Missing tax configuration
- Inventory restriction
- Physical verification mismatch

Managing pending items in a dedicated module provides consistency, traceability and a uniform user experience.

---

# 3. Responsibilities

The module is responsible for:

- creating pending items;
- categorizing pending items;
- assigning responsible users;
- tracking resolution status;
- recording resolution history;
- notifying affected modules;
- publishing lifecycle events.

---

# 4. Non Responsibilities

The module does not:

- resolve inventory issues;
- calculate taxes;
- update suppliers;
- create products;
- import XML;
- execute receiving operations.

It only manages the lifecycle of pending items.

---

# 5. Pending Item Lifecycle

Every pending item follows the same lifecycle.

```
Detected

↓

Created

↓

Assigned

↓

In Progress

↓

Resolved

↓

Closed
```

Cancelled pending items terminate the lifecycle.

---

# 6. Pending Categories

Initial categories include:

### Product

- Product not found
- Multiple matches
- Invalid barcode

### Supplier

- Supplier not identified
- Supplier update approval

### XML

- Invalid XML
- Duplicate XML
- Unsupported document

### Inventory

- Warehouse unavailable
- Storage location missing
- Lot required
- Serial number required

### Fiscal

- Missing tax configuration
- Invalid CFOP
- Invalid fiscal rule

### Finance

- Payment condition missing
- Cost center missing

### System

- Internal processing error
- Integration timeout

New categories may be introduced without changing the module architecture.

---

# 7. Pending Item Structure

Each pending item contains:

```
PendingItem

-------------------------

id

receiving_id

category

type

priority

status

description

assigned_to

created_at

resolved_at
```

Additional metadata may be stored by specialized modules.

---

# 8. Priority Levels

Supported priorities:

- Low
- Medium
- High
- Critical

Priority affects sorting and notification only.

Business rules remain unchanged.

---

# 9. Assignment

Pending items may be assigned to:

- current user;
- specific operator;
- supervisor;
- role;
- work queue.

Assignment changes must be audited.

---

# 10. Resolution

Resolution depends on the pending type.

Examples:

Product Pending

↓

Associate product

↓

Resolved

Supplier Pending

↓

Approve supplier update

↓

Resolved

XML Pending

↓

Reprocess XML

↓

Resolved

The Pending Items module records the result but never executes the business operation.

---

# 11. User Interface

Pending items are displayed inside the Receiving Workspace.

Information includes:

- Category
- Description
- Priority
- Status
- Assigned User
- Creation Date
- Due Date (optional)

Users can navigate directly to the responsible module.

---

# 12. Notifications

The module may notify users when:

- a pending item is created;
- assignment changes;
- priority changes;
- resolution occurs;
- SLA is exceeded.

Notification delivery is handled by the platform notification service.

---

# 13. Audit

Every action must be recorded.

Examples:

- pending created;
- assignment changed;
- priority changed;
- resolved;
- reopened;
- cancelled.

The audit log is immutable.

---

# 14. Events

The module publishes:

```
pending.created

pending.assigned

pending.updated

pending.resolved

pending.closed

pending.reopened

pending.cancelled
```

Other modules may subscribe to these events.

---

# 15. Integrations

Receiving

Creates business pending items.

XML Monitor

Creates XML-related pending items.

Product Localization

Creates product matching pending items.

Supplier Update

Creates supplier approval pending items.

Inventory

Creates warehouse and stock pending items.

Fiscal

Creates fiscal validation pending items.

Finance

Creates financial configuration pending items.

---

# 16. Principles

The module follows these principles:

- Every unresolved issue becomes a pending item.
- Pending items never contain business logic.
- Resolution belongs to specialized modules.
- All changes are auditable.
- Communication occurs through events.
- One pending item represents one business problem.

---

# 17. Roadmap

Next RFCs:

- RFC-4008 - Physical Verification
- RFC-4009 - Inventory Integration
- RFC-4010 - Finance Integration
- RFC-4011 - Fiscal Integration
- RFC-4012 - Receiving Event Model

---

# 18. Final Considerations

Receiving Pending Items provides a centralized mechanism for managing unresolved business conditions during receiving operations.

By separating pending management from business execution, the platform remains modular, extensible and easier to maintain.

The module reinforces the architectural principle:

> **Simple is always better than complex.**
