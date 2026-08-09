# RFC-BUSINESS-RELATIONSHIP-CACHE.md

**Status:** Draft

**RFC:** 0018

**Categoria:** Business Core

**Módulo:** Business Relationship Engine (BRE)

**Prioridade:** Alta

**Versão:** 1.0

**Dependências:**

* RFC-BUSINESS-RELATIONSHIP-MODEL.md
* RFC-BUSINESS-RELATIONSHIP-API.md

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

Definir a arquitetura de cache do Business Relationship Engine (BRE).

O cache é responsável por reduzir consultas ao banco de dados, permitir funcionamento offline e garantir alta performance na resolução de relacionamentos entre entidades.

O cache não substitui o banco de dados; ele é apenas uma camada de aceleração.

---

# 2. Objetivos Funcionais

O subsistema deverá:

* reduzir latência;
* minimizar consultas repetidas;
* permitir operação offline;
* sincronizar automaticamente;
* suportar multiempresa;
* manter consistência eventual;
* invalidar dados automaticamente;
* registrar estatísticas de utilização.

---

# 3. Arquitetura

```text
                 Business API
                      │
                      ▼
          Relationship Cache Manager
              │               │
              ▼               ▼
       Memory Cache     Persistent Cache
              │               │
              └───────┬───────┘
                      ▼
             Relationship Repository
                      ▼
                 PostgreSQL
```

---

# 4. Níveis de Cache

## Nível 1 (L1)

Cache em memória.

Características:

* extremamente rápido;
* processo local;
* descartável;
* utilizado em consultas repetidas.

Tempo esperado:

```text
< 5 ms
```

---

## Nível 2 (L2)

Cache persistente.

Exemplos:

* SQLite
* IndexedDB
* RocksDB (opcional)

Permite funcionamento offline.

---

## Nível 3 (L3)

Banco oficial.

PostgreSQL.

Sempre considerado a fonte da verdade.

---

# 5. Fluxo

```text
Consulta

↓

L1

↓

Encontrou?

↓

SIM

↓

Retorna

↓

NÃO

↓

L2

↓

Encontrou?

↓

SIM

↓

Atualiza L1

↓

Retorna

↓

NÃO

↓

Banco

↓

Atualiza L2

↓

Atualiza L1

↓

Retorna
```

---

# 6. Chave de Cache

Formato padrão:

```text
<company>:<relationship_type>:<source>:<target>
```

Exemplo:

```text
001:DEFAULT:NCM:84181000
```

---

# 7. Objetos Cacheáveis

Relacionamentos ativos.

Exemplo:

```text
NCM

↓

CEST
```

---

Fornecedor Preferencial.

```text
Produto

↓

Fornecedor
```

---

Cliente

↓

Tabela de Preço

---

Empresa

↓

Filiais

---

# 8. Objetos Não Cacheáveis

Não armazenar:

* relacionamentos expirados;
* registros pendentes;
* registros cancelados;
* versões antigas.

---

# 9. TTL

Tempo padrão:

```text
15 minutos
```

Configurável.

Algumas tabelas poderão utilizar TTL maior.

Exemplo:

NCM

```text
24 horas
```

---

CEST

```text
24 horas
```

---

Municípios

```text
7 dias
```

---

# 10. Invalidação

A invalidação ocorre quando:

* relacionamento criado;
* relacionamento alterado;
* relacionamento encerrado;
* sincronização oficial;
* troca de empresa;
* troca de filial.

---

# 11. Atualização

Sempre utilizar estratégia:

```text
Write Through
```

Fluxo:

```text
Atualizar Banco

↓

Atualizar Cache

↓

Publicar Evento
```

---

# 12. Eventos

```text
RelationshipCached

RelationshipExpired

RelationshipInvalidated

RelationshipLoaded

RelationshipCacheMiss

RelationshipCacheHit
```

---

# 13. Estatísticas

Registrar:

