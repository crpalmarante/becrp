# RFC-Payroll/004 — Detalhamento Contábil por Venda de Origem (Evento 7)

| Campo | Valor |
|---|---|
| **Título** | Detalhamento contábil por venda de origem no lançamento da comissão (evento 7): camada analítica de ligação entre o lançamento e a venda de origem |
| **Autor** | crpalmarante |
| **Status** | ✅ Aprovado |
| **Data** | 05/08/2026 |
| **Versão** | 1.1.0 |
| **Área** | Integração contábil — Folha (comissão — rastreabilidade analítica) |
| **Depende de** | RFC-Payroll/003 (contabilização da comissão — evento 7), RFC-Payroll/001 (modelo de dados), RFC-Payroll/002 (fluxos de contabilização); RFC-COMISSION/005 (detalhe analítico `commission_details`); RFC-015 (projeto — relatório por venda de origem); módulos `eh_hr_payroll` + `account` (plataforma) |
| **Impacta** | RFC-015 (projeto — relatório integrado ao lançamento); RFC-COMISSION/005 (detalhe analítico consumido pelo lançamento); RFC-Payroll/005+ (evoluções: centro de custo, rateio, faixas de meta) |

> **Natureza deste documento:** materializa a **evolução declarada** no
> RFC-Payroll/003 §7 — o **detalhamento contábil por venda de origem no
> lançamento** da comissão. Hoje (RFC-003 §8 decisão 5) o lançamento é
> **consolidado por regra** e o detalhe analítico por venda vive apenas no
> RFC-COMISSION/005 §7 (`commission_details`), **fora do lançamento contábil**.
> O RFC-004 adiciona uma **camada analítica de ligação** que leva a
> rastreabilidade da venda de origem **para dentro do lançamento** — **sem
> alterar as linhas do razão** nem os algoritmos de geração/estorno
> (RFC-Payroll/002 §3/§4). Para isso, **evolui pontualmente a decisão 1 do
> RFC-Payroll/001** ("sem models próprios", ✅ aprovada): a tabela de ligação é
> o **único model próprio** do módulo — a contabilização de base (001/002/003)
> permanece sem models/migrations. A **v1.1.0** aprova as decisões da §8
> (✅ 05/08/2026) e marca o documento como **✅ Aprovado**.

---

## 1. Objetivo

1. **Rastrear cada venda de origem até o lançamento contábil da comissão**: da
   linha da regra do evento 7 no `account.move` ao `commission_details`
   (RFC-COMISSION/005 §3.3) e vice-versa;
2. **Preservar a mecânica da série**: o razão permanece **consolidado por regra**
   (decisão 5 do RFC-003) e os algoritmos de **geração** (RFC-002 §3) e
   **estorno** (RFC-002 §4) **não mudam**;
3. **Integrar o relatório analítico ao lançamento**: o RFC-015 §2.1 (comissões
   por venda de origem) permanece sobre `commission_details`, agora alcançável a
   partir do lançamento contábil (razão ↔ venda, nos dois sentidos);
4. Garantir a **consistência** (soma das ligações = valor da linha = apurado
   congelado da competência) e a **imutabilidade** da camada analítica.

## 2. Conceito

| Conceito | Definição |
|---|---|
| **Camada analítica de ligação** | Tabela do módulo que liga a **linha da comissão no lançamento** (`account.move.line` da regra 7) aos **itens apurados de origem** (`commission_details`, db/017) — o detalhe por venda fica disponível no lançamento **sem virar linha adicional do razão**. |
| **Venda de origem** | A venda do PDV (`pos_sales`) cujo item apurado gerou parte do valor da comissão — granularidade já existente no RFC-COMISSION/005 §7. |
| **Razão consolidado por regra** | As linhas do lançamento continuam como no RFC-003 (§6): um par débito/crédito por regra, agrupado por categoria — a decisão 5 do RFC-003 é **preservada**. |
| **Rastreabilidade nos dois sentidos** | Do lançamento (razão) para as vendas (ligações → `commission_details`) e das vendas para o lançamento (vínculo reverso na consulta do RFC-015 §2.1). |
| **Única exceção a "sem models próprios"** | A tabela de ligação é o **único modelo próprio** do módulo (decisão 1 do RFC-001 preservada em todo o resto): justificada porque `account.move.line` não referencia vendas do PDV e gravar uma linha do razão por venda inflaria o livro-razão. |

## 3. Origem do detalhe — da venda ao lançamento

