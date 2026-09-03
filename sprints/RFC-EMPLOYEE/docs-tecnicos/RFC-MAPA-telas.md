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
| `funcionarios.html` | Funcionários (cadastro/edição, filiais, dependentes, histórico de salários e movimentações com vigência, desligar/reativar) | **RFC-002** (cadastro), **RFC-003** (admissão/desligamento: bloqueio de exame admissional vencido e de processamento de desligado), **RFC-016** (movimentações: cargo/depto/salário com vigência) | ✅ telas e campos com máscaras (CPF/CNPJ/PIS/CBO, telefone, moeda); validação de CPF (dígito verificador) e obrigatórios da RFC-002 §3.2; histórico de salários e movimentações (cargo/departamento) com data de vigência (RFC-002 §3.3/RFC-016) com bloqueio de vigência retroativa sobre competências fechadas (§3.4); bloqueio de admissão com exame admissional vencido (RFC-003 §2.3.3) |
| `folha.html` | Folha de Pagamento (abas: Processar, Holerites, Férias, 13º, Rescisão, **Afastamentos**, **Complementar**, Contábil, Config, **Auditoria**) | **RFC-006** (processamento), **RFC-007** (holerite), **RFC-010** (férias), **RFC-011** (13º), **RFC-003** (rescisão: cálculo de verbas, prazo de pagamento, registro/guarda do acerto), **RFC-005** (tabelas INSS/IRRF na Config), **RFC-014** (FGTS/encargos), **RFC-009** (trilha de auditoria + separação de funções), **RFC-012** (aba Afastamentos: CRUD + pró-rata por dias trabalhados + situação do vínculo), **RFC-013** (aba Complementar: ajuste de competência fechada com motivo obrigatório, valores positivos/negativos com limite legal de 70%, fluxo C→V→F→P com Operador/Aprovador e auditoria) | ✅ máscaras de moeda nos campos da Config (tetos/deduções INSS+IRRF) e no processamento; **aba Config** com competência da tabela + histórico de versões + faixas de **Salário-Família** (RFC-005 §4); cotas por funcionário calculadas dos dependentes com `sal_familia=S`, pagas por faixa e **sem incidir INSS/IRRF**; rescisão com verbas + prazo + acerto imutável após pagamento; **aba Férias** com badge **VENCIDA** (gozo após o fim do período concessivo → salário em dobro, RFC-010 Decisão 4) + toast de alerta; **aba 13º** com 1ª parcela sem INSS/IRRF e 2ª/única com descontos (RFC-011 §3.1/§3.2) + CRUD próprio (calcular/incluir/listar/pagar/excluir); **aba Rescisão** com badge **EM DOBRO** (férias vencidas pagas em dobro no acerto, RFC-010 §6/RFC-003) e 13º proporcional; **aba Auditoria** com a trilha imutável (RFC-009 §5: quando/quem/ação/contexto/antes/depois/tabelas) filtrada por competência/ação, e colunas **Operador** e **Aprovador** na lista de competências; fechamento/validação exigem usuário ≠ Operador e pagamento exige Tesouraria ≠ Aprovador (RFC-009 §4.2); **relatório de encargos** (Contábil → botão) com **anexo da trilha de auditoria** da competência (RFC-015 §3/§4.2 — imprimível/PDF, quem operou a competência) |
| `eventos.html` | Eventos da Folha | **RFC-004** (eventos/proventos/descontos) | ✅ máscara de moeda em `ev-teto` |
| `departamentos-cargos.html` | Departamentos e Cargos | **RFC-008** (empresa/departamentos/cargos) | ✅ máscara de moeda em `car-salario-ref` |
| `empresa-folha.html` | Dados da Empresa (Folha) | **RFC-008** (§2, §5.3), **RFC-014** (CNAE/regime tributário → RAT/SAT) | ✅ |
| `estrutura_salarial.html` | Estrutura Salarial (gerenciar + simular) | **RFC-004** (composição de eventos por cargo), **RFC-006** (simulação de cálculo) | ✅ |
| `portal-funcionario.html` | Portal do Funcionário (meus dados, meus holerites, solicitar férias) | **RFC-007** (holerite), **RFC-010** (férias), **RFC-002** (dados pessoais) | ✅ |
| `rh_dashboard.html` | RH Dashboard (KPIs, ausências, alertas, aprovações) | **RFC-010** (alerta de férias vencidas: concessivo expirado sem gozo → badge-alerta + dias de atraso), **RFC-012** (licenças/ausências), **RFC-015** (resumo/relatórios), **RFC-009** (workflow: badges de role, gating de transições por papel, histórico) | ✅ alerta de férias vencidas no painel (RFC-010 §2.1/Decisão 4); workflow com badges de role/histórico e envio de role na transição |
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
| **RFC-005** | Tabelas fiscais (INSS/IRRF/Salário-Família) | Aba **Config** de `folha.html` |
| **RFC-012** | Afastamentos/licenças | Aba **Afastamentos** de `folha.html` (CRUD dedicado: incluir/alterar/excluir + aprovar/rejeitar com badges de status; situação do vínculo "afastado" ao aprovar) + `rh_dashboard.html` (KPIs/ausências) |
| **RFC-013** | Folha complementar | Aba **Complementar** de `folha.html` (CRUD dedicado: calcular/incluir com motivo obrigatório + validar/fechar/pagar/excluir; diferença positiva tributa INSS/IRRF, negativa exige motivo específico e respeita o limite legal de 70% do salário; múltiplas complementares por competência; colunas Operador/Aprovador e badges de situação; auditoria RFC-009) |

---

## 3. Máscaras aplicadas às telas da folha (padrão `js/masks.js`)

Todas as telas do módulo que têm campos monetários usam `data-mask="moeda"` +
`Mascaras.limparMoeda()`/`fmtMoeda()` (exceto alíquotas `%`, que seguem
`type="number"`):

| Página | Campos mascarados |
|---|---|
| `funcionarios.html` | CPF (f-cpf, dp-cpf), PIS, CBO, CEP, telefones (f-celular, f-tel-comercial, f-contato-emerg-tel), moedas (f-salario, f-vt-desconto, f-vr, f-plano-saude-valor, f-pensao-valor em modo valor fixo, sl-salario do histórico de salários) |
| `folha.html` | `c-salario-minimo`, tetos e deduções INSS (f1–f4) e IRRF (f1–f5), `irrf-ded-dep` |
| `eventos.html` | `ev-teto` |
| `departamentos-cargos.html` | `car-salario-ref` |

---

*Mapa gerado em 10/08/2026 a partir dos cabeçalhos/seções de `rfcs/` e das
telas em `pages/`.*
