"""
Bridge Vendas B2B → WMS (picking/packing/expedição).

Ao faturar um pedido B2B, gera operação WMS, pick list e expedição.
"""

from __future__ import annotations

import wms_locations
import wms_operations
import wms_picking
import wms_shipping
import wms_warehouses


def create_wms_from_pedido(pedido, *, usuario=""):
    """
    pedido: dict com itens, cliente, estabelecimento_id, etc.
    Retorna: {"operacao_id", "pick_list_id", "expedicao_id"}
    """
    pedido = dict(pedido or {})
    armazem = wms_warehouses.map_estabelecimento_to_armazem(pedido.get("estabelecimento_id"))
    if not armazem:
        raise ValueError("pedido sem estabelecimento_id mapeado para armazém")

    # local de picking padrão
    locs = wms_locations.list_localizacoes(armazem=armazem, tipo="picking")
    loc_origem = (locs[0]["codigo"] if locs else "PCK-01") if isinstance(locs, list) else "PCK-01"

    itens = []
    for i, it in enumerate(pedido.get("itens") or [], start=1):
        if not str(it.get("prod_id") or it.get("produto_id") or "").strip():
            continue
        qtd = float(it.get("qtd") or it.get("quantidade") or 0)
        if qtd <= 0:
            continue
        itens.append({
            "linha": i,
            "produto_id": str(it.get("prod_id") or it.get("produto_id") or ""),
            "produto": it.get("produto") or "",
            "qtd": qtd,
            "loc_origem": loc_origem,
        })
    if not itens:
        raise ValueError("pedido sem itens para WMS")

    op = wms_operations.create_operacao({
        "tipo": "EXP-CLIENTE",
        "armazem": armazem,
        "documento_tipo": "pedido_venda",
        "documento_ref": pedido.get("numero") or str(pedido.get("id")),
        "parceiro": pedido.get("razao_social") or pedido.get("cliente") or "",
        "responsavel": usuario,
        "linhas": itens,
    }, usuario=usuario)
    wms_operations.transition(op["id"], "plan", usuario=usuario)
    wms_operations.transition(op["id"], "ready", usuario=usuario)

    pick = wms_picking.create_pick_list({
        "operacao_id": op["id"],
        "estrategia": "single",
        "operador": usuario,
    }, usuario=usuario)

    exp = wms_shipping.create_expedicao({
        "pick_list_id": pick["id"],
        "destino": "customer",
    }, usuario=usuario)

    return {
        "operacao_id": op.get("id"),
        "pick_list_id": pick.get("id"),
        "expedicao_id": exp.get("id"),
    }
