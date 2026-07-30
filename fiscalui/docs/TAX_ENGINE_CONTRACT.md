# FiscalUI — Tax Engine: Interface e Contrato

## O Problema

O Motor Fiscal é o coração de qualquer ERP brasileiro. Ele precisa calcular, decidir e aplicar a tributação correta para cada operação — considerando dezenas de variáveis que mudam constantemente.

**FiscalUI não resolve o Tax Engine.** Ele só consome o resultado. A complexidade pertence ao backend. Mas a **interface** entre eles precisa ser bem definida.

## Escopo do Tax Engine (Backend — Python/COBOL)

### Impostos

```
ICMS      → Imposto sobre Circulação de Mercadorias e Serviços
ICMS-ST   → Substituição Tributária
FCP       → Fundo de Combate à Pobreza
DIFAL     → Diferencial de Alíquota
IPI       → Imposto sobre Produtos Industrializados
PIS       → Programa de Integração Social
COFINS    → Contribuição para Financiamento da Seguridade Social
ISS       → Imposto sobre Serviços
IBS       → Imposto sobre Bens e Serviços (futuro — reforma)
CBS       → Contribuição sobre Bens e Serviços (futuro)
IS        → Imposto Seletivo (futuro)
IRRF      → Imposto de Renda Retido na Fonte
CSLL      → Contribuição Social sobre o Lucro Líquido
```

### Classificadores

```
CST       → Código de Situação Tributária (ICMS/IPI)
CSOSN     → Código de Situação Tributária do Simples Nacional
CFOP      → Código Fiscal de Operações e Prestações
NCM       → Nomenclatura Comum do Mercosul
CEST      → Código Especificador da Substituição Tributária
Origem    → Origem da mercadoria (0 a 8)
```

### Variáveis de Decisão

```
Estado de origem       → SP, RJ, MG, ...
Estado de destino      → SP, RJ, MG, ...
Município              → São Paulo, Rio, ...
Produto                → Código, NCM, CEST
Serviço                → LC 116, item da lista
Cliente                → Regime, inscrição estadual
Operação               → Venda, devolução, transferência, bonificação
Data                   → Vigência da legislação
Regime do emitente     → Simples, Presunto, Real
Regime do destinatário → Simples, Presunto, Real
Benefício fiscal       → Crédito presumido, redução de base, diferimento
```

### Benefícios Fiscais (Exemplos)

```
Redução de base de cálculo ICMS
Crédito presumido ICMS
Diferimento ICMS
Isenção ICMS
Não-incidência ICMS
Suspensão ICMS
Drawback (IPI)
Reid (IPI)
PIS/COFINS monofásico
PIS/COFINS substituição tributária
PIS/COFINS importação
```

## Contrato FiscalUI ← → Tax Engine

FiscalUI não calcula imposto. Ele **envia os dados da operação** e **recebe o resultado tributário** pronto para exibição.

### Request (FiscalUI → Tax Engine)

```json
{
    "operacao": "VENDA",
    "emitente": {
        "cnpj": "11.222.333/0001-44",
        "regime": "REGIME_NORMAL",
        "uf": "SP",
        "ie": "123.456.789.000"
    },
    "destinatario": {
        "cnpj": "99.888.777/0001-11",
        "uf": "RJ",
        "ie": "987.654.321.000"
    },
    "itens": [
        {
            "codigo": "PROD-001",
            "descricao": "Parafuso 1/4",
            "ncm": "7318.15.00",
            "cest": "21.023.00",
            "cfop": "5101",
            "unidade": "UN",
            "quantidade": 100,
            "valorUnitario": 1.50,
            "valorFrete": 10.00,
            "valorDesconto": 5.00,
            "valorOutras": 0,
            "origem": 0
        }
    ],
    "transporte": {
        "modal": "RODOVIARIO",
        "frete": "CIF"
    },
    "dataOperacao": "2026-07-24"
}
```

### Response (Tax Engine → FiscalUI)

