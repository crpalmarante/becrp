# RFC-18116 - Customer Refusal

| Field           | Value                                                                                                           |
| --------------- | --------------------------------------------------------------------------------------------------------------- |
| RFC             | RFC-18116                                                                                                       |
| Title           | Customer Refusal                                                                                                |
| Status          | Done                                                                                                           |
| Version         | 1.0                                                                                                             |
| Domain          | Delivery Platform                                                                                               |
| Depends On      | RFC-18001 Delivery Orders, RFC-18111 Stop Execution, RFC-18113 Delivery Exceptions, RFC-18115 Failed Deliveries |
| Integrates With | Sales, POS, WMS, Inventory, Customer Service, Tracking                                                          |
| UI              | BusinessUI                                                                                                      |
| Author          | Business Platform Team                                                                                          |

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

This RFC defines the Customer Refusal process.

Customer Refusal occurs when the delivery reaches the destination and the customer or authorized recipient explicitly refuses to receive the goods.

This process is distinct from operational delivery failures because the delivery attempt successfully reached the customer.

---

# 2. Objectives

Customer Refusal answers:

* Who refused the delivery?
* Why was the delivery refused?
* Were all items refused or only some?
* What evidence was collected?
* What is the next business action?

---

# 3. Core Principle

Customer Refusal is a business outcome.

It is not merely an operational failure.

```text
Delivery Attempt

        │

        ▼

Customer Contact

        │

        ├── Accepted

        └── Refused

                │

                ▼

Business Resolution
```

---

# 4. Refusal Entity

Each Customer Refusal records:

* Delivery Order
* Trip
* Stop
* Customer
* Recipient
* Refusal Timestamp
* Refusal Reason
* Resolution Status

---

# 5. Typical Refusal Reasons

Examples include:

* damaged goods;
* incorrect products;
* incorrect quantities;
* order cancelled by customer;
* customer changed their mind;
* late delivery;
* pricing disagreement;
* recipient not authorized;
* other.

Reason codes are configurable.

---

# 6. Refusal Scope

A refusal may affect:

* the entire delivery;
* selected products;
* selected quantities.

This supports partial acceptance scenarios.

---

# 7. Workflow

```text
Arrive

↓

Present Goods

↓

Customer Decision

↓

Accepted

or

Refused

↓

Business Resolution
```

---

# 8. Evidence

Evidence may include:

* recipient name;
* refusal reason;
* digital signature;
* photographs;
* driver observations;
* optional audio or supporting documents.

Evidence requirements are configurable.

---

# 9. Resolution Options

Possible resolutions include:

* return goods to warehouse;
* schedule a new delivery;
* replace products;
* issue a return authorization;
* escalate to customer service;
* cancel remaining deliveries.

The selected resolution is governed by company policy.

---

# 10. Inventory Integration

Refused goods are reconciled with warehouse operations.

Depending on the resolution, inventory may:

* return to available stock;
* enter inspection or quarantine;
* await quality evaluation;
* be prepared for a replacement shipment.

---

# 11. Customer Service Integration

Customer Refusal may automatically create a customer service case containing:

* refusal details;
* supporting evidence;
* assigned responsible team;
* follow-up history.

---

# 12. Tracking Integration

Tracking events include:

* Delivery Presented
* Customer Refused Delivery
* Refusal Recorded
* Resolution Started
* Resolution Completed

---

# 13. Business Rules

## Rule 1

A Customer Refusal always occurs after customer contact.

---

## Rule 2

Every refusal requires a reason code.

---

## Rule 3

Every refusal must preserve a complete audit trail.

---

## Rule 4

A refusal does not automatically cancel the Sales Order or Delivery Order.

Subsequent business actions determine the final outcome.

---

## Rule 5

Partial refusals are supported.

Accepted and refused quantities are recorded independently.

---

# 14. Performance Indicators

Operational KPIs include:

* refusal rate;
* refusals by reason;
* refusals by customer;
* refusals by product;
* average resolution time;
* replacement rate.

---

# 15. Future Enhancements

Possible future capabilities:

* electronic refusal forms;
* AI refusal pattern analysis;
* customer satisfaction correlation;
* automatic replacement recommendations;
* digital identity verification.

---

# 16. Final Architecture Rule

Customer Refusal records the customer's explicit decision not to accept the delivered goods.

It separates customer business decisions from operational execution failures, ensuring appropriate workflows for logistics, customer service and inventory management.

```text
Stop Execution

↓

Customer Decision

├── Accepted

└── Refused

        ↓

Customer Refusal

↓

Business Resolution

↓

Inventory / Customer Service / Sales
```

Customer Refusal preserves the integrity of commercial documents while providing a structured process for handling customer-driven delivery outcomes.

> **Simple is always better than complex.**

obs:
À primeira vista, parece que Customer Refusal poderia ser apenas um tipo de Failed Delivery, mas juridicamente e operacionalmente isso nem sempre é verdade.

Há uma diferença clara:

Failed Delivery → a entrega não pôde ser concluída por uma condição operacional.
Customer Refusal → a entrega pôde ser realizada, mas o destinatário recusou o recebimento.

Isso gera implicações diferentes:

pode exigir registro do motivo da recusa;
pode exigir assinatura do destinatário recusando;
pode gerar devolução ao estoque;
pode gerar devolução ao fornecedor;
pode envolver financeiro, SAC e faturamento;
pode ter implicações fiscais (dependendo do momento da recusa e dos documentos emitidos).

Por isso, eu trataria Customer Refusal como um processo de negócio próprio.
