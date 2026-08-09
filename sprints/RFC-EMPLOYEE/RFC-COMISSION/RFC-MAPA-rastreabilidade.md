# Mapa de Rastreabilidade — Módulo de Comissões (RFC-COMISSION)

> Liga cada **conceito de comissão** ao documento (RFC da série + RFC do
> projeto) e à **migration SQL** que o materializa. Complementa o
> `docs-tecnicos/RFC-MAPA-encadeamento.md` (que cobre apenas os RFCs 001–016
> do projeto central).
> Fontes: cabeçalhos e seções dos próprios documentos em `RFC-COMISSION/`,
> `rfcs/` e `db/`.

---

## 1. A série RFC-COMISSION em uma linha

```
RFC-001 (política e reflexos) ◄── RFC-002 (módulo PDV: produto/categoria/taxa)
        ▲                              │
        │                              ▼
        └───────────── RFC-004 (tela de categorias/regras) ──► RFC-003 (dados + db/016)
                       │  ├──► RFC-005 (apuração/vendas)
                       │  ├──► RFC-006 (tela de produtos/regras por produto)
                       │  ├──► RFC-007 (tela de taxa padrão do funcionário)
                       │  └──► RFC-008 (tela de taxa padrão GLOBAL — db/018)
```

| RFC | Tema | Depende de | Impacta |
|---|---|---|---|
| **RFC-COMISSION/001** | Comissões de vendas: política, cálculo, incidências, reflexos | RFC-001, 002, 004, 005 (projeto) | RFC-006, 007, 010, 011 (projeto); RFC-COMISSION/002, 003 |
| **RFC-COMISSION/002** | Módulo de comissões no PDV (produto/categoria/taxa padrão) | RFC-COMISSION/001; RFC-002 (projeto) | RFC-006, 007 (projeto); na prática alimenta RFC-COMISSION/003 (dados) |
| **RFC-COMISSION/003** | Modelo de dados (product_categories, products, commission_rules) | RFC-COMISSION/001, 002; RFC-002, 009 (projeto) | RFC-COMISSION/004, 005, 006, 007 |
| **RFC-COMISSION/004** | Tela de categorias e regras por categoria | RFC-COMISSION/002, 003 | RFC-COMISSION/005; RFC-007, 015 (projeto) |
| **RFC-COMISSION/005** | Apuração das vendas do PDV (venda × item × vendedor) | RFC-COMISSION/002, 003, 004 | RFC-006, 007, 015 (projeto) |
| **RFC-COMISSION/006** | Tela de produtos e regras por produto (evolução do RFC-004) | RFC-COMISSION/002, 003, 004 | RFC-COMISSION/005; RFC-007, 015 (projeto) |
| **RFC-COMISSION/007** | Tela de taxa padrão do funcionário (fallback — evolução do RFC-004/006) | RFC-COMISSION/002, 003, 004, 006 | RFC-COMISSION/005, 008; RFC-007, 015 (projeto) |
| **RFC-COMISSION/008** | Tela de taxa padrão GLOBAL da empresa (fallback final — evolução do RFC-003/007) | RFC-COMISSION/002, 003, 007 | RFC-COMISSION/002, 003 (precedência/resolução), RFC-COMISSION/005; RFC-007, 015 (projeto) |

---

## 2. Tabela de Rastreabilidade por Conceito

### 2.1 Conceitos de negócio

| Conceito | RFC-COMISSION | RFC do projeto | Migration |
|---|---|---|---|
| Comissão = remuneração variável (provento) | 001 §2, §4 | RFC-004 §3.1 (evento 7) | db/010 (seed `payroll_events` código 7) |
| Política de comissão (percentual/faixas/eligibilidade/vigência) | 001 §3 | RFC-005 §6 decisão 2 (tabelas internas para faixas) | — (faixas: evolução via mecânica do RFC-005) |
| Precedência de taxa: **produto → categoria → taxa padrão do funcionário → taxa padrão GLOBAL** | 001 §2, §3, §5 · 002 §3.1 · 008 §2/§3.3 | RFC-004 §3.1 | db/016 (índices únicos parciais em `commission_rules`) · db/018 (`commission_global_rules`) |
| Fonte da comissão: manual/importação (1ª versão) → PDV (evolução) | 001 §3, §5, §9 decisão 1 · 002 §7 decisão 4 | RFC-006 (projeto) §3.1 passo 4 (lançar eventos variáveis) | — |
| Adiantamento de comissão (desconto que abate a devida) | 001 §4 regra 4 | RFC-004 §3.2 (evento 26 Adiantamento) | db/010 (seed evento 26) |
| Comissão negativa (zerar ou abater) | 001 §4 regra 6, §9 decisão 4 | RFC-004 §4 (regras de cálculo) | — |
| DSR sobre comissão (reflexo) | 001 §7.1 | RFC-004 §3.1 (evento 8 DSR) | db/010 (seed evento 8) |
| Incidências INSS/IRRF/FGTS | 001 §6 | RFC-004 §5 · RFC-005 §2/§3 | db/010 (flags `incide_inss/irrf/fgts` do evento 7) · db/012 (`base_fgts`) |