1. O PDV apura a comissão **por item** (`commission_details` — venda, item,
   funcionário, produto, taxa, valor — RFC-COMISSION/005 §3.3) e **congela** o
   total por funcionário × competência (`commission_settlements`, §3.5);
2. O total congelado entra na folha pelo **evento 7** (RFC-COMISSION/001 §5
   regra 4) e vira a linha da regra de comissão no contracheque (RFC-003 §3);
3. Ao **gerar o lançamento** (RFC-002 §3), o módulo liga a **linha da regra 7**
   aos **itens apurados** da competência — uma ligação por `commission_detail_id`
   (§4);
4. Resultado: a linha consolidada da comissão no razão (2.000,00 — ex. §6)
   expande analiticamente nas vendas de origem (500 + 700 + 800), sem mudar o
   lançamento.

## 4. Modelo de Dados — camada analítica de ligação (única exceção)

> **Não há campos novos em `account.move`/`account.move.line` nem mudança nos
> algoritmos**; a rastreabilidade usa **uma tabela própria do módulo** —
> `commission_move_line_detail` — a **única exceção** à decisão 1 do
> RFC-Payroll/001 ("sem models próprios"), justificada pela granularidade
> analítica por venda (inexistente nos modelos da plataforma). A tabela é
> criada pelo **model ORM do módulo** (como qualquer model da plataforma) —
> **sem migration SQL em `db/`** (padrão da série).

| Coluna | Tipo | Regra | Definição |
|---|---|---|---|
| id | BIGSERIAL | PK | Identificador da ligação |
| move_line_id | BIGINT | NOT NULL FK → `account.move.line` | **Linha da regra 7** (comissão) no lançamento — débito 3.1.03 / crédito 2.1.04 |
| commission_detail_id | BIGINT | NOT NULL FK → `commission_details` (db/017) | **Item apurado de origem** — um detalhe por item (UNIQUE abaixo) |
| sale_id | BIGINT | NOT NULL | Venda de origem (`pos_sales.id`) — **denormalizada** para consulta sem join |
| amount | NUMERIC(14,2) | NOT NULL CHECK (amount > 0) | Valor da comissão do item apurado (positivo) |
| UNIQUE (commission_detail_id) | — | — | **Idempotência**: um item apurado ligado a uma única linha do lançamento (decisão 3) |

> **Invariantes** (padrão do projeto — imutabilidade e consistência):
> 1. `sum(amount)` por `move_line_id` = **valor da linha da regra 7** no
>    lançamento (e = total congelado em `commission_settlements` da competência);
> 2. As ligações são **imutáveis após a geração** (sem UPDATE/DELETE/TRUNCATE —
>    a reversão acontece pelo estorno do lançamento, RFC-002 §4, nunca por
>    correção pontual);
> 3. Escrita apenas pelo **fluxo de geração do módulo** (contabilização) — fora
>    dele, sem escrita direta.
> 4. **Congelamento do apurado preservado**: uma venda cancelada **após** o
>    fechamento da competência (RFC-COMISSION/005 §3.5) não altera
>    retroativamente o lançamento — as ligações apontam para os detalhes
>    congelados; a reversão acontece pelo mecanismo de **estorno** do
>    RFC-Payroll/002 §4, nunca por correção pontual da ligação.
> 5. **Consistência da denormalização**: `sale_id` = `commission_details.sale_id`
>    da ligação (padrão de consistência do projeto — db/015 invariante 2,
>    db/017 invariante 3).

## 5. Algoritmos — geração da ligação e estorno herdado

**Geração da ligação** (executada dentro da geração do lançamento — RFC-002 §3,
somente para a regra do evento 7):

```
função gerar_ligacoes(move, contracheque):
    # só para a regra do evento 7 (comissão) — demais regras sem ligação
    linha_comissao = move.linhas[regra evento 7]
    apurado = commission_details por (funcionário, competência)      # db/017
    para cada detalhe em apurado:                                    # um por item
        grava commission_move_line_detail(move_line_id=linha_comissao,
                                          commission_detail_id=detalhe.id,
                                          sale_id=detalhe.sale_id,
                                          amount=detalhe.commission_value)
    # invariante 1: soma das ligações = valor da linha (senão, falha a geração)
```

- **Idempotência** — a `UNIQUE (commission_detail_id)` garante que a regeração
  (retrofit via botão manual, RFC-001 §3.3) não duplica ligações; o `move_id`
  único por contracheque (RFC-001 §8 decisão 5) já protege o lançamento;
