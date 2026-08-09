# RFC-001 — Arquitetura Geral do ERP COBOL ⚠️ ARQUIVADO

> **⚠️ Documento HISTÓRICO — não faz mais parte do conjunto de RFCs.**
> As RFCs atuais (em `../rfcs/`) tratam somente de **processos e conceitos**
> (RFC-001-conceitos-gerais … RFC-007-holerite) e não contêm tecnologia.
> Este documento técnico foi arquivado em 31/07/2026 por decisão do autor.

| Campo | Valor |
|---|---|
| **Título** | Arquitetura geral do ERP caseiro (COBOL + Python + PostgreSQL) — HISTÓRICO |
| **Autor** | crpalmarante |
| **Status** | 🗄️ Arquivado |
| **Data** | 31/07/2026 |
| **Versão** | 1.0.0 |
| **Área** | Arquitetura |
| **Depende de** | — (RFC fundador) |
| **Impacta** | RFC-002 (Web), RFC-003 (Frontend), RFC-004 (Dados), RFC-005 (Folha), RFC-006 (COBOL) |

---

## 1. Objetivo

Definir a arquitetura fundamental do ERP 100% caseiro: stack, camadas, fluxo de
dados, princípios de isolamento e a regra crítica de integração COBOL↔Python
(`libcob`), servindo de base para todos os demais RFCs.

## 2. Contexto

- Construir um ERP **do zero**, sem frameworks, sem bibliotecas externas e sem CDN.
- Backend: **COBOL** (motor de regras de negócio) + **Python** (web/orquestração) + **PostgreSQL**.
- Frontend: **HTML + CSS + JS puro**, 100% escrito por nós.
- Módulo MVP: **Folha de Pagamento**.
- Restrição permanente: **nada** de Bootstrap, jQuery, React, Vue.js, Angular ou
  qualquer dependência externa além de PostgreSQL, GnuCOBOL, `gcc`, Python stdlib
  e `psycopg` (ver `PLAN_ERP.md`).

## 3. Decisão

Adotar a **arquitetura em camadas** com **COBOL como motor de negócio** invocado
via `ctypes` (arquitetura 1 da pesquisa). Processamento pesado em **subprocess
isolado** é a **recomendação** para a folha em lote, mas permanece **pendente de
aprovação** (ver seção 8).

```
┌──────────────────────────────────────────────────────┐
│  FRONTEND  HTML + CSS + JS puro (fetch API, SPA*)    │
└───────────────────────┬──────────────────────────────┘
                        │ HTTP/JSON
┌───────────────────────▼──────────────────────────────┐
│  WEB LAYER  Python stdlib (ThreadingHTTPServer)      │
│  • rotas · sessões (cookie assinado c/ hmac)          │
│  • validação · orquestração · persistência            │
└───────┬───────────────────────────────┬──────────────┘
        │ ctypes (startup, 1x)          │ psycopg + camada própria
        │                               │
        │  ┌─ subprocess (batch)** ─┐   │
        ▼  ▼                        │    ▼
┌───────▼───────────────┐          │    ┌────────▼───────────────┐
│  COBOL (.so)          │──────────┘    │  PostgreSQL            │
│  Núcleo financeiro    │               │  dados da folha        │
└───────────────────────┘               └────────────────────────┘
```
\* SPA vs. formulários clássicos: **pendente** (ver seção 8).
\** subprocess para batch pesado: **recomendação pendente** (ver seção 8).

### 3.1 Princípios

1. **COBOL nunca fala HTTP** — é chamado pelo Python, recebe dados tipados,
   retorna resultados tipados. Responsabilidade: cálculo/regra pura.
2. **Python nunca duplica regra fiscal** — orquestra e persiste, não recalcula
   INSS/IRRF (isso é do COBOL).
3. **PostgreSQL é a única fonte de verdade** — ambos os lados leem/gravam via
   nossa camada de dados (Python), ou via SQL puro do COBOL quando em batch.