### 2.2 Módulo PDV

| Conceito | RFC-COMISSION | RFC do projeto | Migration |
|---|---|---|---|
| Produto do catálogo de vendas | 002 §2 · 003 §3.2 · 006 §3 | — (módulo comercial fora do escopo) | db/016 (`products`) |
| Categoria de produto (agrupamento com taxa comum) | 002 §3.2 · 003 §3.1 | RFC-008 (projeto) §3 (padrão de cadastro mestre) | db/016 (`product_categories`) |
| Regra de comissão funcionário × produto/categoria × taxa | 002 §3 · 003 §3.3 · 006 §4 | RFC-002 (funcionário) | db/016 (`commission_rules`, `ck_rule_target_exclusive`) |
| Taxa padrão do funcionário (fallback) | 002 §3.1 · 003 §3.3 · 007 §3 | — | db/016 (regra com product/category NULL + índice único parcial) |
| Taxa padrão GLOBAL da empresa (fallback final) | 003 §7 · 007 §6 · 008 §2/§3 | — | db/018 (`commission_global_rules`, `uq_commission_global_default`) |
| Vigência da regra (ativa na data da venda) | 002 §5 regra 3 · 003 §5 | RFC-005 regra 1 (vigência por competência) | db/016 (`valid_from/valid_until`, `ck_rule_validity`) |
| Cálculo no PDV: comissão = valor de venda × taxa | 002 §4 · 001 §4 | RFC-004 §4 (regra de cálculo do evento 7) | — (cálculo na aplicação/COBOL) |
| Inativação lógica (nunca exclusão física) | 003 §4 regra 2 · 004 §8 decisão 3 · 006 §8 decisão 3 · 007 §7 decisão 3 · 008 §8 decisão 3 | RFC-008 (projeto) decisão 4 (padrão do projeto) | db/016 · db/018 (`prevent_hard_delete` reusado) |
| Permissão de escrita (`manter_cadastros`) | 004 §6 · 006 §6 · 007 §5 · 008 §5 · 003 §4 regra 1 | RFC-009 §3.1 (matriz ação×papel) | db/011 (`f_has_permission_guc`) · db/016/db/018 (triggers) |

### 2.3 Tela de cadastro

| Conceito | RFC-COMISSION | RFC do projeto | Migration |
|---|---|---|---|
| Tela de categorias (listagem + formulário) | 004 §3 | RFC-008 (projeto — padrão de cadastros mestres) | db/016 |
| Tela de regras por categoria (funcionário × categoria × taxa) | 004 §4 | RFC-009 §3.1 (ação `manter_cadastros`) | db/016 |
| Tela de produtos (listagem + formulário) | 006 §3 | RFC-008 (projeto — padrão de cadastros mestres) | db/016 (`products`) |
| Tela de regras por produto (funcionário × produto × taxa) | 006 §4 | RFC-009 §3.1 (ação `manter_cadastros`) | db/016 (`commission_rules`, `uq_commission_rules_product`) |
| Tela de taxa padrão (funcionário × taxa padrão) | 007 §3 | RFC-009 §3.1 (ação `manter_cadastros`) | db/016 (`commission_rules`, `uq_commission_rules_default`) |
| Tela de taxa padrão GLOBAL (empresa × taxa) | 008 §3 | RFC-009 §3.1 (ação `manter_cadastros`) | db/018 (`commission_global_rules`, `uq_commission_global_default`) |
| Validações (duplicidade, versionamento por vigência, exclusividade) | 004 §4.2 · 006 §4.2 · 007 §3.2 · 008 §3.2 | — | db/016/db/018 (índices únicos parciais com `status = 'ativo'` + CHECKs) |
| Auditoria das operações de cadastro | 004 §6 | RFC-009 §5 (`audit_log`) | db/009 |

### 2.4 Integração com a folha

| Conceito | RFC-COMISSION | RFC do projeto | Migration |
|---|---|---|---|
| Comissão apurada entra no evento 7 da competência | 001 §5 regra 4 · 002 §4 regra 5 | RFC-006 (projeto) §3.1 passo 4 · §3.2 passos 6–12 | db/010 · db/012 (`payroll_lines`) |
| Comissão no holerite (consolidada por competência) | 002 §5 regra 5 | RFC-007 (projeto) §2.2 (proventos por evento) | db/014 (`payroll_stubs`) · db/015 (`payroll_entries`, UNIQUE stub_id+event_id) |
| Comissão nas médias de férias (12 meses) | 001 §7.2 | RFC-010 (férias) | db/010 (kind `ferias`) |
| Comissão na média do 13º | 001 §7.3 | RFC-011 (13º salário) | db/010 (kind `decimo_terceiro`) |
| Comissões devidas na rescisão | 001 §7.4 | RFC-003 (projeto — admissão/demissão) | db/010 (kind `rescisao`) |
| Detalhamento por venda de origem | 002 §5 regra 5 · 005 §3.3/§7 | RFC-007 (projeto) regra 2 (rastreabilidade) | db/017 (`commission_details` — implementada e validada) |
| Devolução parcial por status do item | 005 §3.2/§5 regra 2 | — | db/017 (`pos_sale_items.status = 'devolvido'`) |
| Congelamento do apurado (fechamento por competência) | 005 §3.5/§5 regra 8 | RFC-006 (projeto — evento 7: valor congelado) | db/017 (`commission_settlements`) |
| Relatório de comissões por venda de origem | 005 §7 · 002 §5 regra 5 | RFC-015 §2.1 (relatório) | db/017 (consulta sobre `commission_details`) |

