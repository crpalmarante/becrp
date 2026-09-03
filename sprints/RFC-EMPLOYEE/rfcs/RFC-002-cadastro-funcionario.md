# RFC-002 — Cadastro de Funcionário

| Campo | Valor |
|---|---|
| **Título** | Cadastro de Funcionário: o que cadastrar |
| **Autor** | crpalmarante |
| **Status** | ✅ Implementado (31/07/2026 — regras §3.2–3.4 e Decisão 1: histórico de salários com vigência, validação de obrigatórios no processamento, bloqueio de competências fechadas) |
| **Data** | 31/07/2026 |
| **Versão** | 1.0.0 |
| **Área** | Conceitos — Cadastros |
| **Depende de** | RFC-001 (Conceitos Gerais) |
| **Impacta** | RFC-003, RFC-006 |

---

## 1. Conceito

**Funcionário** é a pessoa com vínculo empregatício registrado na empresa. O
cadastro do funcionário é a **fonte única de verdade** dos dados usados no
processamento da folha: nada é calculado com informação que não esteja aqui.

## 2. Grupos de Dados

### 2.1 Dados Pessoais
| Campo | Obrigatório | Observação |
|---|---|---|
| Nome completo | ✅ | Como consta no documento oficial |
| Data de nascimento | ✅ | Usada em férias, aniversariantes, IRRF |
| Sexo | ✅ | |
| Estado civil | 🔸 | |
| Nacionalidade | ✅ | |
| CPF | ✅ | Identificador único do funcionário |
| RG / órgão emissor / UF | 🔸 | |
| Título de eleitor | 🔸 | |
| PIS/PASEP | 🔸 | Necessário para benefícios e FGTS |

### 2.2 Contato e Endereço
| Campo | Obrigatório | Observação |
|---|---|---|
| Endereço completo (CEP, logradouro, nº, bairro, cidade, UF) | ✅ | Usado em envio de documentos |
| Telefone / celular | 🔸 | |
| E-mail | 🔸 | Entrega do holerite eletrônico |

### 2.3 Dados Trabalhistas (CTPS)
| Campo | Obrigatório | Observação |
|---|---|---|
| Número CTPS / série / UF | ✅ | Registro legal do vínculo |
| Data de admissão | ✅ | Início do vínculo (ver RFC-003) |
| Data de demissão | 🔸 | Preenchida na rescisão (ver RFC-003) |
| Situação do vínculo | ✅ | Ativo, afastado, em aviso, desligado |

### 2.4 Dados de Cargo e Departamento
| Campo | Obrigatório | Observação |
|---|---|---|
| Cargo | ✅ | Cargo ocupado (tabela de cargos) |
| Departamento / centro de custo | ✅ | Usado em relatórios e rateio |
| Data de posse no cargo | 🔸 | |
| Tipo de vínculo | ✅ | CLT, estagiário, aprendiz, temporário |

### 2.5 Dados Salariais e de Pagamento
| Campo | Obrigatório | Observação |
|---|---|---|
| Salário base (ou valor hora) | ✅ | Base do cálculo |
| Forma de pagamento | ✅ | Mensalista / horista / diarista |
| Banco / agência / conta | ✅ | Para pagamento e holerite |
| Meio de pagamento (depósito, TED, PIX) | 🔸 | |
| Jornada de trabalho / escala | 🔸 | Base para horas extras |
| Carga horária mensal contratual | 🔸 | Usada no cálculo do valor da hora |

### 2.6 Dependentes
| Campo | Obrigatório | Observação |
|---|---|---|
| Nome do dependente | 🔸 | |
| Data de nascimento | 🔸 | Critério para salário-família |
| CPF | 🔸 | |
| Grau de parentesco | 🔸 | |
| Tipo de dependência | 🔸 | Para IRRF (dedução) e/ou salário-família |

### 2.7 Benefícios
| Campo | Obrigatório | Observação |
|---|---|---|
| Optante por vale-transporte | ✅ | Sim/não — afeta desconto de 6% |
| Vale-refeição / alimentação | 🔸 | Valor ou percentual de participação |
| Plano de saúde / odontológico | 🔸 | Valor da coparticipação |
| Outros benefícios | 🔸 | Descritos livremente |

### 2.8 Informações Complementares
| Campo | Obrigatório | Observação |
|---|---|---|
| Escolaridade | 🔸 | |
| Exame médico admissional | 🔸 | Vencimento (ver RFC-003) |
| Restrições / observações | 🔸 | Livre |
| Situação para pensão alimentícia | 🔸 | Percentual ou valor fixo |

## 3. Regras do Cadastro

1. **CPF é único** — não é possível cadastrar dois funcionários com o mesmo CPF.
2. **Todo campo obrigatório deve estar preenchido antes da primeira folha**
   (validação no processamento).
3. **Dados podem mudar ao longo do tempo** — alteração de salário, cargo ou
   dependentes tem **data de vigência**, para o cálculo usar o valor correto na
   competência certa.
4. **A alteração de dados históricos não pode mudar competências já fechadas.**
5. **Desligamento** bloqueia novos processamentos para o funcionário (ver RFC-003).

## 4. Processos Relacionados

- **Admissão** cria o cadastro inicial (RFC-003).
- **Alteração contratual** atualiza salário/cargo com vigência.
- **Afastamento** mantém o vínculo ativo, mas suspende (total ou parcialmente) o
  pagamento durante o período.
- **Rescisão** encerra o vínculo e gera o acerto (RFC-003).

## 5. Decisões Aprovadas

1. **Histórico de salários desde a admissão** — sem ponto de migração; todo o
   histórico do vínculo é registrado. ✅ 31/07/2026
2. **Vínculo único** — um funcionário tem um único vínculo na 1ª versão;
   multiemprego fica para evolução futura. ✅ 31/07/2026
3. **Múltiplos tipos por dependente** — um dependente pode valer para IRRF e
   salário-família ao mesmo tempo (configuração de tipos por dependente). ✅ 31/07/2026

## 6. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| crpalmarante | autor | ✅ Aprovado | 10/08/2026 |
