# RFC-LOOKUP-AUTOCOMPLETE-ENGINE.md

**Status:** Draft

**RFC:** 0012

**Categoria:** UI Framework / Business Core

**Prioridade:** Alta

**Autor:** Arquitetura ERP

**Versão:** 1.0

---

# 1. Objetivo

Definir uma arquitetura padronizada para componentes de pesquisa (Lookup) com **AutoComplete**, **AutoFill**, **Validação**, **Cache**, **Busca Inteligente** e **Relacionamentos entre tabelas**, reutilizável em todo o ERP.

O objetivo é eliminar campos de texto livres para dados estruturados, reduzindo erros de digitação e centralizando regras de negócio.

Esta RFC define um **motor genérico**, independente do domínio de negócio.

---

# 2. Motivação

O ERP possuirá centenas de cadastros contendo campos que representam entidades existentes.

Exemplos:

* NCM
* CEST
* CFOP
* CST ICMS
* CST PIS
* CST COFINS
* CST IPI
* CNAE
* Município IBGE
* País
* Estado
* Cidade
* Banco
* Agência
* Transportadora
* Cliente
* Fornecedor
* Produto
* Centro de Distribuição
* Natureza de Operação

Permitir digitação manual gera:

* inconsistência
* duplicidade
* erros fiscais
* problemas de integração
* baixa produtividade

---

# 3. Objetivos da Arquitetura

O componente deverá:

✔ pesquisa incremental

✔ autocomplete

✔ pesquisa por código

✔ pesquisa por descrição

✔ pesquisa parcial

✔ teclado

✔ mouse

✔ touch

✔ cache local

✔ funcionamento offline

✔ preenchimento automático

✔ validação automática

✔ componente reutilizável

---

# 4. Arquitetura

```
┌───────────────────────────────┐
│         Tela                  │
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│ Lookup Component              │
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│ Lookup Service                │
└──────────────┬────────────────┘
               │
        ┌──────┴────────┐
        ▼               ▼
Cache Local      Banco de Dados
        │
        ▼
Relacionamentos
        │
        ▼
AutoFill Engine
```

---

# 5. Componentes

## 5.1 Lookup Component

Responsável pela interface.

Funções:

* captura teclado
* autocomplete
* exibe lista
* navegação
* seleção

---

## 5.2 Lookup Service

Responsável pela pesquisa.

Funções:

* consultar banco
* consultar cache
* paginação
* filtros
* ordenação

---

## 5.3 AutoFill Engine

Após seleção do registro:

* preencher outros campos
* disparar eventos
* validar regras

---

## 5.4 Validation Engine

Valida:

* obrigatoriedade
* vigência
* relacionamento
* empresa
* permissões

---

## 5.5 Cache Manager

Mantém:

* tabelas fiscais
* catálogos
* consultas recentes

---

# 6. Interface do Componente

```
┌──────────────────────────────────────────────┐
│ 🔍 Digite código ou descrição...             │
└──────────────────────────────────────────────┘
```

Pesquisa por:

* código
* descrição
* palavras
* código parcial

---

# 7. Fluxo de Pesquisa

```
Usuário digita

↓

300 ms debounce

↓

Consulta Cache

↓

Encontrou?

↓

SIM → retorna

↓

NÃO

↓

Consulta Banco

↓

Atualiza Cache

↓

Mostra resultados
```

---

# 8. Pesquisa Inteligente

Aceita:

```
8418

geladeira

refrigerador

841810

freezer
```

Todos retornam resultados compatíveis.

---

# 9. Ordenação

Prioridade:

1 Código exato

2 Código parcial

3 Início da descrição

4 Palavra inteira

5 Texto semelhante

---

# 10. Debounce

Tempo padrão

```
300 ms
```

Configurável.

---

# 11. Navegação

Suporte completo:

↑

↓

PgUp

PgDn

Home

End

Enter

ESC

TAB

Shift+TAB

Mouse

Touch

---

# 12. Resultado

```
84181000
Refrigeradores domésticos

----------------------

84182100
Refrigeradores combinados

----------------------

84182900
Outros refrigeradores
```

---

# 13. API do Lookup

Interface genérica:

```
LookupProvider

search(text)

get(id)

validate(id)

autocomplete(text)

fill(id)
```

---

# 14. Eventos

```
onSearch

onSelect

onFill

onValidate

onClear

onError

onCancel
```

---

# 15. AutoFill

O componente pode preencher outros campos automaticamente.

Exemplo:

```
Selecionou Cliente

↓

Preenche

telefone

email

cidade

UF

condição pagamento
```

---

Outro exemplo:

```
Selecionou Produto

↓

Preenche

unidade

preço

NCM

CFOP

tributação
```

---

# 16. Relacionamentos

O Lookup suporta relacionamentos.

Exemplo:

```
Produto

↓

Categoria

↓

Departamento

↓

Empresa
```

---

# 17. Exemplo NCM → CEST

```
Seleciona NCM

↓

Lookup Service

↓

Consulta relacionamento

↓

Encontrou CEST?

↓

SIM

↓

AutoFill

↓

Campo preenchido
```