---

## 3. Conceitos que apontam para MÚLTIPLOS lugares (não-óbvios)

- **Precedência produto → categoria → taxa padrão do funcionário → taxa padrão
  GLOBAL** nasce no **RFC-002 §3.1** (regra de negócio), é referenciada no
  **RFC-001 §2/§3/§5** (política) e é **materializada no banco** pelas db/016
  (índices únicos parciais) e db/018 (`commission_global_rules`) — a consulta de
  referência está no **RFC-003 §5** (níveis por funcionário) e no **RFC-008 §6**
  (nível global).
- **Evento 7 (Comissão/Vendas)** é o ponto de encontro da série com o núcleo:
  definido no **RFC-004 do projeto** (§3.1) e seedado na **db/010**; a série
  apenas o *alimenta* (RFC-002 §4 regra 5) e o *exibe* (RFC-007 (projeto) via db/015).
- **Faixas escalonadas por meta** estão descritas no **RFC-001 §3** (política)
  mas fora da 1ª versão; a mecânica de implementação é a **decisão 2 do
  RFC-005** (tabelas internas genéricas), não a db/016.

---

## 4. Migrations envolvidas (ordem de aplicação)

```
db/002 (employees/set_updated_at/prevent_hard_delete)
   → db/009 (users/roles/audit_log)
   → db/011 (permissions — f_has_permission_guc)
   → db/010 (payroll_periods/payroll_events — evento 7, DSR, adiantamento)
   → db/012 (payroll_runs/payroll_lines — resultado consolidado)
   → db/013 (tax_tables — tabelas INSS/IRRF do RFC-005)
   → db/014 (payroll_stubs — holerite) → db/015 (payroll_entries — corpo)
   → db/016 (product_categories/products/commission_rules — MÓDULO DE COMISSÕES)
   → db/017 (pos_sales/pos_sale_items/commission_details + commission_settlements — APURAÇÃO E FECHAMENTO DO PDV)
   → db/018 (commission_global_rules — TAXA PADRÃO GLOBAL DA EMPRESA)
```

> A db/016 depende apenas de 002 (employees) e 011 (permissões); a db/017
> depende de 002, 011 e 016 (products/commission_rules). O restante da cadeia é
> necessário quando a comissão **entra na folha** (evento 7 → runs → holerite).

---

## 5. Cobertura atual e pendências

| Item | Status |
|---|---|
| RFC-COMISSION 001–008 + db/016 + db/017 + db/018 | ✅ escritos e validados (migrations testadas em Postgres 16) |
| RFC-COMISSION/007 (tela de taxa padrão do funcionário) | ✅ escrito — interface sobre a db/016 (sem nova migration); taxa padrão já validada nos testes da db/016/017 |
| RFC-COMISSION/008 (tela de taxa padrão GLOBAL da empresa) | ✅ escrito — nova tabela `commission_global_rules` (db/018) criada e validada na suíte; duplicidade e versionamento por inativação cobertos |
| RFC-COMISSION/006 (tela de produtos/regras por produto) | ✅ escrito — interface sobre a db/016 (sem nova migration); regras por produto já validadas nos testes da db/016/017 |
| RFC-COMISSION/005 (apuração/vendas) | ✅ implementado — `pos_sales`/`pos_sale_items`/`commission_details` + `commission_settlements` (db/017); devolução parcial por status do item e congelamento do apurado por competência |
| Teste de integração das db/016 + 017 + 018 | ✅ `tests/test_commission_rules_integration.py` (33 casos — precedência, versionamento de regra, estorno, devolução parcial, congelamento do apurado, relatório por venda de origem, imutabilidade, telas de regras por produto do RFC-006, de taxa padrão do funcionário do RFC-007 e de taxa padrão GLOBAL do RFC-008) |
| COBOL (evento 7 no cálculo) | ✅ PAYCALC/CALCEVENT recebem a comissão apurada (evento 007) com testes ctypes (`test_ctypes_paycalc.py`, `test_ctypes_calcevent.py`) |
| Referência cruzada no mapa central | ✅ README.md e PLAN_ERP.md citam a série e a db/016; PLAN_ERP.md também cita a db/017 |

---

*Mapa gerado em 05/08/2026 a partir dos cabeçalhos/seções de `RFC-COMISSION/`,
`rfcs/` e `db/`.*