* Cache Hit
* Cache Miss
* Tempo médio
* Tempo máximo
* TTL restante
* Objetos armazenados
* Objetos expirados

---

# 14. Compressão

Objetos grandes poderão ser comprimidos.

Estratégias permitidas:

* LZ4
* Zstandard

A escolha depende do ambiente de execução.

---

# 15. Multiempresa

Cada empresa possui cache independente.

Nunca compartilhar:

```text
Empresa A

↓

Fornecedor
```

com

```text
Empresa B
```

---

# 16. Sincronização

Durante sincronização.

```text
Servidor

↓

Novos relacionamentos

↓

Persistent Cache

↓

Memory Cache
```

---

# 17. Offline

Quando o banco estiver indisponível.

Fluxo:

```text
Consulta

↓

L1

↓

L2

↓

Resposta
```

Caso não exista.

```text
Sem resultado
```

---

# 18. Política de Evicção

L1

Utilizar:

```text
LRU
```

(Less Recently Used)

---

L2

Utilizar:

```text
TTL + LRU
```

---

# 19. Pré-carregamento

Durante login.

Carregar:

* empresa ativa;
* filial ativa;
* relacionamentos fiscais;
* fornecedores preferenciais;
* categorias;
* tabelas oficiais.

---

# 20. Consultas Frequentes

Devem permanecer em memória.

Exemplos:

* Produto → Categoria
* Produto → Marca
* Produto → NCM
* NCM → CEST
* Produto → Fornecedor Preferencial

---

# 21. Segurança

Nunca armazenar em cache:

* credenciais;
* tokens;
* senhas;
* chaves privadas;
* certificados.

---

# 22. Consistência

O cache utiliza:

```text
Eventual Consistency
```

O banco de dados permanece como fonte oficial.

---

# 23. API

```text
get()

put()

remove()

invalidate()

invalidateByCompany()

invalidateByEntity()

invalidateByRelationship()

clear()

warmup()

statistics()
```

---

# 24. Warmup

Na inicialização.

```text
Servidor

↓

Relacionamentos mais usados

↓

L2

↓

L1
```

---

# 25. Monitoramento

Métricas obrigatórias.

* Hit Rate
* Miss Rate
* Tempo médio
* Tempo máximo
* Número de invalidações
* Objetos em memória
* Objetos persistidos

---

# 26. Recuperação

Após reinicialização.

Fluxo:

```text
Persistent Cache

↓

Memory Cache

↓

Sistema pronto
```

---

# 27. Performance

Metas.

Consulta L1:

```text
< 5 ms
```

Consulta L2:

```text
< 20 ms
```

Banco:

```text
< 100 ms
```

Warmup inicial:

```text
< 3 segundos
```

---

# 28. Integração

Consumidores:

* Lookup Engine
* AutoFill Engine
* Fiscal Engine
* Workflow Engine
* Document Engine
* POS
* Compras
* Vendas
* Estoque

Todos utilizam a mesma camada de cache.

---

# 29. Roadmap

## Sprint CACHE-01

* Memory Cache (L1)
* API básica
* Estatísticas

## Sprint CACHE-02

* Persistent Cache (L2)
* TTL
* LRU
* Invalidação

## Sprint CACHE-03

* Warmup
* Operação offline
* Eventos

## Sprint CACHE-04

* Compressão
* Monitoramento
* Ajustes automáticos de desempenho

---

# 30. Considerações Arquiteturais

O subsistema de cache pertence ao **Business Relationship Engine**, mas sua implementação deve ser genérica o suficiente para ser reutilizada por outros componentes do Business Core.

A implementação deve respeitar os princípios de:

* desacoplamento;
* independência do banco de dados;
* suporte a múltiplos provedores de cache;
* operação offline;
* observabilidade completa.

O Cache Manager não possui regras de negócio. Sua única responsabilidade é fornecer acesso rápido e consistente aos relacionamentos utilizados pelo BRE.