---

# 18. Quando existir apenas um relacionamento

```
NCM

↓

1 CEST

↓

Preenche automaticamente
```

Sem interação do usuário.

---

# 19. Quando existir múltiplos relacionamentos

```
NCM

↓

4 CEST

↓

Abrir diálogo
```

```
Escolha o CEST

( ) 21.001.00

( ) 21.002.00

( ) 21.005.00

( ) Não possui ST
```

---

# 20. Quando não existir relacionamento

```
NCM

↓

Nenhum CEST

↓

Campo vazio

↓

Registrar informação
```

---

# 21. Modelo de Dados

## Tabela NCM

```
id

codigo

descricao

vigencia_inicio

vigencia_fim

ativo
```

---

## Tabela CEST

```
id

codigo

descricao

segmento

ativo
```

---

## Relacionamento

```
ncm_cest

id

ncm_id

cest_id

descricao_aplicacao

st_obrigatorio

vigencia_inicio

vigencia_fim
```

Relacionamento:

```
NCM 1

↓

N

↓

NCM_CEST

↓

N

↓

1

CEST
```

---

# 22. Regras de AutoFill

## Regra 1

Um relacionamento

→ preencher automaticamente.

---

## Regra 2

Mais de um

→ solicitar escolha.

---

## Regra 3

Nenhum

→ manter vazio.

---

## Regra 4

Relacionamento expirado

→ ignorar.

---

## Regra 5

Relacionamento futuro

→ ignorar.

---

# 23. Cache

Cache de:

* NCM
* CEST
* CFOP
* CST
* Municípios

Atualização:

* sincronização
* importação
* inicialização

---

# 24. Performance

Objetivos:

Pesquisa:

< 100 ms

AutoFill:

< 50 ms

Cache Hit:

< 10 ms

---

# 25. Segurança

Validar:

empresa

filial

vigência

permissões

registro ativo

---

# 26. Extensibilidade

Novos providers:

```
ProductLookup

PartnerLookup

SupplierLookup

BankLookup

IBGELookup

CFOPLookup

NCMLookup

CESTLookup

CountryLookup

CurrencyLookup
```

Sem alterar o componente.

---

# 27. Casos de Uso

## Produto

Seleciona NCM.

Sistema completa CEST.

---

## Cliente

Seleciona CEP.

Sistema completa:

cidade

bairro

UF

IBGE

---

## Compras

Seleciona fornecedor.

Sistema completa:

prazo

último preço

condição

---

## Financeiro

Seleciona banco.

Sistema completa:

código

agência

carteira

---

# 28. Benefícios

* Redução de erros de digitação.
* Padronização da interface.
* Melhor experiência do usuário.
* Maior produtividade.
* Menor custo de manutenção.
* Reutilização em todo o ERP.
* Regras de negócio centralizadas.
* Suporte nativo a relacionamentos entre entidades.
* Preparação para operação offline com cache.

---

# 29. Integração com o Framework

Este componente passa a fazer parte do **BusinessUI Framework** como um componente base.

Todos os módulos do ERP devem utilizá-lo em substituição a campos de texto para referências a entidades cadastradas.

Componentes derivados:

* LookupNCM
* LookupCEST
* LookupCFOP
* LookupCST
* LookupProduto
* LookupCliente
* LookupFornecedor
* LookupBanco
* LookupMunicípio
* LookupTransportadora

Todos compartilham o mesmo motor, alterando apenas o provedor de dados (Lookup Provider).

---

# 30. Roadmap

### Fase 1

* Motor genérico de Lookup.
* Pesquisa incremental.
* AutoComplete.
* Cache em memória.

### Fase 2

* AutoFill Engine.
* Eventos.
* Validação.

### Fase 3

* Cache persistente (IndexedDB/SQLite).
* Funcionamento offline.
* Sincronização automática.

### Fase 4

* Pesquisa fuzzy.
* Ranking por relevância.
* Histórico de seleção.
* Favoritos.
* Inteligência baseada em contexto.

---

# Anexo A — Implementação NCM → CEST

O relacionamento entre NCM e CEST **não é 1:1**. Um NCM pode estar associado a nenhum, um ou vários CEST, dependendo da aplicação da mercadoria e da legislação vigente.

Por isso, a implementação deve utilizar uma tabela de relacionamento (`ncm_cest`) com vigência e regras de aplicação, evitando gravar códigos diretamente na tabela de produtos.

Fluxo recomendado:

1. Usuário seleciona um NCM pelo componente Lookup.
2. O sistema consulta a tabela `ncm_cest`.
3. Se existir apenas um CEST válido, ele é preenchido automaticamente.
4. Se existirem vários CEST válidos, é apresentada uma lista para escolha.
5. Se não existir relacionamento válido, o campo permanece vazio e o usuário pode prosseguir conforme as regras fiscais configuradas.

Essa abordagem garante aderência às mudanças da legislação e evita inconsistências no cadastro de produtos.
