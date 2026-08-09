# Mapa de Encadeamento — RFCs 001–016 (+ séries RFC-COMISSION 001–008 e RFC-Payroll 001–004)

> Diagrama das **dependências** ("Depende de") e **impactos** ("Impacta") entre os
> 16 RFCs do sistema de Folha de Pagamento.
> Gerado a partir dos cabeçalhos dos próprios RFCs em `../rfcs/`.
> As **séries RFC-COMISSION 001–008** (módulo de comissões do PDV) e
> **RFC-Payroll 001–004** (módulo de folha de pagamento — contabilização) são
> complementares a este mapa — ver **§6** e **§7** e os mapas detalhados
> `RFC-COMISSION/RFC-MAPA-rastreabilidade.md` e
> `RFC-Payroll/RFC-MAPA-rastreabilidade.md`.

---

## 1. Visão Geral em Camadas

```
┌══════════════════════════════════════════════════════════════════════┐
│  CAMADA 0 · FUNDAMENTO                                                │
└══════════════════════════════════════════════════════════════════════┘

        ┌──────────────────────────────────────┐
        │  RFC-001 · Conceitos Gerais          │   não depende de nada
        └────────────────────┬─────────────────┘   (RFC fundador)
                             │
                             │  impacta 002–016
                             ▼
┌══════════════════════════════════════════════════════════════════════┐
│  CAMADA 1 · CADASTROS MESTRES                                        │
└══════════════════════════════════════════════════════════════════════┘

   ┌─────────────────────────┐      ┌─────────────────────────┐
   │ RFC-002 · Funcionário   │◄─────│ RFC-008 · Empresa,      │
   │   depende de (001)      │      │   Departamentos, Cargos │
   └───────────┬─────────────┘      │   depende de (001)      │
               │                    └──────┬─────────┬────────┘
               │                           │         │
               ▼                           ▼         ▼
┌══════════════════════════════════════════════════════════════════════┐
│  CAMADA 2 · PROCESSOS E REGRAS DE CÁLCULO                            │
└══════════════════════════════════════════════════════════════════════┘

   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
   │ RFC-003          │   │ RFC-004          │◄─►│ RFC-005          │
   │ Adm./Rescisão    │   │ Eventos          │   │ Tabelas Fiscais  │
   │ (001, 002)       │   │ (001, 002, 005)  │   │ (001, 004)       │
   └────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
            │                      │                      │
            └──────────────────────┼──────────────────────┘
                                   ▼
┌══════════════════════════════════════════════════════════════════════┐
│  CAMADA 3 · PROCESSAMENTO                                            │
└══════════════════════════════════════════════════════════════════════┘

        ┌────────────────────────────────────────────┐
        │  RFC-006 · Processamento da Folha          │
        │  depende de (001, 002, 003, 004, 005)      │
        └───────────────────┬────────────────────────┘
                            │
                            ▼
┌══════════════════════════════════════════════════════════════════════┐
│  CAMADA 4 · SAÍDAS E CONSUMO                                         │
└══════════════════════════════════════════════════════════════════════┘

   ┌─────────────────────────┐      ┌─────────────────────────┐
   │ RFC-007 · Holerite      │      │ RFC-015 · Relatórios e  │
   │ (001, 004, 006)         │      │  Fechamento             │
   └─────────────────────────┘      │ (006, 007, 014)         │
                                    └─────────────────────────┘
```

---

## 2. Processos Transversais (folhas especiais, governança e encargos)

Estes RFCs não formam uma camada única — são **transversais** ao fluxo principal:

```
FOLHAS ESPECIAIS
   ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
   │ RFC-010    │ │ RFC-011    │ │ RFC-012    │ │ RFC-013    │ │ RFC-016    │
   │ Férias     │ │ 13º Sal.   │ │ Afastamento│ │ Complement.│ │ Moviment.  │
   │ (001,002,  │ │ (001,002,  │ │ (001,002,  │ │ (001,006)  │ │ (001,002,  │
   │  004,006)  │ │  004,006)  │ │  006)      │ │            │ │  008)      │
   └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
         │              │              │              │              │
         │              │              │              │              ├──► 004
         │              │              │              │              ├──► 006
         │              │              │              │              ├──► 007
         │              │              │              │              ├──► 013
         │              │              │              │              └──► 015
         │              │              │              └──► 006/007/009
         │              │              └──► 006/010/011
         │              └──► 003/006/007/014
         └──► 003/006/007/012

GOVERNANÇA E ENCARGOS (alimentam/consumem o processamento)
   ┌──────────────────────────┐      ┌──────────────────────────┐
   │ RFC-009 · Usuários,      │      │ RFC-014 · Encargos       │
   │  Papéis e Auditoria      │      │  Patronais e FGTS        │
   │  (001, 006)              │      │  (001, 004, 005, 008)    │
   └──────────┬───────────────┘      └───────────┬──────────────┘
              │                                  │
              ├──► 006                          ├──► 007
              ├──► 013                          └──► 015
              └──► 015
```

