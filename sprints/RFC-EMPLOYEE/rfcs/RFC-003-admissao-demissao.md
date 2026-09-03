# RFC-003 — Admissão e Demissão

| Campo | Valor |
|---|---|
| **Título** | Processos de Admissão e Demissão (Rescisão) |
| **Autor** | crpalmarante |
| **Status** | ✅ Implementado (09/08/2026 — rescisão com verbas/prazo/guarda do acerto; desligar/reativar com status; bloqueio de processamento de desligado §3.4.1; bloqueio de admissão com exame admissional vencido §2.3.3) |
| **Data** | 31/07/2026 |
| **Versão** | 1.0.0 |
| **Área** | Conceitos — Processos |
| **Depende de** | RFC-001, RFC-002 |
| **Impacta** | RFC-006 |

---

## 1. Conceito

**Admissão** é o processo que cria o vínculo empregatício e o cadastro inicial do
funcionário. **Demissão (rescisão)** é o processo que encerra o vínculo e calcula
o acerto de todas as verbas devidas. Ambos são processos de negócio com etapas,
documentos e regras próprias — independentes de tecnologia.

## 2. Processo de Admissão

### 2.1 Etapas
1. **Triagem e seleção** (fora do sistema — contratação).
2. **Coleta de documentos** (ver 2.2).
3. **Exame médico admissional** (obrigatório pela legislação).
4. **Cadastro do funcionário** no sistema (RFC-002).
5. **Assinatura do contrato de trabalho** e registro na CTPS.
6. **Configuração de eventos e benefícios** (optante VT, VR, plano de saúde,
   jornada) — ver RFC-004.
7. **Liberação para inclusão na próxima folha.**

### 2.2 Documentos típicos
- Documento de identidade (RG) e CPF
- CTPS (física ou digital)
- Comprovante de residência
- Foto 3x4
- Título de eleitor
- PIS/PASEP
- Certidão de nascimento/casamento
- Comprovante de escolaridade
- Dados bancários (banco, agência, conta)
- Declaração de dependentes (para IRRF/salário-família)
- Declaração de opção ou não pelo vale-transporte

### 2.3 Regras da admissão
1. **Data de admissão é o início do vínculo** e define a primeira competência em
   que o funcionário entra na folha.
2. **O cadastro só pode ser liberado para a folha** quando os dados obrigatórios
   (RFC-002) estiverem completos.
3. **Exame admissional vencido bloqueia a admissão** (ou gera alerta conforme
   política da empresa).

## 3. Processo de Demissão (Rescisão)

### 3.1 Motivos de desligamento
| Tipo | Descrição |
|---|---|
| Sem justa causa (empregador) | Empresa encerra o vínculo sem justificativa legal |
| Com justa causa (empregado) | Faltas graves do empregado previstas em lei |
| Pedido de demissão (empregado) | Empregado encerra por iniciativa própria |
| Acordo entre as partes | Fim do vínculo por consenso (regras específicas) |
| Término de contrato | Contrato por prazo determinado que chega ao fim |

### 3.2 Verbas rescisórias típicas (acerto)
| Verba | Condição | Regra geral |
|---|---|---|
| Saldo de salário | Sempre | Dias trabalhados no mês da saída |
| Aviso prévio | Trabalhado ou indenizado | 30 dias + 3 por ano de serviço (limitado) |
| Férias vencidas | Quando existentes | Período aquisitivo completo + 1/3 |
| Férias proporcionais | Sempre | Período proporcional + 1/3 |
| 13º proporcional | Sempre | Meses trabalhados no ano / 12 |
| Multa FGTS | Sem justa causa / acordo | Percentual sobre o saldo do FGTS |
| Adicionais não pagos | Quando devidos | Noturno, insalubridade, etc. |

### 3.3 Etapas
1. **Registro do desligamento** com data e motivo.
2. **Cálculo do acerto** (verbas + saldo) — regras de cálculo no RFC-006.
3. **Exame médico demissional** (obrigatório pela legislação).
4. **Homologação** (quando exigida — sindicato ou órgão competente).
5. **Geração de guias** (FGTS, GRRF, seguro-desemprego, CAGED).
6. **Pagamento das verbas rescisórias** dentro do prazo legal.
7. **Baixa na CTPS** e encerramento do cadastro (status "desligado").

### 3.4 Regras da rescisão
1. **Data de demissão bloqueia novos processamentos** para o funcionário.
2. **O acerto é uma folha especial** da competência da saída — não pode ser
   alterada após o pagamento.
3. **Prazo de pagamento é obrigatório** (10 dias corridos após o desligamento
   sem aviso prévio; datas específicas com aviso trabalhado).
4. **Toda verba do acerto deve ser rastreável** até o evento correspondente
   (RFC-004) — nada de valores avulsos.

## 4. Decisões Aprovadas

1. **Só valores para conferência** — a 1ª versão calcula e exibe os valores das
   guias (FGTS/GRRF, seguro-desemprego, CAGED); a emissão oficial fica para
   evolução futura. ✅ 31/07/2026
2. **Aviso prévio trabalhado com horário reduzido** — o acerto considera a
   redução de 2h/dia ou 7 dias corridos; o funcionário permanece no
   processamento durante o aviso. ✅ 31/07/2026
3. **Sem férias coletivas** na 1ª versão. ✅ 31/07/2026

## 5. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| crpalmarante | autor | ✅ Aprovado | 10/08/2026 |

## 6. Rastreabilidade da Implementação

| Item | Onde | Verificação |
|---|---|---|
| Cálculo do acerto (decisões 1–4) | `folha_pagamento.cbl` — `rescisao-calcular/incluir` | `smoke_rfc003_rescisao.py` (54 checks) |
| Badge **EM DOBRO** (férias vencidas) na tabela | `pages/folha.html` — `carregarRescisoes` | `check_render_rescisao_node.js` (RENDER OK) |
| Toast de alerta ao registrar vencidas | `pages/folha.html` — `calcularRescisao` | `check_render_rescisao_node.js` (RENDER OK) |
| Cenário visual (2 rescisões C/P para navegador) | `scripts/cenario_rescisao_browser.py` | browser-use (badge + botões por estado) |

> **Bug corrigido em 11/08/2026** — o loop de `READ` do `gravar-rescisao`
> (para calcular o próximo id) sobrescrevia os campos calculados `re-*` com o
> último registro do arquivo; a 2ª+ rescisão gravava saldo/férias/13º/FGTS do
> registro anterior. Fix: backup `ws-re-backup` do registro calculado antes do
> loop e restauração antes do `WRITE`. Coberto pela seção 8 do
> `smoke_rfc003_rescisao.py` (11 checks de regressão — 2 rescisões em sequência
> com valores distintos não herdam).