- **Estorno herdado** (RFC-002 §4) — o estorno **não cria ligações novas**: as
  linhas do estorno herdam a rastreabilidade via `reversed_entry_id` →
  lançamento original → ligações; lançamento em rascunho cancelado descarta as
  ligações junto (nada no razão). Após estorno **postado**, as ligações
  permanecem no lançamento original (e o `move_id` não vazio já impede nova
  geração — decisão 5 do RFC-001); o descarte de ligações só acontece no
  caminho **rascunho cancelado** (regeneração sem conflito de UNIQUE);
- **Relatório** (RFC-015 §2.1) — permanece sobre `commission_details`, agora com
  o **vínculo reverso** para o lançamento (consulta por competência retorna o
  `move_id`/`move_line_id` da comissão) — rastreabilidade razão ↔ venda.

## 6. Exemplo de rastreabilidade

Comissão do evento 7 = **2.000,00** (mesma folha do RFC-003 §6 — salário 10.000
+ comissão 2.000 + encargos = 16.400 débito = 16.400 crédito, **razão
inalterado**):

| Item apurado (db/017) | Venda de origem | Valor |
|---|---|---|
| `commission_detail` #1 | Venda 1001 | 500,00 |
| `commission_detail` #2 | Venda 1002 | 700,00 |
| `commission_detail` #3 | Venda 1003 | 800,00 |
| **Total da linha da regra 7** | (débito 3.1.03 / crédito 2.1.04) | **2.000,00** |

> A linha da comissão no lançamento (2.000,00) recebe **3 ligações** (500 + 700 +
> 800). Consulta de rastreabilidade: do `account.move.line` → vendas 1001/1002/1003
> (código, data, produto, taxa — RFC-015 §2.1); da venda → o lançamento
> (`move_id`) da competência. **Lançamento continua equilibrado e consolidado
> por regra** — nada muda no razão nem nos algoritmos de 001/002/003.

## 7. Escopo Fora Deste RFC

- **Rateio por centro de custo / departamento** (contas diferentes por unidade
  de negócio) → evolução (RFC-Payroll/005+).
- **Comissão por faixas de meta** no lançamento (mecânica de tabelas internas do
  RFC-005 do projeto) → evolução.
- **Moeda estrangeira** e câmbio nos lançamentos → evolução.
- **Divisão de venda entre múltiplos vendedores** na ligação analítica →
  evolução (divisão é regra de apuração — RFC-COMISSION/005 §8).
- Detalhes do **livro-razão** e fechamento contábil (projeto central) → RFC-006
  (projeto), RFC-007 (projeto) e módulos contábeis da plataforma.

## 8. Decisões

1. **Razão consolidado preservado** — as linhas do lançamento não mudam: o
   detalhamento por venda é uma **camada analítica de ligação**, não linhas
   adicionais do razão (preserva a decisão 5 do RFC-003 e a mecânica do
   RFC-002 §3) (§2/§4/§5). ✅ 05/08/2026
2. **Tabela de ligação — única exceção a "sem models próprios"** —
   `commission_move_line_detail` (move_line_id → linha da regra 7;
   commission_detail_id → item apurado; sale_id denormalizado; amount) —
   justificada porque `account.move.line` não referencia vendas do PDV e linhas
   por venda no razão inflariam o livro-razão (§4). ✅ 05/08/2026
3. **Geração idempotente e validada** — uma ligação por `commission_detail_id`
   (UNIQUE) gravada na geração do lançamento; invariante: soma das ligações =
   valor da linha = apurado congelado da competência; falha bloqueia a geração
   (§4/§5). ✅ 05/08/2026
4. **Estorno herdado** — o estorno (RFC-002 §4) não cria ligações: a
   rastreabilidade das linhas do estorno segue `reversed_entry_id` → original →
   ligações; rascunho cancelado descarta as ligações (§5). ✅ 05/08/2026
5. **Escopo restrito à comissão (evento 7)** — a ligação analítica por venda
   existe apenas para a regra de comissão; as demais regras permanecem
   consolidadas por regra, sem detalhe de origem (§5). ✅ 05/08/2026
6. **Relatório integrado ao lançamento** — RFC-015 §2.1 permanece sobre
   `commission_details`, agora com o vínculo reverso para o lançamento (razão ↔
   venda nos dois sentidos) (§5). ✅ 05/08/2026

## 9. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| crpalmarante | autor | ✅ | 05/08/2026 |
