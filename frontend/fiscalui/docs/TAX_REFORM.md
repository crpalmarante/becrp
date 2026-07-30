# FiscalUI — Reforma Tributária: Dois Motores Simultâneos

## O Problema

A reforma tributária (EC 132/2023) cria um novo sistema sem eliminar o antigo de imediato. Durante a **transição** (estimada em 7 anos), ambos coexistirão:

```
HOJE                          TRANSIÇÃO (2026-2033)              FUTURO
─────                         ─────────────────────              ──────
                              ┌──────────────────┐
ICMS                          │  ICMS             │
IPI                           │  IPI              │
PIS                           │  PIS              │
COFINS                        │  COFINS           │
ISS                           │  ISS              │
                              │                   │
                              │  +                │
                              │                   │
                              │  IBS  ← novo      │
                              │  CBS  ← novo      │
                              │  IS   ← novo      │
                              └──────────────────┘

Sistema antigo                Sistema híbrido                   Apenas novo
(5 tributos)                  (8 tributos ativos)               (3 tributos)
```

### Timeline da Transição

```
2026      2027      2028      2029      2030      2031      2032      2033
├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│                             │                             │
│  ICMS 100%                   │  ICMS ↓                     │  ICMS 0%
│  IPI 100%                    │  IPI ↓                      │  IPI 0%
│  PIS 100%    ▲               │  PIS ↓                      │  PIS 0%
│  COFINS 100%  │              │  COFINS ↓                   │  COFINS 0%
│  ISS 100%     │              │  ISS ↓                      │  ISS 0%
                 │
    IBS 0%      │              IBS ↑                         IBS 100%
    CBS 0%                     CBS ↑                          CBS 100%
    IS 0%                      IS ↑                           IS 100%

                         ▲
                         │
                    PONTO CRÍTICO
                    Dois sistemas
                    com alíquotas
                    variando ano a ano
```

### O Que Muda na Prática

```
Cenário: Venda de um produto de SP para RJ em 2029

HOJE (sem reforma):
├── ICMS:  12% interestadual + 6% DIFAL
├── IPI:   5%
├── PIS:   1.65%
├── COFINS: 7.6%
└── Total tributos: ~26.25%

EM 2029 (transição):
├── ICMS:  8% (reduzindo)
├── IPI:   3% (reduzindo)
├── PIS:   1.0% (reduzindo)
├── COFINS: 5.0% (reduzindo)
├── ISS:   Parcial (depende do serviço)
├── IBS:   4% (crescente — novo)
├── CBS:   4% (crescente — novo)
└── Total tributos: ~25% + IBS/CBS

EM 2033+:
├── IBS:   ~12% (definitivo)
├── CBS:   ~5% (definitivo)
└── IS:    Seletivo (produtos específicos)
```

## Impacto no ERP

### O Que Precisa Coexistir

```
NOTA FISCAL (NF-e):

HOJE:                                   TRANSIÇÃO:
┌──────────────────────┐               ┌──────────────────────┐
│ ICMS: 17.40          │               │ ICMS: 12.00          │
│ IPI:  7.75           │               │ IPI:  4.50           │
│ PIS:  0.94           │               │ PIS:  0.60           │
│ COFINS: 4.35         │               │ COFINS: 2.80         │
│                      │               │                      │
│ Total: 30.44         │               │ IBS:  5.80   ← NOVO  │
└──────────────────────┘               │ CBS:  2.90   ← NOVO  │
                                       │                      │
                                       │ Total: 28.60         │
                                       └──────────────────────┘
```

### O Que o Sistema Precisa Suportar

```
1. Duas tabelas de alíquota ativas simultaneamente
2. Dois conjuntos de CST (antigo + novo)
3. Cálculo paralelo dos dois sistemas
4. Exibição comparativa na interface
5. Geração de documentos com ambos tributos
6. Relatórios fiscais para ambos sistemas
7. Redução gradual de alíquotas antigas
8. Aumento gradual de alíquotas novas
9. Período de teste (dry-run) antes da vigência
10. Rollback se reforma for adiada
```

