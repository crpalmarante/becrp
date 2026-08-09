# Migração — CRUD COBOL + JSON projeção

**Meta:** segurança e escopo original — verdade no COBOL; Python extrai JSON; relatórios na tela.

## Ordem sugerida

| # | Domínio | Estado | Fonte atual | Programa |
|---|---------|--------|-------------|----------|
| 1 | Contas a receber (AR) | **feito** | `.dat` + projeção JSON | `gerir_titulos_ar` |
| 2 | Pedidos B2B (cab+itens) | **feito** | `.dat` + projeção JSON | `gerir_pedidos_b2b` + `gerir_itens_ped_b2b` |
| 3 | Parceiros (core+end+ctt) | **feito** | `.dat` + projeção JSON | `gerir_parceiros` + `gerir_end_parceiro` + `gerir_ctt_parceiro` |
| 4 | Delivery orders | **feito** | `.dat` + hist auxiliar + projeção | `gerir_entregas` + `gerir_paradas_ent` + `gerir_itens_ent` |
| 5 | Reservas venda | **feito** | `.dat` + hist auxiliar + projeção | `gerir_reservas_venda` + `gerir_lin_reserva` |
| 6 | Faturas venda (B2B) | **feito** | `.dat` + hist auxiliar + projeção | `gerir_faturas_venda` |
| — | Produtos / fornecedores | **feito** (SEQUENTIAL + COMP-3) | `.dat` + projeção JSON | `cadastrar_produto` / `gerir_fornecedores` |
| — | Numeração | já COBOL | `.dat` | existentes |

## Regras
- Nova feature de negócio: CRUD COBOL primeiro
- JSON: só listar/relatório (e sync opcional)
- **`.dat` de verdade:** `ORGANIZATION IS SEQUENTIAL` (registro fixo; `COMP-3` ok)
- **LINE SEQUENTIAL:** só texto/CSV/export — sem `COMP-*`
- Extras aninhados (endereços BP): core no `.dat`; detalhe via arquivo auxiliar ou campo payload até modelar 2º arquivo