---

## 3. Tabela Completa de Dependências e Impactos

| RFC | Tema | Depende de | Impacta |
|---|---|---|---|
| **001** | Conceitos Gerais | — (fundador) | 002–016 (todos) |
| **002** | Cadastro de Funcionário | 001 | 003, 006 |
| **003** | Admissão e Demissão | 001, 002 | 006 |
| **004** | Eventos (proventos/descontos) | 001, 002, 005 | 006, 007 |
| **005** | Tabelas Fiscais | 001, 004 | 006, 007 |
| **006** | Processamento da Folha | 001–005 | 007 |
| **007** | Holerite | 001, 004, 006 | — (saída) |
| **008** | Empresa, Departamentos, Cargos | 001 | 002, 007, 014, 016 |
| **009** | Usuários, Papéis, Auditoria | 001, 006 | 006, 013, 015 |
| **010** | Férias | 001, 002, 004, 006 | 003, 006, 007, 012 |
| **011** | 13º Salário | 001, 002, 004, 006 | 003, 006, 007, 014 |
| **012** | Afastamentos e Licenças | 001, 002, 006 | 006, 010, 011 |
| **013** | Folha Complementar | 001, 006 | 006, 007, 009 |
| **014** | Encargos Patronais e FGTS | 001, 004, 005, 008 | 007, 015 |
| **015** | Relatórios e Fechamento | 006, 007, 014 | 006, 009 |
| **016** | Movimentações Contratuais | 001, 002, 008 | 004, 006, 007, 013, 015 |

---

## 4. Observações de Estrutura

### 4.1 RFCs raiz e folha
- **Raiz:** RFC-001 — não depende de nenhum outro; impacta todos.
- **Folhas (não impactam ninguém):** RFC-007 (Holerite) — consumidor final.
- **Centro de gravidade:** RFC-006 (Processamento) — depende de 001–005 e é
  impactado/consumido por quase todos os demais.

### 4.2 Círculos e reciprocidades (intencionais)
- **004 ↔ 005** — Eventos e Tabelas Fiscais dependem um do outro (incidências
  dos eventos definem as bases que as tabelas usam).
- **006 ↔ 009** — Processamento depende de Governança (autorização das ações de
  estado) e Governança impacta o Processamento.
- **010 ↔ 012** — Férias impactam Afastamentos (suspensão do período aquisitivo)
  e Afastamentos impactam Férias — recíproco.
- **012 → 010/011** — Afastamentos impactam Férias e 13º (meses não contados).

### 4.3 Dependência "não óbvia"
- **016 (Movimentações) impacta 004 (Eventos)** — movimentações mudam salário e
  jornada, que alimentam eventos proporcionais, embora 016 não dependa de 004.
- **008 (Empresa) impacta 014 (Encargos)** — o CNAE da empresa define o RAT.

---

## 5. Status de Aprovação (01/08/2026)

| RFC | Decisões | Status |
|---|---|---|
| 001–016 | ✅ aprovadas | ✅ |

---

## 6. Série RFC-COMISSION — módulo de comissões do PDV (001–008)

Série **complementar** aos RFCs 001–016: modela as comissões de vendas do PDV
(política, regras por produto/categoria/taxa padrão e apuração), materializadas
nas migrations **db/016** (regras de comissão), **db/017** (apuração das vendas)
e **db/018** (taxa padrão GLOBAL da empresa). O resultado alimenta o **evento 7
(Comissão/Vendas)** do RFC-004 (projeto) e segue para o processamento (RFC-006,
projeto) e o holerite (RFC-007, projeto).

> **Atenção à colisão de numeração:** os RFCs deste mapa (001–016) são os do
> **projeto central** — inclusive o **RFC-008 (projeto)** (Empresa, Departamentos,
> Cargos), citado nas tabelas e diagramas acima. O **RFC-COMISSION/008** é outro
> documento (tela de taxa padrão GLOBAL da empresa).

