# RFC-001 — Conceitos Gerais do Sistema

| Campo | Valor |
|---|---|
| **Título** | Conceitos gerais do sistema de Folha de Pagamento |
| **Autor** | crpalmarante |
| **Status** | ✅ Concluído (11/08/2026) — documento conceitual, sem código associado |
| **Data** | 31/07/2026 |
| **Versão** | 1.0.0 |
| **Área** | Conceitos |
| **Depende de** | — (RFC fundador) |
| **Impacta** | RFC-002 a RFC-016 |

> **Natureza deste documento:** define **conceitos e processos de negócio**.
> Não trata de tecnologia, implementação ou ferramentas.

---

## 1. Objetivo

Estabelecer a linguagem comum do sistema: o significado de cada conceito
(funcionário, evento, tabela, competência, processamento, holerite) e como os
processos se encadeiam. Todo o restante do sistema deve usar estes termos com o
mesmo significado.

## 2. Conceitos Fundamentais

| Conceito | Definição |
|---|---|
| **Funcionário** | Pessoa registrada na empresa com vínculo empregatício. É o sujeito central de todo o processamento (ver RFC-002). |
| **Cadastro** | Conjunto de informações mestras que descrevem uma entidade (funcionário, cargo, departamento, evento, tabela). São a base de todo o cálculo. |
| **Evento** | Uma unidade de provento (crédito) ou desconto (débito) na folha, com código, descrição, fórmula e regras próprias (ver RFC-004). |
| **Tabela** | Parâmetro oficial ou interno versionado por competência, usado no cálculo (INSS, IRRF, salário-família — ver RFC-005). |
| **Competência** | Período mensal a que se refere o processamento (ex.: competência 01/2026 = folha de janeiro de 2026). |
| **Processamento** | A execução do cálculo da folha de uma competência, gerando o resultado por funcionário (ver RFC-006). |
| **Holerite** | O demonstrativo de pagamento do funcionário: o que recebeu, o que foi descontado e o líquido (ver RFC-007). |
| **Admissão** | O processo de entrada do funcionário na empresa (ver RFC-003). |
| **Demissão / Rescisão** | O processo de saída do funcionário e o acerto das verbas (ver RFC-003). |

## 3. Visão dos Processos

```
        ┌───────────┐     ┌─────────────────┐     ┌────────────────┐
        │ ADMISSÃO  │ ──▶ │  CADASTRO       │ ──▶ │  EVENTOS E     │
        │ (RFC-003) │     │  DE FUNCIONÁRIO │     │  TABELAS       │
        └───────────┘     │  (RFC-002)      │     │  (RFC-004/005) │
                          └─────────────────┘     └───────┬────────┘
                                                          │
        ┌───────────────┐     ┌───────────────────────────▼──────┐
        │  HOLERITE     │ ◀── │  PROCESSAMENTO DA FOLHA          │
        │  (RFC-007)    │     │  (RFC-006)                       │
        └───────────────┘     └──────────────────────────────────┘
        ┌───────────────┐
        │  DEMISSÃO /   │
        │  RESCISÃO     │
        │  (RFC-003)    │
        └───────────────┘
```

### 3.1 Fluxo de alto nível

1. **Admissão** do funcionário → gera o registro no **cadastro**.
2. **Cadastro** reúne todos os dados que o cálculo precisa (salário, cargo,
   dependentes, benefícios).
3. **Eventos e tabelas** definem o que entra na folha e com quais parâmetros.
4. **Processamento mensal** usa cadastro + eventos + tabelas para calcular a
   competência.
5. O resultado é apresentado no **holerite**.
6. A **demissão** encerra o vínculo e gera o acerto rescisório.

## 4. Regras Gerais

1. **Um funcionário pertence a uma empresa e a uma competência em um momento.**
2. **Toda informação que entra no cálculo deve estar no cadastro, em um evento
   ou em uma tabela** — nada de valores "solto" no processamento.
3. **Competência é imutável após o fechamento** (ver RFC-006).
4. **Todo valor exibido no holerite deve ser rastreável** até sua origem
   (cadastro, evento ou tabela).
5. **Tabelas são versionadas por competência** — o cálculo da competência usa
   sempre a tabela vigente naquele mês (ver RFC-005).

## 5. Escopo Fora Deste RFC

- Detalhe de cada cadastro → RFC-002.
- Detalhe dos processos de entrada/saída → RFC-003.
- Detalhe dos eventos → RFC-004.
- Detalhe das tabelas → RFC-005.
- Detalhe do processamento → RFC-006.
- Detalhe do holerite → RFC-007.

## 6. Decisões Aprovadas

1. **Monocliente** — a 1ª versão atende uma empresa por instalação;
   multiempresa fica para evolução futura. ✅ 31/07/2026
2. **Mensal + complementar + 13º** — a 1ª versão processa folha mensal,
   folha complementar (ajustes de competência fechada) e 13º salário. ✅ 31/07/2026

## 7. Rastreabilidade da Conclusão (11/08/2026)

Este RFC é **conceitual** — define a linguagem comum e os princípios do
módulo. Não possui implementação de código própria (como os demais RFCs
002–016), pois seu conteúdo foi **materializado em todos eles**: cada conceito
(competência, evento, tabela, holerite, fluxo) está implementado e coberto pelo
CI no respectivo RFC. Encerrado como documento de referência do módulo.

| Princípio (RFC-001 §4) | Onde foi materializado |
|---|---|
| Competência imutável após fechamento | RFC-006 (processamento) — fechamento bloqueia alterações |
| Eventos como unidades de provento/desconto | RFC-004 (eventos) + `folha_pagamento.cbl` |
| Tabelas versionadas por competência | RFC-005 (tabelas) — `folha_config.dat` multi-versão |
| Holerite rastreável até a origem | RFC-007 (holerite) + `holerite_mostrar` |
| Mensal + complementar + 13º | RFC-006/010/011/013 — processamento, férias/13º e complementar |

## 8. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| crpalmarante | _autor_ | ✅ Aprovado | 11/08/2026 |