```json
{
    "valoresTotais": {
        "baseCalculoICMS": 145.00,
        "valorICMS": 17.40,
        "baseCalculoICMSST": 0,
        "valorICMSST": 0,
        "valorFCP": 0,
        "baseCalculoIPI": 155.00,
        "valorIPI": 7.75,
        "valorPIS": 0.94,
        "valorCOFINS": 4.35,
        "valorAproximadoTributos": 37.20,
        "totalTributos": 30.44
    },
    "itens": [
        {
            "codigo": "PROD-001",
            "cst": "00",
            "csosn": null,
            "cfop": "5101",
            "ncm": "7318.15.00",
            "cest": "21.023.00",
            "origem": 0,
            "icms": {
                "cst": "00",
                "modalidade": "MARGEM_VALOR_AGREGADO",
                "baseCalculo": 145.00,
                "aliquota": 12.00,
                "valor": 17.40,
                "baseCalculoST": 0,
                "aliquotaST": 0,
                "valorST": 0,
                "valorFCP": 0
            },
            "ipi": {
                "cst": "50",
                "baseCalculo": 155.00,
                "aliquota": 5.00,
                "valor": 7.75
            },
            "pis": {
                "cst": "01",
                "baseCalculo": 145.00,
                "aliquota": 0.65,
                "valor": 0.94
            },
            "cofins": {
                "cst": "01",
                "baseCalculo": 145.00,
                "aliquota": 3.00,
                "valor": 4.35
            }
        }
    ],
    "observacoes": [
        "ICMS calculado com aliquota interestadual SP→RJ (12%)",
        "Produto sujeito a ST (CEST 21.023.00) — base de cálculo reduzida"
    ],
    "erros": []
}
```

## Princípios do Contrato

```
1. FiscalUI nunca decide tributos
   Ele envia dados brutos da operação e recebe o cálculo pronto.

2. Tax Engine nunca renderiza UI
   Ele recebe JSON e devolve JSON — não sabe o que é tela.

3. Versão do contrato é explícita
   Toda request tem "versaoContrato": "1.0" — permite evolução.

4. Erros são campos, não exceções
   Tax Engine retorna erros no JSON, não HTTP 500.
   FiscalUI exibe os erros para o usuário.

5. Observações são texto livre
   O Tax Engine pode incluir observações sobre cada cálculo.
   FiscalUI as exibe na interface para auditoria.

6. Futuro (Reforma Tributária)
   O contrato já prevê IBS, CBS, IS mesmo antes da vigência.
   Quando a reforma entrar, basta o backend começar a preencher.
   FiscalUI: zero alteração.
```

## Implementação Sugerida

```
┌──────────────┐       JSON        ┌────────────────┐
│  FiscalUI    │──────────────────▶│  Python API     │
│  (formulário)│                   │  (orquestrador) │
└──────────────┘                   └───────┬────────┘
                                          │
                                 ┌────────▼────────┐
                                 │  Rules Engine    │
                                 │  (regras de      │
                                 │   tributação)    │
                                 └────────┬────────┘
                                          │
                                 ┌────────▼────────┐
                                 │  COBOL           │
                                 │  (cálculos       │
                                 │   críticos)      │
                                 └────────┬────────┘
                                          │
                                 ┌────────▼────────┐
                                 │  PostgreSQL      │
                                 │  (tabelas:       │
                                 │   alíquotas,     │
                                 │   benefícios,    │
                                 │   NCM, CEST...)  │
                                 └─────────────────┘
```

### Python (Orquestrador de Regras)

```
1. Recebe request do FiscalUI
2. Busca tabelas de alíquota no PostgreSQL
3. Determina CST/CSOSN por produto + UF + cliente
4. Aplica regras de benefício fiscal
5. Chama COBOL para cálculos críticos (validação fiscal)
6. Monta response JSON
```

### COBOL (Cálculos Críticos)

```
Onde a precisão importa:
  - Cálculo de ICMS com arredondamento fiscal (Lei 9.430/96)
  - Cálculo de IPI (base + frete + seguro + outras despesas)
  - Rateio de PIS/COFINS não-cumulativo
  - Validação de CST/CFOP contra NCM
  - Fechamento de lote fiscal (validação cruzada)
```

---

**Arquivo:** `docs/TAX_ENGINE_CONTRACT.md`
**Versão:** 1.0
**Data:** 2026-07-24