```
RFC-COMISSION/001 (política) ◄── RFC-COMISSION/002 (módulo PDV: produto/categoria/taxa)
        ▲                              │
        │                              ▼
        └───────────── RFC-COMISSION/004 (telas) ──► RFC-COMISSION/003 (dados + db/016)
                       │  ├──► RFC-COMISSION/005 (apuração/vendas + db/017)
                       │  ├──► RFC-COMISSION/006 (tela de produtos/regras)
                       │  ├──► RFC-COMISSION/007 (tela de taxa padrão do funcionário)
                       │  └──► RFC-COMISSION/008 (tela de taxa padrão GLOBAL + db/018)
                       ▼
        alimenta o evento 7 (Comissão/Vendas) do RFC-004 (projeto)
```

| RFC | Tema | Depende de | Impacta |
|---|---|---|---|
| **RFC-COMISSION/001** | Comissões de vendas: política, cálculo, incidências, reflexos | RFC-001, 002, 004, 005 (projeto) | RFC-006, 007, 010, 011 (projeto); RFC-COMISSION/002, 003 |
| **RFC-COMISSION/002** | Módulo de comissões no PDV (produto/categoria/taxa padrão) | RFC-COMISSION/001; RFC-002 (projeto) | RFC-006, 007 (projeto); na prática alimenta RFC-COMISSION/003 (dados) |
| **RFC-COMISSION/003** | Modelo de dados (product_categories, products, commission_rules) | RFC-COMISSION/001, 002; RFC-002, 009 (projeto) | RFC-COMISSION/004, 005, 006, 007, 008 |
| **RFC-COMISSION/004** | Tela de categorias e regras por categoria | RFC-COMISSION/002, 003 | RFC-COMISSION/005; RFC-007, 015 (projeto) |
| **RFC-COMISSION/005** | Apuração das vendas do PDV (venda × item × vendedor) | RFC-COMISSION/002, 003, 004 | RFC-006, 007, 015 (projeto) |
| **RFC-COMISSION/006** | Tela de produtos e regras por produto (evolução do RFC-004) | RFC-COMISSION/002, 003, 004 | RFC-COMISSION/005; RFC-007, 015 (projeto) |
| **RFC-COMISSION/007** | Tela de taxa padrão do funcionário (fallback — evolução do RFC-004/006) | RFC-COMISSION/002, 003, 004, 006 | RFC-COMISSION/005, 008; RFC-007, 015 (projeto) |
| **RFC-COMISSION/008** | Tela de taxa padrão GLOBAL da empresa (fallback final — evolução do RFC-003/007) | RFC-COMISSION/002, 003, 007 | RFC-COMISSION/002, 003 (precedência/resolução), RFC-COMISSION/005; RFC-007, 015 (projeto) |

> Mapa detalhado da série, conceito por conceito e migration por migration:
> **`RFC-COMISSION/RFC-MAPA-rastreabilidade.md`**.

---

## 7. Série RFC-Payroll — módulo de folha de pagamento (001–004)

Série **complementar** aos RFCs 001–016: especifica o **módulo de folha de
pagamento** com numeração e qualificador próprios (`RFC-Payroll/00N`).
**RFC-Payroll/001 (Contabilização Automática da Folha de Pagamento)** estende os
modelos da plataforma (`hr.salary.rule`/`hr.payslip`, módulos `eh_hr_payroll` +
`account`) para mapear contas de débito/crédito por regra salarial, configurar
diário e contas padrão no contracheque, lançar automaticamente na confirmação e
estornar no cancelamento; **RFC-Payroll/002 (Fluxos de Contabilização)** detalha
a geração do lançamento (movimento por regra por categoria) e o algoritmo de
estorno; **RFC-Payroll/003 (Contabilização da Comissão — Evento 7)** contabiliza
a comissão apurada no PDV (RFC-COMISSION) como regra mapeada com par de contas,
reutilizando a mesma mecânica — **sem models nem migrations próprios** (a
contabilização vive no módulo `account` da plataforma); **RFC-Payroll/004
(Detalhamento por Venda de Origem)** materializa a evolução do RFC-003 §7:
adiciona a **camada analítica de ligação** entre a linha da comissão no
lançamento e a venda de origem (`commission_details`, RFC-COMISSION/005) —
rastreabilidade razão ↔ venda, com o razão permanecendo **consolidado por
regra** (único model próprio do módulo).

