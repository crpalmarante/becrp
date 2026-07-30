# Business Platform
# BC-003A — Catálogo Universal de Papéis (Role Model)

**Documento:** BC-003A
**Título:** Catálogo Universal de Papéis
**Versão:** 1.0.0 (Draft)
**Dependências:** BC-003 (Entidades), BC-001 (Ontologia)

---

## Capítulo 1 — Objetivo

Definir o modelo de papéis da plataforma. Uma `Party` não é cliente ou fornecedor por natureza — ela **desempenha papéis**. Este documento estabelece quais papéis existem, como se relacionam e como especializam o comportamento da `Party` sem duplicar sua identidade.

---

## Capítulo 2 — Princípio Fundamental

**Uma Party. Múltiplos papéis. Identidade única.**

```
Party (João Silva — CPF 123.456.789-00)
  │
  ├── CustomerRole       (cliente desde 2020)
  ├── SupplierRole       (fornecedor desde 2023)
  └── EmployeeRole       (funcionário desde 2018)
```

João Silva é uma única Party. Os papéis que ele desempenha mudam com o tempo. Sua identidade permanece.

---

## Capítulo 3 — Estrutura de um Papel

Todo papel herda:

```
Role
├── RoleId
├── PartyId (referência à Party)
├── Type (tipo do papel)
├── Status (ativo, inativo, suspenso)
├── EffectiveDate (início da vigência)
├── ExpirationDate (fim da vigência)
├── CreatedAt
├── UpdatedAt
└── Metadata
```

Um papel tem **vigência**. Uma Party pode assumir um papel hoje, perdê-lo amanhã e retomá-lo depois. O histórico de papéis é preservado.

---

## Capítulo 4 — Papéis do BusinessCore

### 4.1 CustomerRole

**Definição:** Papel de Party que adquire produtos ou serviços da organização.

**Atributos:**
- CreditLimit (limite de crédito)
- PaymentTerms (condições de pagamento)
- PriceList (tabela de preços)
- SalesChannel (canal de vendas)

**Especializações (fora do BusinessCore):**
- FiscalCore → CustomerFiscalData (regime, IE, contribuinte ICMS)
- AccountingCore → CustomerAccountData (conta contábil padrão)

### 4.2 SupplierRole

**Definição:** Papel de Party que fornece produtos ou serviços para a organização.

**Atributos:**
- PaymentTerms (condições de pagamento)
- LeadTime (prazo de entrega)
- MinimumOrder (pedido mínimo)
- QualityRating (classificação de qualidade)

### 4.3 EmployeeRole

**Definição:** Papel de Party que mantém vínculo trabalhista com a organização.

**Atributos:**
- HireDate (data de admissão)
- Department (departamento)
- JobTitle (cargo)
- WorkSchedule (jornada de trabalho)

### 4.4 CarrierRole

**Definição:** Papel de Party que realiza transporte de mercadorias.

**Atributos:**
- FleetSize (tamanho da frota)
- CoverageAreas (regiões de atendimento)
- CarrierType (rodoviário, aéreo, marítimo)

### 4.5 SalesRepRole

**Definição:** Papel de Party que atua como representante comercial.

**Atributos:**
- CommissionRate (taxa de comissão)
- Territory (território de atuação)
- Superviser (supervisor)

### 4.6 AccountantRole

**Definição:** Papel de Party que presta serviços contábeis.

**Atributos:**
- CRCNumber (registro profissional)
- ServiceType (tipos de serviço contábil)

### 4.7 ContactRole

**Definição:** Papel de Party que atua como ponto de contato de outra Party.

**Atributos:**
- ContactType (comercial, financeiro, técnico)
- IsPrimary (contato principal)
- Department (departamento)

### 4.8 PartnerRole

**Definição:** Papel de Party que mantém relação de parceria comercial.

**Atributos:**
- PartnershipType (joint venture, distribuidor, revendedor)
- RevenueShare (participação em resultados)
- AgreementNumber (número do acordo)

### 4.9 ManufacturerRole

**Definição:** Papel de Party que fabrica produtos.

**Atributos:**
- ManufacturingCapacity (capacidade produtiva)
- Certifications (certificações)
- Plants (unidades fabris)

### 4.10 TaxpayerRole

**Definição:** Papel de Party sujeita a obrigações tributárias.

> **Este papel pertence ao FiscalCore**, não ao BusinessCore. Sua definição aqui é apenas conceitual para demonstrar a cadeia de especialização.

**Atributos (FiscalCore):**
- TaxRegime (regime tributário)
- StateTaxId (IE)
- CityTaxId (IM)
- Suframa

---

## Capítulo 5 — Papéis Compostos

Uma Party pode acumular múltiplos papéis simultaneamente. Exemplos reais:

| Party | Papéis | Cenário |
|-------|--------|---------|
| Fornecedor A | SupplierRole + CarrierRole | Fornece e entrega |
| Cliente B | CustomerRole + SupplierRole | Compra e vende para a empresa |
| Contador C | AccountantRole + EmployeeRole | Funcionário que presta serviços contábeis |
| Transportadora D | CarrierRole + CustomerRole | Usa serviços da empresa |

---

## Capítulo 6 — Ciclo de Vida de um Papel

```
Atribuído → Ativo → Suspenso → Cancelado
                      ↓
                  Reativado
```

Cada transição de estado gera um Evento.

---

## Capítulo 7 — Papéis vs. Especializações

É importante distinguir:

- **Papel (Role):** comportamento que uma Party assume em uma relação de negócio. Ex: CustomerRole.
- **Especialização (Fiscal/Accounting):** atributos técnicos adicionados por outros motores. Ex: FiscalCustomerData.

```
Party
  │
  ├── CustomerRole (BusinessCore — papel de negócio)
  │     └── FiscalCustomerData (FiscalCore — dados fiscais do cliente)
  │     └── AccountingCustomerData (AccountingCore — dados contábeis)
  │
  ├── SupplierRole (BusinessCore — papel de negócio)
  │     └── FiscalSupplierData (FiscalCore — dados fiscais do fornecedor)
  │
  └── EmployeeRole (BusinessCore — papel de negócio)
        └── HRData (RH Core — dados trabalhistas)
```

O papel é do BusinessCore. A especialização é do motor responsável.

---

## Capítulo 8 — Benefícios do Modelo de Papéis

1. **Identidade única** — Uma Party, um cadastro, múltiplos papéis
2. **Histórico completo** — Papéis passados são preservados mesmo após cancelamento
3. **Transição natural** — Fornecedor vira cliente sem recadastro
4. **Extensibilidade** — Novos papéis são adicionados sem alterar a Party
5. **Especialização limpa** — Cada motor adiciona dados apenas nos papéis que lhe concernem

---

## Capítulo 9 — Catálogo de Papéis (v1.0)

| Papel | Domínio | Motor |
|-------|---------|-------|
| CustomerRole | Comercial | BusinessCore |
| SupplierRole | Compras | BusinessCore |
| EmployeeRole | RH | BusinessCore |
| CarrierRole | Logística | BusinessCore |
| SalesRepRole | Comercial | BusinessCore |
| AccountantRole | Financeiro | BusinessCore |
| ContactRole | Cadastro | BusinessCore |
| PartnerRole | Parcerias | BusinessCore |
| ManufacturerRole | Produção | BusinessCore |
| TaxpayerRole | Fiscal | FiscalCore |
| DebtorRole | Financeiro | AccountingCore |
| CreditorRole | Financeiro | AccountingCore |

---

**Arquivo:** `docs/BC-003A_ROLE_MODEL.md`
**Versão:** 1.0.0
**Data:** 2026-07-25