## Como a Arquitetura Resolve

```
┌────────────────────────────────────────────────────────────┐
│  FiscalUI                                                   │
│  Nada muda — continua consumindo JSON                      │
│  Só precisa mostrar mais campos na tela                    │
│  O contrato da API já prevê IBS, CBS, IS                   │
├────────────────────────────────────────────────────────────┤
│         ↑ JSON: agora com IBS, CBS, IS preenchidos         │
├────────────────────────────────────────────────────────────┤
│  Python (API)                                              │
│  Orquestra DOIS motores:                                   │
│  ├── motor_antigo → calcula ICMS, IPI, PIS, COFINS, ISS    │
│  └── motor_novo   → calcula IBS, CBS, IS                   │
│  Retorna TUDO no mesmo JSON                                │
├────────────────────────────────────────────────────────────┤
│         ↑ chamadas paralelas                               │
├────────────────────────────────────────────────────────────┤
│  COBOL                                                     │
│  Módulo antigo: ICMS, IPI, PIS, COFINS (com redução)       │
│  Módulo novo:  IBS, CBS, IS (com alíquotas crescentes)     │
├────────────────────────────────────────────────────────────┤
│  PostgreSQL                                                │
│  tabelas_antigas: aliquotas_icms, cest, beneficios         │
│  tabelas_novas:   aliquotas_ibs, aliquotas_cbs             │
└────────────────────────────────────────────────────────────┘
```

### Contrato da API (já preparado)

```json
{
    "valoresTotais": {
        "valorICMS": 12.00,
        "valorIPI": 4.50,
        "valorPIS": 0.60,
        "valorCOFINS": 2.80,
        "valorISS": 0,

        "valorIBS": 5.80,
        "valorCBS": 2.90,
        "valorIS": 0,

        "totalTributos": 28.60
    },
    "itens": [
        {
            "codigo": "PROD-001",
            "cst": "00",
            "ncm": "7318.15.00",
            "icms": { "cst": "00", "baseCalculo": 145.00, "aliquota": 8.00, "valor": 12.00 },
            "ipi": { "cst": "50", "baseCalculo": 150.00, "aliquota": 3.00, "valor": 4.50 },
            "pis": { "cst": "01", "baseCalculo": 145.00, "aliquota": 0.65, "valor": 0.60 },
            "cofins": { "cst": "01", "baseCalculo": 145.00, "aliquota": 3.00, "valor": 2.80 },

            "ibs": { "baseCalculo": 150.00, "aliquota": 4.00, "valor": 5.80 },
            "cbs": { "baseCalculo": 145.00, "aliquota": 2.00, "valor": 2.90 }
        }
    ]
}
```

### O Que FiscalUI Precisa Fazer

```
1. Exibir IBS, CBS, IS na tela (campos extras)
2. Mostrar comparativo "antes vs depois"
3. Botão "Simular cenário pós-reforma"
4. Relatório com ambos os regimes

NADA disso é lógica fiscal. É só UI.
```

## Vantagem da Arquitetura

```
ERP Monolítico:
  ┌──────────────────────────────────────┐
  │  Regras ICMS                          │
  │  Regras IPI    ← tudo misturado      │
  │  Regras PIS                           │
  │  Regras IBS   ← enfiar aqui? 😱       │
  │  Tela de venda ← precisa alterar     │
  └──────────────────────────────────────┘
  → Precisa reescrever o sistema inteiro

FiscalUI + Backend em Camadas:
  ┌──────────────────────────────────────┐
  │  FiscalUI: zero alteração na lógica  │
  │  Python: novo endpoint de cálculo    │
  │  COBOL: novo módulo IBS/CBS          │
  │  PostgreSQL: novas tabelas           │
  │                                       │
  │  Frontend: só exibir mais campos     │
  └──────────────────────────────────────┘
  → Adiciona sem quebrar o existente
```

---

**Arquivo:** `docs/TAX_REFORM.md`
**Versão:** 1.0
**Data:** 2026-07-24