> **Atenção à numeração independente:** os números da série **RFC-Payroll/00N**
> são próprios e independentes dos RFCs do projeto central (001–016) e da série
> RFC-COMISSION (001–008). O **RFC-Payroll/001** (contabilização da folha) não
> deve ser confundido com o **RFC-001 (projeto)** (Conceitos Gerais); o
> **RFC-Payroll/003** (contabilização da comissão) não deve ser confundido com o
> **RFC-003 (projeto)** (Admissão e Demissão); o **RFC-Payroll/004**
> (detalhamento por venda de origem) não deve ser confundido com o
> **RFC-004 (projeto)** (Eventos, Proventos e Descontos).

```
RFC-Payroll/001 (contabilização da folha — modelo de dados e funcionalidades)
        │  estende hr.salary.rule/hr.payslip; consome o apurado de comissões pelo evento 7
        ▼
RFC-Payroll/002 (fluxos de contabilização — geração do lançamento por regra/categoria e estorno)
        │  usa a mecânica do módulo `account` (account.move, reversed_entry_id)
        ▼
RFC-Payroll/003 (contabilização da comissão — evento 7 como regra mapeada)
        │  reutiliza a mecânica de 001/002 — sem models/migrations próprios
        ▼
RFC-Payroll/004 (detalhamento contábil por venda de origem no lançamento da comissão)
        │  camada analítica de ligação (único model próprio) — razão permanece consolidado por regra
        ▼
   lançamento contábil no módulo `account` (plataforma) — sem migration própria
```

| RFC | Tema | Depende de | Impacta |
|---|---|---|---|
| **RFC-Payroll/001** | Contabilização automática da folha: modelo de dados e funcionalidades — contas nas regras salariais, diário/contas padrão no contracheque, lançamento automático e estorno | RFC-006, 007 (projeto); módulos `eh_hr_payroll` + `account` (plataforma) | RFC-007 (projeto — vínculos no holerite); RFC-COMISSION/001 (comissão contabilizada); RFC-Payroll/002 (fluxos); RFC-Payroll/003 (comissão — evento 7); RFC-Payroll/004 (detalhamento por venda de origem); RFC-Payroll/005+ (evoluções) |
| **RFC-Payroll/002** | Fluxos de contabilização: geração do lançamento (movimento por regra por categoria) e algoritmo de estorno no cancelamento | RFC-Payroll/001; RFC-006, 007 (projeto); módulos `eh_hr_payroll` + `account` (plataforma) | RFC-007 (projeto — vínculos do lançamento/estorno no holerite); RFC-COMISSION/001 (comissão contabilizada); RFC-Payroll/003 (comissão — evento 7); RFC-Payroll/004 (detalhamento por venda de origem); RFC-Payroll/005+ (evoluções) |
| **RFC-Payroll/003** | Contabilização automática da comissão (evento 7): regra de comissão mapeada com par de contas | RFC-Payroll/001, 002; RFC-COMISSION/001 (política), RFC-COMISSION/005 (apuração); RFC-004, 006 (projeto); módulos `eh_hr_payroll` + `account` (plataforma) | RFC-007 (projeto — holerite); RFC-015 (projeto — relatórios); RFC-COMISSION/001 (comissão contabilizada); RFC-Payroll/004 (detalhamento por venda de origem); RFC-Payroll/005+ (evoluções) |
| **RFC-Payroll/004** | Detalhamento contábil por venda de origem no lançamento da comissão (evento 7): camada analítica de ligação entre a linha do razão e a venda de origem | RFC-Payroll/001, 002, 003; RFC-COMISSION/005 (detalhe analítico); RFC-015 (projeto — relatório); módulos `eh_hr_payroll` + `account` (plataforma) | RFC-015 (projeto — relatório integrado ao lançamento); RFC-COMISSION/005 (detalhe consumido pelo lançamento); RFC-Payroll/005+ (evoluções) |

> **Rastreabilidade por venda de origem** — a rastreabilidade da comissão da
> **venda ao lançamento contábil** (RFC-Payroll/004, camada analítica de ligação
> `commission_move_line_detail`) cruza as duas séries: origem analítica em
> `commission_details` (RFC-COMISSION/005 §7 · db/017), relatório por venda de
> origem no RFC-015 §2.1 (projeto) e **razão consolidado por regra** (decisão 5
> do RFC-Payroll/003) — conceito também rastreado na tabela §2.3 do
> `RFC-Payroll/RFC-MAPA-rastreabilidade.md`.
>
> Mapa detalhado da série: **`RFC-Payroll/RFC-MAPA-rastreabilidade.md`**.

---

*Mapa gerado em 01/08/2026 a partir dos cabeçalhos dos RFCs em `rfcs/` e das
séries `RFC-COMISSION/` (001–008) e `RFC-Payroll/` (001–004).*
