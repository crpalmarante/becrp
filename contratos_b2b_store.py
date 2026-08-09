"""
Contratos B2B (Vendas Corporativas).

MVP: dados/contratos_b2b.json
Fluxo: rascunho → ativo → suspenso|encerrado|cancelado
Pode gerar Pedido de Venda a partir de contrato ativo.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import jsonio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "contratos_b2b.json")

STATUSES = ("rascunho", "ativo", "suspenso", "encerrado", "cancelado")
FLOW = {
    "rascunho": {"ativo", "cancelado"},
    "ativo": {"suspenso", "encerrado", "cancelado"},
    "suspenso": {"ativo", "encerrado", "cancelado"},
    "encerrado": set(),
    "cancelado": set(),
}
CYCLES = ("mensal", "trimestral", "anual", "unico")
RENEWALS = ("automatica", "manual", "nao")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _digits(val):
    return "".join(c for c in str(val or "") if c.isdigit())


def _money(val):
    try:
        return float(
            Decimal(str(val or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )
    except Exception:
        return 0.0


def _as_qty(val):
    try:
        return round(float(val or 0), 3)
    except (TypeError, ValueError):
        return 0.0


def _load():
    if not os.path.exists(DATA_FILE):
        return {"next_id": 1, "contratos": [], "atualizado_em": None}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"next_id": 1, "contratos": [], "atualizado_em": None}
    data.setdefault("contratos", [])
    data.setdefault("next_id", 1)
    if not isinstance(data["contratos"], list):
        data["contratos"] = []
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("contratos") or [])
    jsonio.save(DATA_FILE, data)


def _normalize_itens(itens):
    out = []
    for it in itens or []:
        if not isinstance(it, dict):
            continue
        q = _as_qty(it.get("qtd") or it.get("qty") or it.get("quantidade") or 0)
        preco = _money(it.get("preco") or it.get("unit_price") or 0)
        if q <= 0:
            continue
        sub = _money(it.get("subtotal")) if it.get("subtotal") is not None else _money(q * preco)
        out.append({
            "prod_id": it.get("prod_id") or it.get("produto_id") or it.get("item_id") or "",
            "produto": (it.get("produto") or it.get("item_name") or it.get("description") or "").strip(),
            "qtd": q,
            "preco": preco,
            "desconto_pct": float(it.get("desconto_pct") or 0),
            "subtotal": sub,
        })
    return out


def _calc_total(itens):
    return _money(sum(_money(it.get("subtotal")) for it in itens or []))


def _normalize(row):
    r = dict(row or {})
    try:
        r["id"] = int(r.get("id") or 0)
    except (TypeError, ValueError):
        r["id"] = 0
    st = str(r.get("status") or "rascunho").lower()
    if st not in STATUSES:
        st = "rascunho"
    r["status"] = st
    ciclo = str(r.get("ciclo") or r.get("billing_cycle") or "mensal").lower()
    if ciclo in ("monthly",):
        ciclo = "mensal"
    elif ciclo in ("quarterly",):
        ciclo = "trimestral"
    elif ciclo in ("yearly", "annual"):
        ciclo = "anual"
    elif ciclo in ("once", "one_shot", "único", "unico"):
        ciclo = "unico"
    if ciclo not in CYCLES:
        ciclo = "mensal"
    r["ciclo"] = ciclo
    ren = str(r.get("renovacao") or r.get("renewal_type") or "manual").lower()
    if ren in ("automatic", "auto"):
        ren = "automatica"
    elif ren in ("none", "no"):
        ren = "nao"
    if ren not in RENEWALS:
        ren = "manual"
    r["renovacao"] = ren
    r["itens"] = _normalize_itens(r.get("itens") or r.get("items") or [])
    if r.get("valor") is None or r.get("valor") == "":
        r["valor"] = _calc_total(r["itens"])
    else:
        r["valor"] = _money(r.get("valor"))
    r["cnpj"] = _digits(r.get("cnpj"))
    r.setdefault("pedidos_gerados", [])
    if not isinstance(r["pedidos_gerados"], list):
        r["pedidos_gerados"] = []
    return r


def listar(status=None, cliente_id=None, q=None):
    rows = [_normalize(r) for r in (_load().get("contratos") or [])]
    if status:
        st = str(status).lower()
        rows = [r for r in rows if r.get("status") == st]
    if cliente_id:
        cid = str(cliente_id)
        rows = [r for r in rows if str(r.get("cliente_id") or "") == cid]
    if q:
        qq = str(q).lower().strip()
        dig = _digits(q)
        rows = [
            r for r in rows
            if qq in str(r.get("numero") or "").lower()
            or qq in str(r.get("titulo") or "").lower()
            or qq in str(r.get("razao_social") or "").lower()
            or (dig and dig in _digits(r.get("cnpj")))
        ]
    rows.sort(key=lambda r: r.get("id") or 0, reverse=True)
    return rows


def get(cid):
    for r in listar():
        if str(r.get("id")) == str(cid):
            return r
    return None


def create(payload, *, usuario=""):
    body = dict(payload or {})
    body.pop("id", None)
    body.pop("action", None)
    data = _load()
    nid = int(data.get("next_id") or 1)
    numero = (body.get("numero") or "").strip()
    if not numero:
        numero = f"CT-{nid:05d}"
    itens = _normalize_itens(body.get("itens") or body.get("items") or [])
    row = _normalize({
        "id": nid,
        "numero": numero,
        "titulo": (body.get("titulo") or body.get("title") or "").strip() or f"Contrato {numero}",
        "status": "rascunho",
        "cliente_id": body.get("cliente_id") or body.get("customer_id") or "",
        "razao_social": (body.get("razao_social") or body.get("customer_name") or "").strip(),
        "cnpj": body.get("cnpj"),
        "inicio": (body.get("inicio") or body.get("start_date") or _today())[:10],
        "fim": (body.get("fim") or body.get("end_date") or "")[:10],
        "ciclo": body.get("ciclo") or body.get("billing_cycle") or "mensal",
        "renovacao": body.get("renovacao") or body.get("renewal_type") or "manual",
        "valor": body.get("valor") if body.get("valor") is not None else None,
        "itens": itens,
        "payment_terms": body.get("payment_terms") or body.get("condicao_pg") or "30",
        "forma_pg": body.get("forma_pg") or "Boleto",
        "lista_precos_id": body.get("lista_precos_id") or "",
        "vendedor": body.get("vendedor") or body.get("sales_rep") or usuario or "",
        "pedido_origem_id": body.get("pedido_origem_id"),
        "notas": (body.get("notas") or body.get("notes") or "").strip(),
        "pedidos_gerados": [],
        "criado_em": _now(),
        "criado_por": usuario,
        "atualizado_em": _now(),
    })
    if not row["razao_social"] and not row["cliente_id"]:
        raise ValueError("informe cliente (razao_social ou cliente_id)")
    data["contratos"].insert(0, row)
    data["next_id"] = nid + 1
    _save(data)
    return row


def update(cid, payload, *, usuario=""):
    data = _load()
    row = None
    idx = None
    for i, r in enumerate(data.get("contratos") or []):
        if str(r.get("id")) == str(cid):
            row = r
            idx = i
            break
    if row is None:
        raise ValueError("contrato não encontrado")
    cur = _normalize(row)
    if cur.get("status") in ("encerrado", "cancelado"):
        raise ValueError(f"contrato {cur['status']} — edição bloqueada")
    body = dict(payload or {})
    for k in (
        "titulo", "razao_social", "cliente_id", "cnpj", "inicio", "fim",
        "ciclo", "renovacao", "valor", "payment_terms", "forma_pg",
        "lista_precos_id", "vendedor", "notas", "pedido_origem_id",
    ):
        if k in body and body[k] is not None:
            cur[k] = body[k]
    if "itens" in body or "items" in body:
        cur["itens"] = _normalize_itens(body.get("itens") or body.get("items"))
        if body.get("valor") is None:
            cur["valor"] = _calc_total(cur["itens"])
    cur["atualizado_em"] = _now()
    cur["atualizado_por"] = usuario
    cur = _normalize(cur)
    data["contratos"][idx] = cur
    _save(data)
    return cur


def set_status(cid, novo_status, *, usuario=""):
    st = str(novo_status or "").lower()
    if st not in STATUSES:
        raise ValueError(f"status inválido: {novo_status}")
    data = _load()
    idx = None
    row = None
    for i, r in enumerate(data.get("contratos") or []):
        if str(r.get("id")) == str(cid):
            idx, row = i, r
            break
    if row is None:
        raise ValueError("contrato não encontrado")
    cur = _normalize(row)
    atual = cur["status"]
    if st == atual:
        return cur
    if st not in FLOW.get(atual, set()):
        raise ValueError(f"transição inválida: {atual} → {st}")
    if st == "ativo":
        if not cur.get("itens") and _money(cur.get("valor")) <= 0:
            raise ValueError("contrato sem itens/valor — não ativa")
        if len(_digits(cur.get("cnpj"))) != 14 and not cur.get("cliente_id"):
            raise ValueError("contrato B2B requer CNPJ ou cliente_id")
    cur["status"] = st
    cur["atualizado_em"] = _now()
    cur["atualizado_por"] = usuario
    data["contratos"][idx] = cur
    _save(data)
    return cur


def create_from_pedido(pedido, *, usuario=""):
    """Gera contrato rascunho a partir de pedido/cotação B2B."""
    p = pedido or {}
    return create({
        "titulo": f"Contrato ref. {p.get('numero') or p.get('id')}",
        "cliente_id": p.get("cliente_id"),
        "razao_social": p.get("razao_social"),
        "cnpj": p.get("cnpj"),
        "inicio": _today(),
        "ciclo": "mensal",
        "renovacao": "manual",
        "itens": p.get("itens") or [],
        "valor": p.get("total"),
        "payment_terms": p.get("payment_terms") or p.get("condicao_pg"),
        "forma_pg": p.get("forma_pg"),
        "lista_precos_id": p.get("lista_precos_id"),
        "vendedor": p.get("vendedor") or usuario,
        "pedido_origem_id": p.get("id"),
        "notas": f"Gerado do documento {p.get('numero') or p.get('id')}",
    }, usuario=usuario)


def gerar_pedido(cid, *, usuario=""):
    """
    Cria pedido B2B (rascunho) a partir do contrato ativo.
    Retorna {contrato, pedido}.
    """
    import pedidos_b2b_store

    cur = get(cid)
    if not cur:
        raise ValueError("contrato não encontrado")
    if cur.get("status") != "ativo":
        raise ValueError("só gera pedido de contrato ativo")
    if not cur.get("itens"):
        raise ValueError("contrato sem itens")

    pedido = {
        "tipo": "pedido",
        "status": "rascunho",
        "data": _today(),
        "cliente_id": cur.get("cliente_id") or "",
        "razao_social": cur.get("razao_social") or "",
        "cnpj": cur.get("cnpj") or "",
        "payment_terms": cur.get("payment_terms") or "30",
        "forma_pg": cur.get("forma_pg") or "Boleto",
        "lista_precos_id": cur.get("lista_precos_id") or "",
        "vendedor": cur.get("vendedor") or usuario or "",
        "itens": [
            {
                "prod_id": it.get("prod_id"),
                "produto": it.get("produto"),
                "qtd": it.get("qtd"),
                "preco": it.get("preco"),
                "desconto_pct": it.get("desconto_pct") or 0,
                "subtotal": it.get("subtotal"),
            }
            for it in cur.get("itens") or []
        ],
        "total": cur.get("valor") or _calc_total(cur.get("itens")),
        "notas": f"Contrato {cur.get('numero')}",
        "contrato_id": cur.get("id"),
        "contrato_numero": cur.get("numero"),
        "smart": {"entregas": 0, "faturas": 0, "compras": 0,
                  "assinaturas": 0, "projetos": 0, "tarefas": 0},
    }
    saved = pedidos_b2b_store.save(pedido, is_new=True)

    data = _load()
    for i, r in enumerate(data.get("contratos") or []):
        if str(r.get("id")) == str(cid):
            gens = list(r.get("pedidos_gerados") or [])
            gens.append({
                "pedido_id": saved.get("id"),
                "numero": saved.get("numero"),
                "em": _now(),
                "por": usuario,
            })
            r["pedidos_gerados"] = gens
            r["atualizado_em"] = _now()
            data["contratos"][i] = r
            _save(data)
            return {"contrato": _normalize(r), "pedido": saved}
    return {"contrato": cur, "pedido": saved}
