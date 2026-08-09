# RFC-BUSINESS-RELATIONSHIP-API.md

**Status:** Draft

**RFC:** 0016

**Categoria:** Business Core

**Módulo:** Business Relationship Engine (BRE)

**Prioridade:** Arquitetura Base

**Versão:** 1.0

**Dependências:**

* RFC-BUSINESS-RELATIONSHIP-MODEL.md
* RFC-EVENT-ENGINE.md (futura)
* RFC-CACHE-ENGINE.md (futura)

---

## Platform Philosophy

> **Simple is always better than complex.**
> Simples é sempre melhor do que complexo.

Design systems that are easy to understand, easy to maintain, easy to extend, and easy to use.
Avoid unnecessary abstractions. Prefer explicit behavior over hidden magic.
Every feature should solve a real business problem.
Performance and maintainability always come first.

---

# 1. Objetivo

Definir a API pública do Business Relationship Engine (BRE).

A API é a única forma suportada para criação, consulta, alteração, encerramento e navegação de relacionamentos entre entidades do ERP.

Nenhum módulo deverá acessar diretamente as tabelas do BRE.

---

# 2. Princípios

A API segue os princípios:

* baixo acoplamento;
* independência da persistência;
* orientada a serviços;
* orientada a eventos;
* compatível com cache;
* preparada para operação offline;
* preparada para versionamento.

---

# 3. Arquitetura

```text
                Produto

                  │

                  ▼

           Purchase Module

                  │

                  ▼

            Sales Module

                  │

                  ▼

       Business Relationship API

                  │

      ┌───────────┼───────────┐

      ▼           ▼           ▼

 Repository   Cache Engine   Event Engine
```

---

# 4. Conceitos

A API trabalha apenas com:

* entidades;
* relacionamentos;
* filtros;
* consultas;
* eventos.

Ela não conhece:

* tabelas SQL;
* ORM;
* PostgreSQL;
* COBOL;
* Python.

---

# 5. Interface Principal

```text
RelationshipService
```

Responsável por toda interação com o BRE.

---

# 6. Operações de Escrita

## create()

Cria um relacionamento.

Entrada

```text
source

target

relationshipType

validFrom

validTo

priority

metadata
```

Retorno

```text
RelationshipId
```

---

## close()

Encerra um relacionamento.

Nunca remove registros.

---

## replace()

Substitui um relacionamento.

Fluxo

```text
Versão Atual

↓

Encerrar

↓

Nova Versão
```

---

## suspend()

Suspende temporariamente.

---

## activate()

Reativa.

---

# 7. Operações de Consulta

## findById()

Busca por identificador.

---

## findTargets()

Retorna todos os destinos.

Exemplo

```text
Produto

↓

Fornecedor A

Fornecedor B

Fornecedor C
```

---

## findSources()

Consulta inversa.

Exemplo

```text
Fornecedor

↓

Produto A

Produto B

Produto C
```

---

## findRelationships()

Consulta completa.

Aceita filtros.

---

## exists()

Retorna verdadeiro ou falso.

---

## count()

Quantidade de relacionamentos.

---

# 8. Operações Inteligentes

## resolve()

Obtém automaticamente o relacionamento válido.

Considera:

* vigência;
* prioridade;
* empresa;
* filial;
* status.

Exemplo

```text
Produto

↓

Fornecedor Preferencial
```

---

## resolveAll()

Retorna todos.

---

## resolveDefault()

Retorna apenas o padrão.

---

## resolveHistory()

Retorna histórico completo.

---

# 9. Navegação

## traverse()

Permite percorrer grafos.

Exemplo

```text
Produto

↓

Categoria

↓

Departamento

↓

Empresa
```

---

## shortestPath()

Calcula menor caminho.

---

## descendants()

Todos os descendentes.

---

## ancestors()

Todos os ancestrais.

---

# 10. Versionamento

## history()

Histórico.

---

## current()

Versão atual.

---

## previous()

Versão anterior.

---

## next()

Próxima versão.

---

# 11. Validação

## validate()

Executa todas as validações.

Inclui

* vigência;
* duplicidade;
* consistência;
* regras obrigatórias.

