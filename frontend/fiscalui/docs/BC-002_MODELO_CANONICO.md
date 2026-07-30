# Business Platform
# BC-002 — Modelo Canônico Empresarial

**Documento:** BC-002
**Título:** Modelo Canônico Empresarial (Canonical Enterprise Model)
**Versão:** 1.0.0 (Draft)
**Dependências:** BC-000 (Manifesto), BC-001 (Ontologia)

---

## Capítulo 1 — Objetivo

O Modelo Canônico estabelece uma representação única para todos os objetos de negócio da plataforma.

Ele não define:

- banco de dados;
- tabelas;
- classes;
- APIs;
- telas.

Ele define apenas o modelo conceitual compartilhado.

---

## Capítulo 2 — O que é um Modelo Canônico?

É a representação oficial utilizada por todos os motores.

```
Cliente

BusinessCore  FiscalCore  AccountingCore  WorkflowCore  CRM  BI
    │             │             │               │        │    │
    └─────────────┴─────────────┴───────────────┴────────┴────┘

Todos utilizam exatamente o mesmo conceito.
```

Isso elimina conversões entre módulos.

---

## Capítulo 3 — Princípios

### 3.1 Identidade

Todo objeto possui identidade única. `EntityID`. Essa identidade nunca muda.

### 3.2 Nome

Todo objeto possui uma identificação humana. Exemplo: `Produto` → "Notebook Dell Latitude".

### 3.3 Estado

Todo objeto possui um estado: Ativo, Inativo, Bloqueado, Arquivado, Cancelado.

### 3.4 Ciclo de Vida

Todo objeto nasce. Evolui. Pode ser encerrado. Nunca desaparece do histórico.

---

## Capítulo 4 — Estrutura Universal

Todo objeto empresarial herda esta estrutura.

```
BusinessObject
├── ID
├── Code
├── Name
├── Description
├── Status
├── Version
├── CreatedAt
├── UpdatedAt
├── CreatedBy
├── UpdatedBy
├── Tags
├── Metadata
└── Extensions
```

Essa será a "classe abstrata" conceitual do BusinessCore.

---

## Capítulo 5 — Identidade Canônica

A identidade é global.

```
EntityID → UUID → Imutável
```

Nunca será reutilizada.

---

## Capítulo 6 — Código

O código é diferente do identificador.

```
ID:     550e8400-e29b-...
Código: CLI-000012
```

O código pode mudar conforme a regra da empresa. O ID nunca muda.

---

## Capítulo 7 — Versionamento

Todo objeto possui versão.

```
1 → 2 → 3 → 4
```

Isso permitirá auditoria e evolução.

---

## Capítulo 8 — Metadados

Todo objeto suporta metadados.

```
Metadata → Origem (Importado, API, Manual, Sistema Externo, Integração)
```

Os metadados não alteram o significado do objeto.

---

## Capítulo 9 — Extensões

Nenhuma empresa é igual.

```
Extensions → Campos personalizados → Plugins → Verticalizações → Customizações
```

Sem alterar o modelo canônico.

---

## Capítulo 10 — Hierarquia

Todo objeto pertence a um domínio.

```
BusinessObject
│
├── Party
├── Resource
├── Process
├── Document
├── Event
└── Transaction
```

---

## Capítulo 11 — Entidades Canônicas

O BusinessCore reconhecerá inicialmente estas entidades.

```
Party

Organization
Company
Branch
Department
Employee
Customer
Supplier
Product
Service
Asset
Warehouse
Location
Project
Contract
Document
Order
Invoice
Payment
Receipt
Transaction
Event
```

> Observe que `Invoice` aqui significa um conceito de documento comercial. A especialização para NF-e, NFS-e ou outros documentos fiscais será responsabilidade do FiscalCore.

---

## Capítulo 12 — Objetos de Valor (Value Objects)

Existem objetos que não possuem identidade própria.

```
Endereço
Telefone
Email
Moeda
Quantidade
Percentual
Dimensão
Peso
Volume
Coordenada
Período
```

Eles pertencem a uma entidade. Nunca existem sozinhos.

---

## Capítulo 13 — Agregados

Algumas entidades controlam outras.

```
Pedido
├── Itens
├── Descontos
├── Observações
└── Anexos
```

O `Pedido` é a raiz do agregado.

---

## Capítulo 14 — Relacionamentos

Os relacionamentos são explícitos.

```
Cliente → realiza → Pedido → gera → Venda → origina → Documento → gera → Evento
```

Nenhum relacionamento oculto é permitido.

---

## Capítulo 15 — Regras Gerais

Todo objeto deve:

- possuir identidade;
- possuir estado;
- possuir histórico;
- permitir auditoria;
- suportar extensões;
- respeitar a ontologia definida no BC-001.

---

## Capítulo 16 — Governança do Modelo

O Modelo Canônico é controlado pelo BusinessCore. Nenhum outro motor poderá alterá-lo diretamente. Especializações são permitidas. Alterações estruturais exigem nova versão do modelo.

---

## Capítulo 17 — Exemplo de Especialização

```
BusinessObject
        │
        ▼
     Product
        │
        ├───────────────┐
        ▼               ▼
FiscalProduct     AccountingProduct
        │               │
  NCM, CFOP      Conta Contábil
  CEST, CST      Centro de Custos
```

O `Product` continua sendo uma entidade única no BusinessCore. Cada motor adiciona apenas os atributos de sua responsabilidade.

---

## Capítulo 18 — Benefícios

O Modelo Canônico oferece:

- Linguagem comum entre todos os motores
- Integrações simplificadas
- Redução de duplicidade de conceitos
- Evolução independente de cada motor
- Melhor interoperabilidade com APIs e sistemas externos
- Base consistente para BI, IA e integrações futuras

---

## Roadmap do BusinessCore

Após o BC-002, entraremos em modelagem mais detalhada:

```
BC-003 — Entidades Fundamentais
BC-004 — Value Objects
BC-005 — Agregados
BC-006 — Eventos de Negócio
BC-007 — Casos de Uso
BC-008 — Serviços de Domínio
BC-009 — Políticas
BC-010 — Máquina de Estados
```

---

**Arquivo:** `docs/BC-002_MODELO_CANONICO.md`
**Versão:** 1.0.0
**Data:** 2026-07-25
