# RFC-008 — Empresa, Departamentos e Cargos

| Campo | Valor |
|---|---|
| **Título** | Cadastros mestres: Empresa, Departamentos e Cargos |
| **Autor** | crpalmarante |
| **Status** | 📝 Draft (em revisão) |
| **Data** | 01/08/2026 |
| **Versão** | 1.0.0 |
| **Área** | Conceitos — Cadastros |
| **Depende de** | RFC-001 (Conceitos Gerais) |
| **Impacta** | RFC-002, RFC-007, RFC-014, RFC-016 |

---

## 1. Conceito

**Empresa**, **Departamento** e **Cargo** são os cadastros mestres que dão contexto
ao funcionário (RFC-002) e ao holerite (RFC-007). O funcionário pertence a um
departamento e ocupa um cargo; o holerite exibe a razão social/CNPJ da empresa,
o cargo e o departamento do funcionário.

## 2. Empresa

Dados da organização mantidos no sistema. A 1ª versão é **monocliente** (uma
empresa por instalação — decisão RFC-001).

| Campo | Obrigatório | Observação |
|---|---|---|
| Razão social | ✅ | Exibida no holerite (RFC-007) |
| Nome fantasia | 🔸 | |
| CNPJ | ✅ | Exibido no holerite (RFC-007) |
| CNAE principal | ✅ | Base para RAT/SAT nos encargos (RFC-014) |
| Regime tributário | ✅ | Lucro real, presumido ou Simples Nacional (RFC-014) |
| Inscrição municipal | 🔸 | |
| Endereço completo | ✅ | |
| Contato / responsável | 🔸 | |

## 3. Departamento / Centro de Custo

Unidade organizacional usada no rateio e nos relatórios (RFC-015).

| Campo | Obrigatório | Observação |
|---|---|---|
| Código | ✅ | Identificador único |
| Descrição | ✅ | Ex.: "TI", "Comercial" |
| Centro de custo | 🔸 | Usado em relatórios e rateio |
| Responsável | 🔸 | |
| Situação | ✅ | Ativo / inativo |

## 4. Cargo

Posição ocupada pelo funcionário (tabela de cargos referenciada no RFC-002).

| Campo | Obrigatório | Observação |
|---|---|---|
| Código | ✅ | Identificador único |
| Descrição | ✅ | Ex.: "Analista de Sistemas" |
| CBO | 🔸 | Classificação Brasileira de Ocupações |
| Salário de referência | 🔸 | Informativo; o salário real é do funcionário (RFC-002) |
| Situação | ✅ | Ativo / inativo |

## 5. Regras Gerais

1. **O funcionário referencia cargo e departamento** — não são copiados para o
   cadastro; a alteração é feita por movimentação contratual (RFC-016).
2. **Inativação não apaga histórico** — um cargo/departamento inativo não pode
   ser atribuído a novos funcionários, mas permanece no histórico dos antigos.
3. **CNAE e regime tributário são obrigatórios** — alimentam o cálculo de
   encargos patronais (RFC-014).
4. **Empresa única** — a 1ª versão não cria nem troca de empresa em runtime;
   os dados são configurados uma vez (monocliente, RFC-001).

## 6. Decisões Aprovadas

1. **CNAE e regime tributário obrigatórios na empresa** — necessários para os
   encargos patronais (RFC-014). ✅ 01/08/2026
2. **Departamento com centro de custo opcional** — relatórios podem consolidar
   por departamento sem exigir centro de custo na 1ª versão. ✅ 01/08/2026
3. **CBO opcional no cargo** — obrigar CBO só se formos usar para relatórios ou
   eSocial no futuro. ✅ 01/08/2026
4. **Inativação lógica (nunca exclusão física)** — para empresa, departamento e
   cargo, preservando o histórico. ✅ 01/08/2026

## 7. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| _em aberto_ | _autor_ | ⏳ | — |
