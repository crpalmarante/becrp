# RFC-015 — Diagrama do Fluxo de Fechamento da Competência

> Diagrama do **fluxo de fechamento** da competência (RFC-015 §3), da entrada
> (competência calculada/validada) até o registro do pagamento e a competência
> encerrada — com os papéis do RFC-009 nas transições e os relatórios do
> RFC-015 §2 gerados no fechamento.
> **Diagrama validado** com a engine Mermaid v10.9.1 (renderização confirmada
> no navegador, sem erros de sintaxe).

---

## 1. Diagrama (Mermaid flowchart)

````markdown
```mermaid
flowchart TD
    %% ═══════════ ENTRADA ═══════════
    CALC["Competência calculada / validada<br>(RFC-006 · estados Calculada → Validada)"] --> VERIF

    %% ═══════════ 5 VERIFICAÇÕES DE CONSISTÊNCIA (RFC-015 §3.1) ═══════════
    subgraph VERIF["① Verificações de consistência — pré-fechamento (RFC-015 §3.1)"]
        direction TB
        V1["1 · Líquido = proventos − descontos, para todos os funcionários (RFC-007)"]
        V2["2 · Nenhum valor sem origem rastreável (evento + referência + cadastro)"]
        V3["3 · Totais por departamento conferem com a soma dos holerites"]
        V4["4 · Encargos calculados para a competência (RFC-014)"]
        V5["5 · Nenhum funcionário com dados obrigatórios pendentes (RFC-002)"]
    end

    VERIF --> DEC{Verificações<br>passaram?}
    DEC -- "Não → corrigir<br>e reverificar" --> VERIF
    DEC -- "Sim" --> CONF["Conferência<br>(papel: Conferente)"]

    %% ═══════════ ETAPAS DO FECHAMENTO (RFC-015 §3.2) ═══════════
    CONF --> APROV["Aprovação<br>(papel: Aprovador)"]
    APROV --> FECH["Fechamento definitivo<br>→ competência FECHADA<br>(imutável — RFC-006)"]

    %% ═══════════ RELATÓRIOS GERADOS NO FECHAMENTO (RFC-015 §2) ═══════════
    subgraph RELAT["Relatórios gerados no fechamento (RFC-015 §2)"]
        direction TB
        R1["Folha por departamento<br>(Gestão)"]
        R2["Total de encargos<br>(Contabilidade)"]
        R3["Resumo por funcionário<br>(Tesouraria)"]
        R4["Conferência mês a mês<br>(Conferente)"]
    end

    FECH --> RELAT
    FECH --> PAGA["Registro do pagamento<br>(papel: Tesouraria)<br>→ estado PAGA"]
    RELAT --> PAGA
    PAGA --> FIM(["Competência encerrada<br>· valores imutáveis<br>· correções só via folha complementar (RFC-013)"])

    %% ═══════════ ESTILOS ═══════════
    classDef entrada fill:#6b21a8,stroke:#d8b4fe,color:#ffffff,stroke-width:2px;
    classDef check fill:#0e7490,stroke:#67e8f9,color:#ffffff,stroke-width:2px;
    classDef decisao fill:#b45309,stroke:#fcd34d,color:#ffffff,stroke-width:2px;
    classDef etapa fill:#1d4ed8,stroke:#93c5fd,color:#ffffff,stroke-width:2px;
    classDef fech fill:#9f1239,stroke:#fda4af,color:#ffffff,stroke-width:2px;
    classDef paga fill:#15803d,stroke:#86efac,color:#ffffff,stroke-width:2px;
    classDef rel fill:#6b21a8,stroke:#d8b4fe,color:#ffffff,stroke-width:2px;
    classDef fim fill:#374151,stroke:#9ca3af,color:#ffffff,stroke-width:2px;

    class CALC entrada;
    class V1,V2,V3,V4,V5 check;
    class DEC decisao;
    class CONF,APROV etapa;
    class FECH fech;
    class PAGA paga;
    class R1,R2,R3,R4 rel;
    class FIM fim;

    style VERIF fill:#ecfeff,stroke:#06b6d4,stroke-width:2px;
    style RELAT fill:#faf5ff,stroke:#a855f7,stroke-width:2px;
```
````

---

## 2. Legenda (cores)

| Cor | Significado | Nós |
|---|---|---|
| 🟣 **Roxo** | **Entrada** — competência já calculada/validada (RFC-006) | CALC |
| 🔵 **Azul-ciano** | **Verificações de consistência** pré-fechamento (RFC-015 §3.1) | V1–V5 |
| 🟠 **Âmbar** | **Decisão** — verificações passaram? | DEC |
| 🔵 **Azul** | **Etapas do fechamento** com papel dono (RFC-009) | CONF, APROV |
| 🔴 **Vermelho** | **Fechamento definitivo** — estado FECHADA, imutável | FECH |
| 🟢 **Verde** | **Registro do pagamento** — estado PAGA (Tesouraria) | PAGA |
| 🟣 **Roxo (relatórios)** | **Relatórios** gerados no fechamento (RFC-015 §2) — mesmo tom da entrada, diferenciados pelo subgraph | R1–R4 |
| ⚫ **Cinza** | **Fim** — competência encerrada, valores imutáveis | FIM |

> Os **subgraphs** têm fundos em tons claros para agrupar os nós: `VERIF` em
> ciano claro (`#ecfeff`) e `RELAT` em roxo claro (`#faf5ff`).

---

## 3. Referência Cruzada ao RFC-015

| Elemento do diagrama | Fonte no RFC-015 |
|---|---|
| Entrada (Calculada → Validada) | §1 + decisão 4 (§5) — fechamento só com validação prévia (estados sequenciais do RFC-006) |
| 5 verificações de consistência | §3.1 (itens 1–5) |
| Decisão "Não → corrigir e reverificar" | §3.1 — verificações são pré-fechamento |
| Conferência (Conferente) | §3.2, etapa 1 (papel: RFC-009) |
| Aprovação (Aprovador) | §3.2, etapa 2 |
| Fechamento definitivo → FECHADA (imutável) | §3.2, etapa 3 + regra 4 (§4) |
| Relatórios (R1–R4) | §2 — tabela dos 4 relatórios da 1ª versão |
| Registro do pagamento (Tesouraria → PAGA) | §3.2, etapa 4 |
| Competência encerrada / correções via RFC-013 | §4, regra 4 |

### Notas de fidelidade

1. **Ordem "relatórios antes do pagamento"** — o RFC-015 não explicita essa
   posição; ela vem do RFC-006 §3.3 (passo 16: gerar holerites/relatórios
   antes de registrar o pagamento). Fica registrado para não parecer invenção
   do diagrama.
2. **Papéis nas transições** — Conferente, Aprovador e Tesouraria vêm do
   RFC-009 (separação de funções: Aprovador ≠ Operador).
3. **Status do RFC-015** — está como **Draft (em revisão)** (v1.0.0); o fluxo
   reflete o documento atual.

---

*Diagrama validado com Mermaid v10.9.1 — sem erros de sintaxe. Gerado em
01/08/2026 a partir do RFC-015 (v1.0.0).*
