# RFC-18115 - Failed Deliveries

| Field           | Value                                                                                                                                      |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| RFC             | RFC-18115                                                                                                                                  |
| Title           | Failed Deliveries                                                                                                                          |
| Status          | Done                                                                                                                                      |
| Version         | 1.0                                                                                                                                        |
| Domain          | Delivery Platform                                                                                                                          |
| Depends On      | RFC-18001 Delivery Orders, RFC-18108 Delivery Stops, RFC-18111 Stop Execution, RFC-18113 Delivery Exceptions, RFC-18114 Partial Deliveries |
| Integrates With | Sales, POS, WMS, Inventory, Tracking, Customer Service                                                                                     |
| UI              | BusinessUI                                                                                                                                 |
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

This RFC defines the Failed Delivery process.

A Failed Delivery occurs when a delivery attempt cannot be successfully completed and no goods are delivered to the customer during that attempt.

A Failed Delivery represents the failure of an execution attempt, not the cancellation of the commercial obligation.

---

# 2. Objectives

Failed Deliveries answer:

* Why did the delivery fail?
* Where did the failure occur?
* What should happen next?
* Is another delivery attempt required?
* Has the customer been informed?

---

# 3. Core Principle

A failed delivery ends the current delivery attempt.

It does not automatically cancel the Delivery Order.

```text
Delivery Order

        │

        ▼

Delivery Attempt

        │

        ├── Successful

        └── Failed

                │

                ▼

Next Business Decision
```

---

# 4. Failed Delivery Entity

Each Failed Delivery records:

* Delivery Order
* Trip
* Stop
* Driver
* Failure Reason
* Failure Timestamp
* Resolution Status

---

# 5. Typical Failure Reasons

Examples include:

* customer absent;
* incorrect address;
* access denied;
* customer refused receipt;
* unsafe delivery conditions;
* vehicle breakdown before delivery;
* weather conditions;
* operational interruption.

Reason codes are configurable.

---

# 6. Workflow

```text
Arrive

↓

Delivery Attempt

↓

Failure Identified

↓

Failure Registered

↓

Tracking Updated

↓

Resolution Decision
```

---

# 7. Resolution Options

Depending on company policy, a failed delivery may result in:

* new delivery attempt;
* customer contact;
* delivery rescheduling;
* return to warehouse;
* cancellation of the Delivery Order;
* escalation to customer service.

---

# 8. Inventory Integration

If no items were delivered:

* inventory ownership remains unchanged according to warehouse execution policies;
* returned goods are reconciled with WMS if they left the warehouse.

Inventory movements must remain fully auditable.

---

# 9. Customer Communication

Customers may receive:

* delivery failure notification;
* failure reason (when appropriate);
* next delivery attempt;
* customer service instructions.

---

# 10. Tracking Integration

Tracking events include:

* Delivery Attempt Started
* Delivery Failed
* Failure Reason Registered
* Resolution Initiated
* Resolution Completed

---

# 11. Delivery Balance

When no items are delivered:

```text
Ordered

100

Delivered

0

Remaining

100
```

The Delivery Balance remains unchanged until a successful delivery occurs.

---

# 12. Relationship With Exceptions

Every Failed Delivery generates at least one Delivery Exception.

The exception contains:

* operational details;
* supporting evidence;
* resolution workflow.

---

# 13. Business Rules

## Rule 1

A Failed Delivery represents one failed execution attempt.

---

## Rule 2

A Failed Delivery does not automatically cancel the Delivery Order.

---

## Rule 3

Every Failed Delivery requires a failure reason.

---

## Rule 4

Every Failed Delivery must generate a Tracking event.

---

## Rule 5

Every Failed Delivery must be fully auditable.

---

# 14. Performance Indicators

Operational KPIs include:

* failed delivery rate;
* first-attempt success rate;
* average retry count;
* failures by region;
* failures by driver;
* failures by customer;
* failures by reason.

---

# 15. Future Enhancements

Possible future capabilities:

* automatic retry scheduling;
* predictive failure analysis;
* AI delivery recommendations;
* customer availability prediction;
* weather impact analysis.

---

# 16. Final Architecture Rule

A Failed Delivery records the unsuccessful completion of a delivery attempt.

It preserves the commercial commitment while documenting the operational outcome.

```text
Delivery Order

↓

Delivery Attempt

↓

Failed Delivery

↓

Delivery Exception

↓

Resolution

↓

New Attempt (if applicable)
```

The platform distinguishes clearly between **commercial obligations** and **operational execution**, ensuring that failed attempts do not compromise the integrity of business documents.

> **Simple is always better than complex.**
obs:

Partial Delivery ≠ Failed Delivery

São processos completamente diferentes.

Partial Delivery	Failed Delivery
Parte foi entregue	Nada foi entregue
Operação bem-sucedida parcialmente	Operação não concluída
Pode continuar normalmente	Requer decisão operacional
Atualiza Delivery Balance	Mantém o Delivery Balance inalterado (ou conforme política para itens já descarregados e recolhidos)
Não é exceção	Origina uma exceção operacional

Uma regra arquitetural que eu estabeleceria é:

Uma Failed Delivery encerra a tentativa de entrega, não a obrigação de entregar.

Isso significa que:

a venda continua válida;
a Delivery Order continua válida;
o cliente continua aguardando;
apenas a tentativa falhou.
