# FiscalUI — Parametrização: O Pesadelo da Manutenção

## O Problema

Um ERP brasileiro depende de **milhares de parâmetros** para funcionar. Cada parâmetro precisa ser configurado, atualizado e mantido. A manutenção disso consome mais tempo que qualquer outra atividade no ERP.

### Cadeia de Parâmetros por Produto

```
Produto
└── NCM                    ~15.000 códigos (atualizado periodicamente pela Receita)
    ├── Alíquota IPI       varia por NCM
    ├── Alíquota PIS       varia por NCM
    ├── Alíquota COFINS    varia por NCM
    └── CEST               ~5.000 códigos (atualizado por UF)
         └── Margem ST     varia por CEST × UF
              └── Alíquota ICMS-ST  varia por CEST × UF × produto
                   └── FCP         varia por UF

CFOP                    ~2.000 códigos
└── CFOP × UF           varia por estado (cada UF pode ter regras diferentes)

CST ICMS                dezenas de códigos
└── CST × UF            cada UF interpreta de forma diferente

CSOSN                   Simples Nacional
└── CSOSN × Regime      varia por anexo do Simples

Origem da Mercadoria    0 a 8
└── Origem × NCM        varia por produto

Benefícios Fiscais      milhares (cada UF tem seus próprios)
└── Benefício × UF × NCM × Data  combinação exata
```

### Exemplo de Parametrização Real

```
Para um único produto (PARAFUSO 1/4), o ERP precisa saber:

Produto:       PARAFUSO 1/4
NCM:           7318.15.00
NCM Exceção:   7318.15.00 Ex 001 (se houver)
CEST:          21.023.00 (apenas para certas UF)
CFOP:          5101 (venda dentro do estado)
               6101 (venda interestadual)
               5102 (venda para não contribuinte)
               6102 (venda interestadual não contribuinte)
               5201 (devolução)
               6201 (devolução interestadual)
CST ICMS:      00 (tributada integralmente)
               20 (redução de base)
               40 (isenta)
               41 (não tributada)
               60 (ST)
               depende da UF destino + cliente
CSOSN:         102, 300, 500 (depende do anexo)
Origem:        0 (nacional)
Alíquota ICMS: 18% (SP)
               12% (interestadual SP→RJ)
               7%  (interestadual SP→MT)
               4%  (importados)
IPI:           5%
PIS:           1.65% (cumulativo)
               0.65% + 1.25% (não cumulativo)
COFINS:        7.6% (cumulativo)
               3.0% + 5.0% (não cumulativo)
ICMS-ST:       Sim para algumas UF (CEST ativo)
FCP:           Varia por UF destino
Benefício:     Redução de base de 12% para 7% (se credenciado)
```

## Onde Esses Parâmetros Estão

```
┌──────────────────────────────────────┐
│  ERP Monolítico Típico               │
├──────────────────────────────────────┤
│                                      │
│  Tabelas no banco:                   │
│  ├── produto (campos fixos)          │
│  ├── ncm (importado manualmente)     │
│  ├── cfop (importado manualmente)    │
│  ├── cest (importado manualmente)    │
│  ├── aliquota (cadastro manual)      │
│  ├── beneficio (cadastro manual)     │
│  └── excecao (correção manual)       │
│                                      │
│  Código hardcoded:                   │
│  ├── if uf == 'SP': aliquota = 18   │
│  ├── if ncm.startsWith('7318'):      │
│  └── case CFOP: ...                  │
│                                      │
│  Planilhas de parametrização:        │
│  ├── PARAM_CLIENTE.xlsx              │
│  ├── PARAM_PRODUTO.xlsx              │
│  └── EXCECOES_2026.xlsx              │
│                                      │
└──────────────────────────────────────┘

Resultado:
- Parâmetros espalhados entre banco, código e planilha
- Sincronização manual (sujeita a erro)
- Controle de versão inexistente
- Auditoria impossível
- Cada cliente com sua própria "configuração"
```

## A Abordagem FiscalUI + Backend

```
┌──────────────────────────────────────────────────────────────┐
│  FiscalUI                                                     │
│  ⊗ Não gerencia parâmetros tributários                        │
│  ⊗ Não tem tabela NCM, CFOP, CEST, CST                       │
│  ⊗ Não sabe o que é benefício fiscal                         │
│                                                               │
│  ✓ Tem formulários de cadastro dinâmicos                      │
│  ✓ Componentes genéricos (DataGrid, Form, Select)            │
│  ✓ Interface de busca (autocomplete NCM, CFOP)                │
│  ✓ Upload de planilha (CSV/Excel) para importação            │
└──────────────────────────────────────────────────────────────┘
```

### Onde Fica Cada Coisa

