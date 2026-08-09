# Mapa de Rastreabilidade — Telas × RFCs do Módulo de Folha (RFC-001 a 016)

> Liga cada **tela do ERP** ao(s) RFC(s) de `rfcs/` que ela materializa, e ao
> estado atual de implementação. Complementa o
> `RFC-MAPA-encadeamento.md` (dependências entre RFCs) com o **ângulo da
> interface**: qual página atende cada conceito do módulo.
> Fontes: cabeçalhos e seções das RFCs em `rfcs/` e as telas em `pages/`.

---

## 1. Cobertura das RFCs por tela

| Página | Título da tela | RFC(s) atendidas | Estado |
|---|---|---|---|
| `funcionarios.html` | Funcionários (cadastro/edição, filiais, dependentes, desligar/reativar) | **RFC-002** (cadastro), **RFC-003** (admissão/desligamento), **RFC-016** (movimentações: cargo/depto/salário/jornada) | ✅ telas e campos com máscaras (CPF/CNPJ/PIS/CBO, telefone, moeda); validação de CPF (dígito verificador) e obrigatórios da RFC-002 §3.2 |
| `folha.html` | Folha de Pagamento (abas: Processar, Holerites, Férias, 13º, Rescisão, Contábil, Config) | **RFC-006** (processamento), **RFC-007** (holerite), **RFC-010** (férias), **RFC-011** (13º), **RFC-003** (rescisão), **RFC-005** (tabelas INSS/IRRF na Config), **RFC-014** (FGTS/encargos) | ✅ máscaras de moeda nos campos da Config (tetos/deduções INSS+IRRF) e no processamento |
| `eventos.html` | Eventos da Folha | **RFC-004** (eventos/proventos/descontos) | ✅ máscara de moeda em `ev-teto` |
| `departamentos-cargos.html` | Departamentos e Cargos | **RFC-008** (empresa/departamentos/cargos) | ✅ máscara de moeda em `car-salario-ref` |
| `empresa-folha.html` | Dados da Empresa (Folha) | **RFC-008** (§2, §5.3), **RFC-014** (CNAE/regime tributário → RAT/SAT) | ✅ |
| `estrutura_salarial.html` | Estrutura Salarial (gerenciar + simular) | **RFC-004** (composição de eventos por cargo), **RFC-006** (simulação de cálculo) | ✅ |
| `portal-funcionario.html` | Portal do Funcionário (meus dados, meus holerites, solicitar férias) | **RFC-007** (holerite), **RFC-010** (férias), **RFC-002** (dados pessoais) | ✅ |
| `rh_dashboard.html` | RH Dashboard (KPIs, ausências, alertas, aprovações) | **RFC-012** (licenças/ausências), **RFC-015** (resumo/relatórios), **RFC-009** (workflow) | ✅ |
| `relatorios_rh.html` | Relatórios RH (aniversariantes, por filial, holerites, custos) | **RFC-015** (relatórios/fechamento) | ✅ |
| `emprestimos.html` | Empréstimos (adiantamento salarial, consignado) | **RFC-004** (desconto/adiantamento — evento 26), **RFC-009** (aprovação) | ✅ |
| `usuarios.html` | Usuários do Sistema | **RFC-009** (usuários/papéis) | ✅ |
| `permissoes.html` | Permissões por módulo | **RFC-009** (papéis/permissões/auditoria) | ✅ |
| `periodos.html` | Períodos contábeis | fora do escopo RFC-EMPLOYEE (módulo contábil) | — |
| `ponto.html` | Ponto Eletrônico | fora do escopo RFC-001–016 (RH geral, sem RFC dedicada) | — |
| `fiscal-tabelas.html` | Tabelas fiscais CFOP/CST | fora do escopo RFC-EMPLOYEE (módulo fiscal; não são as tabelas INSS/IRRF do RFC-005) | — |

---

## 2. RFCs sem tela dedicada

| RFC | Tema | Onde é atendida |
|---|---|---|
| **RFC-001** | Conceitos gerais | Transversal (não é uma tela) |
| **RFC-005** | Tabelas fiscais (INSS/IRRF) | Aba **Config** de `folha.html` |
| **RFC-012** | Afastamentos/licenças | `rh_dashboard.html` (KPIs/ausências); sem CRUD dedicado |
| **RFC-013** | Folha complementar | Sem tela própria (evolução planejada) |

---

## 3. Máscaras aplicadas às telas da folha (padrão `js/masks.js`)

Todas as telas do módulo que têm campos monetários usam `data-mask="moeda"` +
`Mascaras.limparMoeda()`/`fmtMoeda()` (exceto alíquotas `%`, que seguem
`type="number"`):

| Página | Campos mascarados |
|---|---|
| `funcionarios.html` | CPF (f-cpf, dp-cpf), PIS, CBO, CEP, telefones (f-celular, f-tel-comercial, f-contato-emerg-tel), moedas (f-salario, f-vt-desconto, f-vr, f-plano-saude-valor, f-pensao-valor em modo valor fixo) |
| `folha.html` | `c-salario-minimo`, tetos e deduções INSS (f1–f4) e IRRF (f1–f5), `irrf-ded-dep` |
| `eventos.html` | `ev-teto` |
| `departamentos-cargos.html` | `car-salario-ref` |

---

*Mapa gerado em 08/08/2026 a partir dos cabeçalhos/seções de `rfcs/` e das
telas em `pages/`.*
