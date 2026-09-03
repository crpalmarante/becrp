# RFC-015 — Relatórios e Fechamento

| Campo | Valor |
|---|---|
| **Título** | Relatórios gerenciais e fechamento da competência |
| **Autor** | crpalmarante |
| **Status** | ✅ Implementado (11/08/2026 — relatório de encargos HTML imprimível (CSS print → PDF) gerado no fechamento (§2/§4 regra 2) com **anexo da trilha de auditoria** da competência (RFC-009 §5, imutável — quem/quando/antes/depois/tabelas); verificações de consistência via estados sequenciais (RFC-006) e separação de funções (RFC-009 §4.2); coberto por smoke_rfc009_auditoria (anexo via HTTP) + review_tela_folha no CI) |
| **Data** | 01/08/2026 |
| **Versão** | 1.1.0 |
| **Área** | Conceitos — Saídas |
| **Depende de** | RFC-006, RFC-007, RFC-014, RFC-COMISSION/005 (apuração — fonte do relatório de comissões) |
| **Impacta** | RFC-006, RFC-009 |

---

## 1. Conceito

**Relatórios** são visões consolidadas da folha para gestão, contabilidade e
tesouraria. **Fechamento** é o conjunto de verificações de consistência que
antecedem o fechamento definitivo da competência (RFC-006, estado "Fechada").

## 2. Relatórios da 1ª Versão

| Relatório | Conteúdo | Público |
|---|---|---|
| **Folha por departamento** | Totais de proventos/descontos por setor (RFC-007) | Gestão |
| **Total de encargos** | Soma dos valores por evento de encargo (RFC-014) | Contabilidade |
| **Resumo por funcionário** | Competência, líquido, forma de pagamento | Tesouraria |
| **Conferência mês a mês** | Comparação com competência anterior | Conferente |
| **Comissões por venda de origem** | Detalhe da comissão por venda/item: funcionário, produto, taxa e valor (RFC-COMISSION/005 — `commission_details`) | Conferente / Gestão |

### 2.1 Relatório de Comissões por Venda de Origem

Audita a comissão do **evento 7 (Comissão/Vendas)** da venda ao holerite: cada
linha é um **item apurado** em `commission_details` (db/017), com a **origem da
regra** (produto/categoria/padrão — precedência RFC-COMISSION/002 §3.1), a taxa
aplicada e o valor.

**Colunas:** competência, código da venda, data da venda, funcionário
(matrícula = `employees.id`, nome), produto, categoria, origem da regra, taxa
(%), valor da comissão, situação da venda, situação do item.

**Filtros:** competência (obrigatório); funcionário, venda, categoria/produto e
situação (opcionais). **Modo conferência** (default) considera apenas vendas
`aberta` com itens `ativo` (elegibilidade por status — RFC-COMISSION/005 §5
regra 2) e totaliza a **apuração derivada** da competência
(RFC-COMISSION/005 §3.4), que **confere com o evento 7 antes do fechamento**
(cruzamento com o holerite — RFC-007). **Após o fechamento**, o evento 7 passa
a usar a `commission_settlements` **congelada** (RFC-COMISSION/005 §3.5):
devolução/cancelamento posterior pode fazer o total "ao vivo" divergir do valor
pago — o **modo auditoria** (todos os detalhes, inclusive vendas
estornadas/canceladas e itens devolvidos) explica a diferença, e para
competências fechadas o relatório deve exibir o valor do settlement como coluna
de comparação.

**Consulta de referência:**

```sql
-- Relatório: comissões por venda de origem (RFC-015 §2.1)
SELECT DATE_TRUNC('month', s.sale_date)::date AS competencia,
       s.code              AS venda,
       s.sale_date         AS data_venda,
       e.id                AS matricula,
       e.full_name         AS funcionario,
       p.code              AS produto,
       pc.description      AS categoria,
       cd.rate_source      AS origem_regra,   -- produto | categoria | padrao
       cd.rate_percent     AS taxa,
       cd.commission_value AS comissao,
       s.status            AS situacao_venda, -- aberta | cancelada | estornada
       i.status            AS situacao_item   -- ativo | devolvido
FROM commission_details cd
JOIN pos_sales          s  ON s.id = cd.sale_id
JOIN pos_sale_items     i  ON i.id = cd.sale_item_id
JOIN employees          e  ON e.id = cd.employee_id
JOIN products           p  ON p.id = cd.product_id
JOIN product_categories pc ON pc.id = p.category_id
WHERE DATE_TRUNC('month', s.sale_date)::date = :competencia   -- obrigatório
  [AND e.id = :funcionario]                                    -- opcional
  [AND s.status = 'aberta' AND i.status = 'ativo']             -- default (conferência c/ evento 7)
ORDER BY s.code, cd.id;
```

