"""
Sales B2B — reserva de estoque na aprovação (MVP).

Não move saldo físico; reduz ATP (promise) até faturar/cancelar.
Fonte da verdade: COBOL SEQUENTIAL (reservas_venda.dat + reservas_linhas.dat).
Projeção: dados/sales_reservations.json
"""

from __future__ import annotations

from datetime import datetime

import inventory_mvp
import reservas_store


def _now():
    return datetime.now().isoformat(timespec="seconds")


def reserved_qty(estabelecimento_id, produto_id, exclude_pedido_id=None):
    eid = str(estabelecimento_id or "").strip()
    pid = str(produto_id or "").strip()
    excl = str(exclude_pedido_id or "").strip()
    total = 0
    for r in reservas_store.listar():
        if r.get("status") != "active":
            continue
        if excl and str(r.get("pedido_id") or "") == excl:
            continue
        if eid and str(r.get("estabelecimento_id") or "") != eid:
            continue
        for line in r.get("linhas") or []:
            if str(line.get("produto_id") or "") == pid:
                try:
                    total += int(line.get("qtd") or 0)
                except (TypeError, ValueError):
                    pass
    return total


def available_for_sale(estabelecimento_id, produto_id, exclude_pedido_id=None):
    bal = inventory_mvp.inventory_balance(estabelecimento_id, produto_id)
    held = reserved_qty(estabelecimento_id, produto_id, exclude_pedido_id=exclude_pedido_id)
    return max(0, int(bal or 0) - int(held or 0))


def get_for_pedido(pedido_id):
    return reservas_store.get_active_for_pedido(pedido_id)


def reserve_for_order(pedido, usuario="", *, allow_partial=False):
    """
    Cria/atualiza reserva ativa para o pedido aprovado.
    Por padrão exige ATP integral; allow_partial=True aceita pedido parcial (RFC).
    """
    pid = str((pedido or {}).get("id") or "").strip()
    if not pid:
        raise ValueError("pedido sem id")
    eid = str((pedido or {}).get("estabelecimento_id") or "").strip()
    if not eid:
        try:
            import org_store
            eid = org_store.estabelecimento_padrao_id() or "matriz"
        except Exception:
            eid = "matriz"

    linhas_in = (pedido or {}).get("itens") or []
    linhas = []
    warnings = []
    shortfalls = []
    for it in linhas_in:
        prod = str(it.get("prod_id") or it.get("produto_id") or it.get("id") or "").strip()
        if not prod:
            continue
        try:
            qtd = int(float(it.get("qtd") or 0))
        except (TypeError, ValueError):
            qtd = 0
        if qtd <= 0:
            continue
        avail = available_for_sale(eid, prod, exclude_pedido_id=pid)
        take = min(qtd, avail) if avail >= 0 else qtd
        if take < qtd:
            msg = f"{prod}: pediu {qtd}, reservou {take} (ATP {avail})"
            warnings.append(msg)
            shortfalls.append({
                "produto_id": prod,
                "produto": it.get("produto") or "",
                "qtd_pedida": qtd,
                "qtd_disponivel": avail,
                "qtd_reservada": take,
            })
        if take > 0:
            linhas.append({
                "produto_id": prod,
                "produto": it.get("produto") or "",
                "qtd": take,
                "qtd_pedida": qtd,
            })

    if shortfalls and not allow_partial:
        detail = "; ".join(warnings)
        err = ValueError(
            "Estoque insuficiente para reserva integral. "
            "Use allow_partial para pedido parcial. " + detail
        )
        err.code = "reserva_parcial"
        err.shortfalls = shortfalls
        err.warnings = warnings
        raise err

    if not linhas:
        raise ValueError("Nenhuma quantidade disponível para reservar")

    # libera reserva anterior do mesmo pedido
    prev = reservas_store.get_active_for_pedido(pid)
    if prev:
        reservas_store.set_status(prev.get("id"), "replaced")

    seq = reservas_store.max_seq() + 1
    row = {
        "id": f"SR-{seq:05d}",
        "seq": seq,
        "pedido_id": pid,
        "pedido_numero": (pedido or {}).get("numero") or "",
        "estabelecimento_id": eid,
        "status": "active",
        "parcial": bool(shortfalls),
        "linhas": linhas,
        "warnings": warnings,
        "usuario": str(usuario or "").strip(),
        "criado_em": _now(),
        "atualizado_em": _now(),
    }
    return reservas_store.save(row, is_new=True)