---

## canCreate()

Verifica antes da criação.

---

## canReplace()

Verifica antes da substituição.

---

# 12. Eventos

Toda operação publica eventos.

```text
RelationshipCreated

RelationshipUpdated

RelationshipClosed

RelationshipActivated

RelationshipSuspended

RelationshipResolved

RelationshipValidated
```

---

# 13. Filtros

Suportados.

Empresa

Filial

Status

Tipo

Prioridade

Data

Origem

Destino

Versão

---

# 14. Ordenação

Suportar.

Prioridade

Descrição

Código

Data

Versão

---

# 15. Paginação

Obrigatória.

```text
page

pageSize

total

hasNext
```

---

# 16. Consulta por Data

Exemplo

```text
Relacionamentos válidos

em

01/01/2028
```

---

# 17. Multiempresa

Todas as consultas respeitam.

```text
company_id
```

---

# 18. Multi-filial

Filtros opcionais.

```text
branch_id
```

---

# 19. Cache

A API nunca acessa cache diretamente.

Fluxo.

```text
API

↓

Cache Engine

↓

Repository
```

---

# 20. Persistência

A API desconhece.

* PostgreSQL
* SQLite
* IndexedDB
* COBOL

Toda persistência é abstraída pelo Repository.

---

# 21. Repository

Interface mínima.

```text
save()

load()

update()

close()

search()

history()
```

---

# 22. Exemplo

Produto

↓

Fornecedor Preferencial

```text
resolve(
 source=Produto,
 relationshipType=SUPPLIES
)
```

Resultado

```text
Fornecedor XYZ
```

---

# 23. Outro Exemplo

NCM

↓

CEST

```text
resolve(
 source=NCM,
 relationshipType=DEFAULT
)
```

Retorno.

```text
21.001.00
```

---

# 24. Exceções

A API deverá lançar exceções padronizadas.

```text
RelationshipNotFound

RelationshipExpired

RelationshipInvalid

RelationshipDuplicated

RelationshipConflict

RelationshipCycleDetected

RelationshipPermissionDenied
```

---

# 25. Performance

Objetivos.

Consulta simples

< 20 ms

Consulta cache

< 5 ms

Criação

< 50 ms

---

# 26. Observabilidade

Registrar.

* tempo;
* origem;
* usuário;
* empresa;
* operação;
* cache hit;
* cache miss.

---

# 27. Segurança

Toda operação verifica.

* autenticação;
* autorização;
* empresa;
* filial;
* permissões.

---

# 28. Compatibilidade

A API deve ser independente da linguagem.

Implementações previstas.

* Python
* COBOL
* REST
* gRPC
* CLI

Todas compartilham o mesmo contrato.

---

# 29. Casos de Uso

## Produto

Resolver categoria.

Resolver marca.

Resolver fornecedor.

Resolver NCM.

---

## Fiscal

Resolver CEST.

Resolver ANP.

Resolver EX TIPI.

Resolver benefício fiscal.

---

## Compras

Resolver fornecedor prioritário.

Resolver prazo.

Resolver contrato.

---

## Vendas

Resolver tabela de preços.

Resolver comissão.

Resolver canal.

---

# 30. Roadmap

## Sprint API-01

* Interface RelationshipService.
* CRUD lógico.
* Consultas básicas.

## Sprint API-02

* Resolve.
* Versionamento.
* Eventos.

## Sprint API-03

* Navegação em grafos.
* Histórico.
* Paginação.

## Sprint API-04

* Integração com Cache Engine.
* Integração com Event Engine.
* Suporte offline.

---

# 31. Evolução Arquitetural

Esta API foi projetada para representar **relacionamentos estruturais**, mas sua arquitetura também permite consultas de grafo.

No futuro, o BRE poderá oferecer funcionalidades como:

* impacto de alterações (Impact Analysis);
* visualização de dependências entre entidades;
* detecção de ciclos;
* análise de hierarquias;
* exploração de relacionamentos por múltiplos níveis.

Esses recursos deverão ser implementados sem alterar o contrato da API definido nesta RFC, preservando compatibilidade com todos os módulos consumidores.