> Aplica-se a **regra geral 1** (competências calculadas/validadas/fechadas) e a
> **regra 2** (exportável em HTML/PDF). O detalhe é imutável (RFC-COMISSION/005
> §5 regra 3) — o relatório reproduz sempre os mesmos valores. Os filtros entre
> `[...]` são opcionais — a consulta acima é de **referência** (não executável
> tal qual); a implementação aplica os filtros informados pelo usuário.

## 3. Fechamento da Competência

### 3.1 Verificações de consistência (pré-fechamento)
1. **Líquido = proventos − descontos** para todos os funcionários (RFC-007).
2. **Nenhum valor sem origem rastreável** (RFC-001, regra 4).
3. **Totais por departamento conferem** com a soma dos holerites.
4. **Encargos calculados** (RFC-014) para a competência.
5. **Nenhum funcionário com dados obrigatórios pendentes** (RFC-002).

### 3.2 Etapas
1. Conferência (papel: Conferente — RFC-009).
2. Aprovação (papel: Aprovador).
3. Fechamento definitivo → competência **Fechada** (imutável, RFC-006).
4. Registro do pagamento (papel: Tesouraria → estado "Paga").

## 4. Regras Gerais

1. **Relatórios só leem competências calculadas, validadas ou fechadas** — nunca
   a competência aberta (valores provisórios).
2. **Todo relatório é exportável** para conferência externa — em HTML
   imprimível ou PDF (ver decisões).
3. **O fechamento é uma ação autorizada** (RFC-009) e auditada.
4. **Depois de fechado, nada muda** — correções só via folha complementar
   (RFC-013).

## 5. Decisões Aprovadas

1. **5 relatórios na 1ª versão** (tabela da seção 2) — sem relatórios
   customizados. ✅ 01/08/2026
2. **Exportação em HTML imprimível (CSS print) e PDF** — o PDF é gerado por
   **dependência estática** (biblioteca Python de geração de PDF, decisão de
   dependência registrada no PLAN_ERP.md); sem serviço externo ou CDN.
   ✅ 01/08/2026
3. **Conferência mês a mês obrigatória** antes do fechamento. ✅ 01/08/2026
4. **Fechamento apenas com validação prévia** (estados sequenciais do RFC-006). ✅ 01/08/2026
5. **Relatório de encargos anexa a trilha de auditoria da competência** — o
   relatório gerado no fechamento inclui a seção **Anexo — Trilha de auditoria**
   (RFC-009 §5, imutável) com os eventos da competência: quando, quem, ação,
   contexto, antes/depois e a versão das tabelas usadas no cálculo (RFC-005
   §5.1.2) — permite conferência externa de quem operou a competência.
   ✅ 11/08/2026
5. **Relatório de comissões por venda de origem** — detalhe por venda/item sobre
   `commission_details` (db/017) com origem da regra, elegibilidade por status e
   cruzamento com o evento 7; público: conferente e gestão (§2.1). ✅ 05/08/2026

## 6. Implementação (rastreabilidade)

| Item | Evidência |
|---|---|
| Relatório de encargos HTML imprimível | `POST /api/folha/competencia/fechar` calcula encargos; `GET /api/folha/encargos/relatorio?competencia=` renderiza (RFC-014 §4.4) com botão Imprimir (CSS print → PDF pelo navegador) |
| Anexo de auditoria no relatório | `server.py::_relatorio_auditoria_html` + `folha_auditoria.listar(competencia)` — eventos imutáveis com quem/quando/antes/depois/tabelas |
| CI | `scripts/smoke_rfc009_auditoria.py` valida o anexo via HTTP (HTML 200, seção presente, eventos e usuários listados) |

## 7. Aprovação

| Revisor | Papel | Voto | Data |
|---|---|---|---|
| crpalmarante | _autor_ | ✅ Aprovado | 11/08/2026 |
