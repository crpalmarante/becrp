# Platform Philosophy — Filosofia da Plataforma

**Simple is always better than complex.**

**Simples é sempre melhor do que complexo.**

Este é o lema da plataforma. Ele é parte da identidade do projeto e deve estar presente em todas as RFCs e na documentação oficial.

This is the platform motto. It is part of the project identity and must appear in every RFC and in the official documentation.

---

## Declaração / Statement

Projete sistemas que sejam fáceis de entender,
fáceis de manter,
fáceis de estender
e fáceis de usar.

Design systems that are easy to understand,
easy to maintain,
easy to extend,
and easy to use.

Evite abstrações desnecessárias.
Prefira comportamento explícito a magia oculta.
Toda funcionalidade deve resolver um problema real de negócio.
Desempenho e manutenibilidade sempre em primeiro lugar.

Avoid unnecessary abstractions.
Prefer explicit behavior over hidden magic.
Every feature should solve a real business problem.
Performance and maintainability always come first.

---

## Princípios / Principles

1. **Simplicidade** — a solução mais simples que resolve o problema real é a correta. *The simplest solution that solves the real problem is the right one.*
2. **Explicitude** — comportamento explícito sempre vence magia oculta. *Explicit behavior always beats hidden magic.*
3. **Custo de manutenção** — código fácil de entender é mais barato de manter. *Code that is easy to understand is cheaper to maintain.*
4. **Problema real** — toda funcionalidade resolve um problema concreto de negócio. *Every feature solves a concrete business problem.*
5. **Desempenho e manutenibilidade** — vêm sempre em primeiro lugar. *Performance and maintainability always come first.*

---

## Uso obrigatório / Mandatory usage

Todo RFC e documento oficial deve conter o bloco de filosofia abaixo no topo, logo após o cabeçalho e os metadados do documento.

Every RFC and official document must contain the standard philosophy block below at the top, right after the document header and metadata.

### Bloco padrão / Standard block

```markdown
---

## Platform Philosophy

> **Simple is always better than complex.**
> Simples é sempre melhor do que complexo.

Design systems that are easy to understand, easy to maintain, easy to extend, and easy to use.
Avoid unnecessary abstractions. Prefer explicit behavior over hidden magic.
Every feature should solve a real business problem.
Performance and maintainability always come first.

---
```

---

## Adequação à arquitetura / Fit with the architecture

O lema combina com a arquitetura da plataforma:

The motto fits the platform architecture:

- **Frontend:** HTML / CSS / JavaScript (vanilla) — componentes modulares, sem abstrações desnecessárias.
- **Backend:** Python — APIs claras e regras de negócio explícitas.
- **Core legado:** COBOL — regras de negócio consolidadas, comportamento previsível.
- **Persistência:** PostgreSQL — modelo de dados direto e compreensível.

Simple is always better than complex.
Simples é sempre melhor do que complexo.