```
┌─────────────────────────────────────────────────────────────┐
│  PARÂMETRO                       │  ONDE VIVE               │
├─────────────────────────────────────────────────────────────┤
│  Tabela NCM oficial              │  Backend (atualização     │
│  Tabela CEST                     │  automática via API       │
│  Tabela CFOP                     │  pública da Receita/      │
│  Tabela CST/CSOSN                │  SEFAZ)                   │
│  Alíquotas internas por UF       │                           │
│  Alíquotas interestaduais        │                           │
├─────────────────────────────────────────────────────────────┤
│  Regras de tributação por        │  Backend (Rules Engine)   │
│  NCM × UF × Regime × CFOP       │  Tabelas de regras        │
│  Benefícios fiscais por UF       │  configuráveis via        │
│  Exceções por cliente/produto    │  interface administrativa │
├─────────────────────────────────────────────────────────────┤
│  Cadastro de produto             │  Backend + FiscalUI       │
│  (NCM, origem, CEST manual)      │  (formulário genérico)    │
│  Cadastro de cliente             │                           │
│  (regime, IE, contribuinte)      │                           │
├─────────────────────────────────────────────────────────────┤
│  Parametrização do cliente       │  FiscalUI (via JSON       │
│  (configurações da UI)           │  da API de config)        │
│  Layout de tela                  │                           │
│  Preferências de exibição        │                           │
└─────────────────────────────────────────────────────────────┘
```

### API de Parâmetros

```json
// GET /api/parametros/ncm?search=7318
// FiscalUI → autocomplete de NCM
{
    "items": [
        {
            "codigo": "7318.15.00",
            "descricao": "Parafusos e porcas, de ferro fundido, ferro ou aço",
            "unidade": "UN",
            "aliquotaIPI": 5.00,
            "aliquotaPIS": 1.65,
            "aliquotaCOFINS": 7.60,
            "cest": "21.023.00",
            "excecoes": []
        }
    ]
}

// GET /api/parametros/cfop?uf=SP&operacao=VENDA
// FiscalUI → filtrar CFOP por operação + UF
{
    "items": [
        { "codigo": "5101", "descricao": "Venda de produção do estabelecimento" },
        { "codigo": "5102", "descricao": "Venda a não contribuinte" },
        { "codigo": "5103", "descricao": "Venda de produção do estabelecimento (Suframa)" }
    ]
}

// GET /api/parametros/cst?regime=REGIME_NORMAL&uf=SP&operacao=VENDA
{
    "items": [
        { "codigo": "00", "descricao": "Tributada integralmente" },
        { "codigo": "10", "descricao": "Tributada com cobrança do ST" },
        { "codigo": "20", "descricao": "Tributada com redução de base" },
        { "codigo": "40", "descricao": "Isenta" },
        { "codigo": "41", "descricao": "Não tributada" },
        { "codigo": "60", "descricao": "ST anterior" }
    ]
}

// GET /api/parametros/aliquota?ufOrigem=SP&ufDestino=RJ&ncm=7318.15.00
// FiscalUI → consultar alíquota para exibição
{
    "icms": {
        "aliquota": 12.00,
        "modalidade": "INTERESTADUAL",
        "difal": 6.00,
        "fcp": 0
    },
    "ipi": { "aliquota": 5.00 },
    "pis": { "aliquota": 1.65 },
    "cofins": { "aliquota": 7.60 }
}
```

### Hierarquia de Resolução de Parâmetros

Quando o Tax Engine precisa decidir um parâmetro, ele segue uma hierarquia:

```
1. Exceção do cliente            (cliente X não paga ST)
2. Exceção do produto            (produto Y tem redução de base)
3. Exceção por contrato          (cliente X + produto Y)
4. Regra geral por UF            (SP → RJ: 12%)
5. Regra nacional                (interestadual padrão)
6. Fallback / default             (valor padrão seguro)
```

### Atualização de Parâmetros

```
NCM / CEST / CFOP:
  → Fonte oficial (Receita Federal, SEFAZ)
  → Atualização automática via API pública
  → Backend consome e atualiza o banco
  → FiscalUI: zero ação

Alíquotas:
  → Publicadas nos DOE (Diário Oficial)
  → Cadastradas via backend administrativo
  → FiscalUI: formulário de configuração (se necessário)

Benefícios fiscais:
  → Concedidos por UF, por empresa
  → Cadastrados via backend administrativo
  → FiscalUI: formulário genérico de cadastro

Exceções por cliente/produto:
  → Cadastradas no ERP (via FiscalUI)
  → FiscalUI: DataGrid + Form de exceções
```

### Formulário de Exceção (FiscalUI)

```json
// POST /api/excecoes
// Request (FiscalUI → Backend)
{
    "tipo": "PRODUTO_CLIENTE",
    "cliente": { "cnpj": "99.888.777/0001-11" },
    "produto": { "codigo": "PROD-001" },
    "regra": {
        "campo": "cst_icms",
        "valor": "40",
        "motivo": "Cliente isento por convenio ICMS 15/93",
        "vigenciaInicio": "2026-01-01",
        "vigenciaFim": "2026-12-31"
    }
}
```

## O Que FiscalUI Entrega

```
FiscalUI provê:

1. Componentes de cadastro genéricos (CRUD)
   → DataGrid para listar parâmetros
   → Form para cadastrar/editar
   → Select com autocomplete (NCM, CFOP, CST)
   → Upload de planilha para importação em lote

2. Interface de parametrização
   → Tela de exceções por cliente
   → Tela de exceções por produto
   → Tela de regras gerais (admin)

3. Feedback visual
   → Indicar se parâmetro veio de regra geral ou exceção
   → Mostrar hierarquia: "NCM → CST → Exceção do cliente"
   → Histórico de alterações (quem, quando, o que)

4. Nada disso é lógica fiscal
   → É só UI genérica sobre dados estruturados
```

---

**Arquivo:** `docs/TAX_PARAMETERIZATION.md`
**Versão:** 1.0
**Data:** 2026-07-24