def release_for_order(pedido_id, motivo="released"):
    key = str(pedido_id or "").strip()
    hit = reservas_store.get_active_for_pedido(key)
    if not hit:
        return None
    return reservas_store.set_status(hit.get("id"), str(motivo or "released"))


def consume_for_order(pedido_id):
    """Marca reserva consumida após stock move (Delivery), não no faturar comercial."""
    return release_for_order(pedido_id, motivo="consumed")


def reserve_stock(estabelecimento_id, linhas, *, usuario="", nota="", origem="manual"):
    """
    Reserva manual de estoque (sem pedido B2B), ex.: venda interna, promessa.
    linhas: [{produto_id, qtd}] — valida ATP por linha (não reserva além do disponível).
    Retorna a reserva criada (status active).
    """
    eid = str(estabelecimento_id or "").strip() or "matriz"
    seq = reservas_store.max_seq() + 1
    rid = f"SR-{seq:05d}"
    linhas_out = []
    warnings = []
    for it in linhas or []:
        if not isinstance(it, dict):
            continue
        prod = str(it.get("produto_id") or it.get("id") or "").strip()
        try:
            qtd = int(float(it.get("qtd") or 0))
        except (TypeError, ValueError):
            qtd = 0
        if not prod or qtd <= 0:
            continue
        avail = available_for_sale(eid, prod)
        take = min(qtd, avail) if avail >= 0 else qtd
        if take < qtd:
            warnings.append(f"{prod}: pediu {qtd}, reservou {take} (ATP {avail})")
        if take > 0:
            linhas_out.append({
                "produto_id": prod,
                "produto": it.get("produto") or "",
                "qtd": take,
                "qtd_pedida": qtd,
            })
    if not linhas_out:
        raise ValueError("Nenhuma quantidade disponível para reservar")
    row = {
        "id": rid,
        "seq": seq,
        "pedido_id": f"MAN-{seq:05d}",
        "pedido_numero": "",
        "estabelecimento_id": eid,
        "status": "active",
        "parcial": bool(warnings),
        "linhas": linhas_out,
        "warnings": warnings,
        "usuario": str(usuario or "").strip(),
        "origem": str(origem or "manual"),
        "nota": str(nota or "").strip(),
        "criado_em": _now(),
        "atualizado_em": _now(),
    }
    return reservas_store.save(row, is_new=True)


def release_reservation(reserva_id, motivo="released"):
    """Libera reserva pelo ID da reserva (SR-xxxxx), não pelo pedido."""
    cur = reservas_store.get(reserva_id)
    if not cur:
        return None
    return reservas_store.set_status(str(reserva_id), str(motivo or "released"))


def list_reservations(estabelecimento_id=None, produto_id=None, status="active"):
    """Lista reservas (padrão: ativas) com linhas, para painel de estoque."""
    out = []
    eid = str(estabelecimento_id or "").strip()
    pid = str(produto_id or "").strip()
    for r in reservas_store.listar():
        if status and r.get("status") != status:
            continue
        if eid and str(r.get("estabelecimento_id") or "") != eid:
            continue
        linhas = r.get("linhas") or []
        if pid:
            linhas = [ln for ln in linhas if str(ln.get("produto_id") or "") == pid]
            if not linhas:
                continue
            r = dict(r)
            r["linhas"] = linhas
        out.append(r)
    out.sort(key=lambda r: r.get("seq") or 0, reverse=True)
    return out