4. **Frontend não conversa com banco** — só via API JSON do nosso servidor.
5. **Zero dependência externa em runtime** além de `psycopg`.

## 4. Alternativas Consideradas

| # | Alternativa | Prós | Contras | Veredito |
|---|---|---|---|---|
| 1 | **Python (web) → ctypes → COBOL .so** | Alta perf, sem overhead, regras isoladas | Crash de COBOL derruba o worker; gestão de ponteiros | ✅ **Escolhida** |
| 2 | Python (web) → subprocess COBOL CLI | Isolamento total | Overhead de spawn/marshalling | ⚠️ Híbrido p/ batch |
| 3 | COBOL → PostgreSQL direto (GixSQL/ESQL) | COBOL dono do banco | Acoplamento, teste difícil | ❌ Não escolhida p/ MVP |
| 4 | COBOL como serviço HTTP próprio | Isolamento | Mais infra, contrato extra | ❌ Complexidade desnecessária |

## 5. Detalhes Técnicos

### 5.1 Regra crítica — ciclo de vida do `libcob`

- Inicializar `libcob.cob_init(0, None)` **uma única vez** no startup do processo.
- Manter os `.so` carregados em memória durante toda a vida do worker.
- **Nunca** carregar/descarregar `.so` dentro de handler de requisição
  (risco de `SIGSEGV: attempt to reference unallocated memory`).
- Em caso de crash: worker pool respawna o processo automaticamente.

### 5.2 Mapeamento de tipos COBOL ↔ Python

- `PIC` decimais (especialmente `COMP-3`) → structs `ctypes` intermediárias.
- Nunca passar `float` diretamente para campo monetário sem conversão explícita.
- Valores monetários: representar como inteiro de centavos na borda ou struct
  com escala documentada (detalhe no RFC-006).

### 5.3 Separação de pastas

```
erp_cobol/
├── rfcs/       # este e os demais RFCs
├── web/        # servidor HTTP, rotas, sessão, estáticos
├── core/       # lógica de aplicação Python (orquestração)
├── cobol/      # fontes .cbl + .so (PAYCALC, TAXCALC…)
├── db/         # SQL puro, migrations, seed de tabelas fiscais
├── static/     # HTML/CSS/JS (100% nosso)
└── tests/      # unittest Python + testes isolados do COBOL
```

## 6. Requisitos Não-Funcionais

- **Rastreabilidade:** cada decisão deste RFC vira uma subseção em RFCs filhos.
- **Testabilidade:** o núcleo COBOL deve ser testável isoladamente (sem web, sem banco).
- **Segurança:** sessão com cookie assinado (hmac), senhas com hash próprio
  (detalhe no RFC-002).
- **Portabilidade:** Linux (GnuCOBOL 3.2+, PostgreSQL, Python 3.x).

## 7. Riscos

| Risco | Mitigação |
|---|---|
| Crash COBOL derruba worker | Worker pool + subprocess p/ batch |
| Perda de precisão em decimais | Structs intermediárias + testes de arredondamento |
| SEGFAULT por recarregar `.so` | Regra 5.1 obrigatória |
| Escopo da folha crescer | MVP enxuto (INSS/IRRF/horas) |

## 8. Decisões em Aberto

1. **Processamento pesado da folha** — recomendação: híbrido (ctypes para
   cálculos rápidos no processo web; **subprocess isolado** para a folha em lote
   com muitos funcionários). Pendente de aprovação.
2. **SPA vs. formulários clássicos** — as seções assumem SPA como recomendação.

## 9. Histórico de Versões

| Versão | Data | Mudança |
|---|---|---|
| 1.0.0 | 31/07/2026 | Criação do RFC |

## 10. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| _em aberto_ | _autor_ | ⏳ | — |

---

*Aprovado ⇒ os RFCs filhos (002–006) detalham cada camada.*
