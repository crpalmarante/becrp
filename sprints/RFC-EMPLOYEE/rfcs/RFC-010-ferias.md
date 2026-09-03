# RFC-010 — Férias

| Campo | Valor |
|---|---|
| **Título** | Processo de férias: aquisição, gozo e pagamento |
| **Autor** | crpalmarante |
| **Status** | ✅ Implementado (10/08/2026 — cálculo no COBOL (padrão rescisão) com alerta e salário em dobro para vencidas §2.1/Decisão 4; dobro também na rescisão §6 (RFC-003); aviso de vencidas no RH Dashboard; badges VENCIDA/EM DOBRO + toasts; 4 checks Node de render no CI) |
| **Data** | 01/08/2026 |
| **Versão** | 1.0.0 |
| **Área** | Conceitos — Processos |
| **Depende de** | RFC-001, RFC-002, RFC-004, RFC-006 |
| **Impacta** | RFC-003, RFC-006, RFC-007, RFC-012 |

---

## 1. Conceito

**Férias** é o direito do funcionário a um período de descanso remunerado após
cada **período aquisitivo** de 12 meses de trabalho. O pagamento inclui o
salário do período + **1/3 constitucional** (evento 10 do RFC-004) e as médias
das verbas variáveis (horas extras, comissões, adicionais).

## 2. Períodos

| Período | Definição |
|---|---|
| **Aquisitivo** | 12 meses de trabalho que geram o direito às férias |
| **Concessivo** | 12 meses seguintes ao aquisitivo em que o empregador deve conceder as férias |
| **Vencidas** | Férias não concedidas dentro do período concessivo — pagas **em dobro** |

### 2.1 Regras dos períodos
1. **Período aquisitivo suspenso por afastamentos** acima de 30 dias (auxílio-
   doença, licenças — ver RFC-012).
2. **Férias vencidas** geram alerta e pagamento em dobro.
3. **Férias proporcionais** (rescisão) são tratadas no RFC-003.

## 3. Etapas do Processo

1. **Programação** — escolha do período de gozo (datas de início e fim).
2. **Aviso de férias** — comunicação ao funcionário com antecedência mínima
   (proposta: 30 dias).
3. **Cálculo** — base = salário + médias de verbas variáveis do período
   aquisitivo + 1/3 constitucional (RFC-004, evento 10).
4. **Pagamento** — até 2 dias antes do início do gozo.
5. **Registro do gozo** — competência de férias própria (RFC-006, seção 6).

## 4. Parcelamento

A legislação permite dividir as férias em até **3 períodos**, com regras de
proporção mínima. Decisão proposta: **parcela única na 1ª versão**, com
parcelamento como evolução futura.

## 5. Abono Pecuniário

O funcionário pode **vender até 1/3 dos dias** de férias (abono pecuniário).
Decisão proposta: **incluir na 1ª versão** — é um evento de provento com
incidência própria.

## 6. Férias na Rescisão

- **Vencidas** + 1/3 → pagas no acerto (RFC-003).
- **Proporcionais** + 1/3 → pagas no acerto (RFC-003).
- Não há gozo na rescisão — apenas pagamento.

## 7. Decisões Aprovadas

1. **Parcela única na 1ª versão** — parcelamento em 3 períodos fica para
   evolução futura. ✅ 01/08/2026
2. **Abono pecuniário incluso** — venda de até 1/3 dos dias, como evento de
   provento. ✅ 01/08/2026
3. **Aviso mínimo de 30 dias** antes do gozo. ✅ 01/08/2026
4. **Férias vencidas pagas em dobro** com alerta automático. ✅ 01/08/2026
5. **Pagamento até 2 dias antes do início** do gozo. ✅ 01/08/2026

## 8. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| crpalmarante | autor | ✅ Aprovado | 10/08/2026 |
