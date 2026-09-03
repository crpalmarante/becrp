# RFC-012 — Afastamentos e Licenças

| Campo | Valor |
|---|---|
| **Título** | Afastamentos, licenças e suspensões do vínculo |
| **Autor** | crpalmarante |
| **Status** | ✅ Implementado (11/08/2026 — CRUD dedicado de afastamentos (incluir/alterar/excluir/aprovar/rejeitar), situação do vínculo "afastado" ao aprovar e retorno a "ativo" ao rejeitar (§4.1/Decisão 2); pró-rata por dias trabalhados no processamento (Decisão 3): licença não remunerada e excedente de auxílio-doença entram como faltas na competência; maternidade/paternidade pagamento integral; suspensão do período aquisitivo de férias com aviso quando afastamento aprovado >30 dias (Decisão 4); aba Afastamentos em folha.html; smoke_rfc012_afastamentos no CI) |
| **Data** | 01/08/2026 |
| **Versão** | 1.0.0 |
| **Área** | Conceitos — Processos |
| **Depende de** | RFC-001, RFC-002, RFC-006 |
| **Impacta** | RFC-006, RFC-010, RFC-011 |

---

## 1. Conceito

**Afastamento** é a situação em que o funcionário **mantém o vínculo** (RFC-002,
situação do vínculo: "afastado") mas fica **total ou parcialmente** sem
pagamento ou com pagamento por terceiro (ex.: INSS). **Não é desligamento.**

## 2. Tipos de Afastamento

| Tipo | Pagamento | Quem paga | Observação |
|---|---|---|---|
| Licença-maternidade | Integral | Empresa (ou INSS via salário-maternidade) | 120 dias + extensão |
| Licença-paternidade | Integral | Empresa | 5 dias |
| Auxílio-doença (acima de 15 dias) | Após o 15º dia | INSS | Empresa paga os 15 primeiros dias |
| Acidente de trabalho | Integral | Empresa (15 dias) + INSS | CAT obrigatória |
| Licença não remunerada | Nenhum | — | Suspensão temporária |
| Suspensão disciplinar | Nenhum | — | Conforme legislação |

## 3. Efeitos na Folha

1. **O afastamento suspende (total ou parcialmente) o pagamento** durante o
   período — os dias não trabalhados não geram salário.
2. **O cálculo usa os dias efetivamente trabalhados** do mês (pró-rata).
3. **Eventos fixos** (salário base, VT, plano de saúde) são recalculados
   proporcionalmente ou suspensos conforme o tipo de afastamento.
4. **Férias:** o período aquisitivo é suspenso após 30 dias de afastamento
   (ver RFC-010).
5. **13º:** meses com afastamento acima de 15 dias não contam como mês
   trabalhado (ver RFC-011).

## 4. Regras do Processo

1. **Afastamento não encerra o vínculo** — o funcionário permanece ativo no
   cadastro, apenas com situação "afastado".
2. **Todo afastamento tem data de início e (prevista) de término.**
3. **O retorno é registrado** — o processamento volta a pagar integralmente.
4. **Afastamento sem remuneração bloqueia o processamento de proventos** do
   período, mas mantém o cadastro.

## 5. Relação com a Rescisão

- Afastamento **não** é motivo de rescisão (RFC-003).
- Um funcionário afastado pode ser desligado (situação muda para "desligado").
- Verbas rescisórias consideram o período de afastamento conforme a lei.

## 6. Decisões Aprovadas

1. **Tipos cobertos na 1ª versão:** licença-maternidade, licença-paternidade,
   auxílio-doença (com 15 dias pagos pela empresa) e licença não remunerada. ✅ 01/08/2026
2. **Afastamento é uma situação do vínculo** (RFC-002), não um evento isolado —
   afeta o processamento inteiro da competência. ✅ 01/08/2026
3. **Pró-rata por dias trabalhados** no mês do afastamento. ✅ 01/08/2026
4. **Suspensão do período aquisitivo de férias após 30 dias.** ✅ 01/08/2026

## 7. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| crpalmarante | _autor_ | ✅ Aprovado | 11/08/2026 |

## 8. Implementação (rastreabilidade)

| Camada | Onde | Cobertura |
|---|---|---|
| COBOL | `cobol/programs/licenca.cbl` (CRUD + aprovação/rejeição/transição) | — |
| Bridge | `cobol_bridge.py`: `licenca_incluir/alterar/excluir`, `licencas_listar/pendentes/por_funcionario`, `licenca_aprovar/rejeitar/transitar`, `dias_afastamento_na_competencia`, `dias_afastamento_no_periodo` | — |
| Server | `server.py`: `GET /api/licencas`, `POST /api/licenca/incluir|alterar|excluir|aprovar|rejeitar`; pró-rata no `competencia/calcular`; aviso de suspensão aquisitiva em `ferias/calcular|incluir`; situação do vínculo ao aprovar/rejeitar | — |
| Tela | `pages/folha.html` (aba **Afastamentos**: CRUD, badges P/S/A/R/C, aprovar/rejeitar/excluir) | — |
| CI | `scripts/smoke_rfc012_afastamentos.py` (21 checks) registrado em `scripts/run_ci.py` | ✅ |
