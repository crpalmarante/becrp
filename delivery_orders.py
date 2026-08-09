"""
Delivery — Orders (RFC-18000 / RFC-18001 MVP).

Pedido de entrega com paradas e itens.
Fonte da verdade: COBOL (dados/entregas*.dat) via delivery_store.
Projeção: dados/delivery_orders.json

Separação:
  Sales = o que foi vendido
  Delivery = como / para onde entregar
  Fiscal = nota
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import delivery_store

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "delivery_orders.json")

STATUSES = {
    "draft": "Rascunho",
    "confirmed": "Confirmada",
    "waiting_stock": "Aguardando estoque",
    "ready": "Pronta",
    "assigned": "Atribuída",
    "in_transit": "Em trânsito",
    "delivered": "Entregue",
    "completed": "Concluída",
    "cancelled": "Cancelada",
}

STOP_STATUSES = {
    "pending": "Pendente",
    "en_route": "A caminho",
    "arrived": "No local",
    "delivered": "Entregue",
    "failed": "Falhou",
    "skipped": "Pulada",
}

PRIORITIES = {
    "emergency": "Emergência",
    "high": "Alta",
    "normal": "Normal",
    "low": "Baixa",
}

TRANSITIONS = {
    ("draft", "confirm"): "confirmed",
    ("draft", "cancel"): "cancelled",
    ("confirmed", "wait_stock"): "waiting_stock",
    ("confirmed", "ready"): "ready",
    ("confirmed", "cancel"): "cancelled",
    ("waiting_stock", "ready"): "ready",
    ("waiting_stock", "cancel"): "cancelled",
    ("ready", "assign"): "assigned",
    ("ready", "cancel"): "cancelled",
    ("assigned", "depart"): "in_transit",
    ("assigned", "cancel"): "cancelled",
    ("in_transit", "deliver"): "delivered",
    ("delivered", "complete"): "completed",
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load_raw():
    """Monta estrutura legada a partir do COBOL (fallback JSON)."""
    try:
        orders = delivery_store.listar()
        if not orders:
            return ensure_seed()
        return {
            "orders": orders,
            "seq": delivery_store.max_seq(),
            "total": len(orders),
            "atualizado_em": _now(),
            "source": "cobol",
        }
    except Exception:
        if not os.path.exists(DATA_FILE):
            return ensure_seed()
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return ensure_seed()
        if not isinstance(data.get("orders"), list):
            data["orders"] = []
        if data.get("seq") is None:
            data["seq"] = len(data["orders"])
        if not data["orders"]:
            return ensure_seed()
        return data


def _save(data, changed=None):
    """Persiste no COBOL o pedido alterado (ou todos) + projeção JSON."""
    orders = data.get("orders") if isinstance(data, dict) else []
    try:
        if changed is not None:
            existing = delivery_store.get(changed.get("id"))
            delivery_store.save(changed, is_new=existing is None)
        else:
            for o in orders or []:
                existing = delivery_store.get(o.get("id"))
                delivery_store.save(o, is_new=existing is None)
        delivery_store.sync_json(
            delivery_store.listar() if changed is not None else orders
        )
    except Exception:
        os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
        data["atualizado_em"] = _now()
        data["total"] = len(orders or [])
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def _hist(status, usuario="", nota=""):
    return {
        "status": status,
        "em": _now(),
        "usuario": str(usuario or "").strip(),
        "nota": str(nota or "").strip(),
    }


def _next_id(data):
    try:
        seq = delivery_store.max_seq() + 1
    except Exception:
        seq = int(data.get("seq") or 0) + 1
    data["seq"] = seq
    return f"DO-{datetime.now().strftime('%Y%m%d')}-{seq:04d}"


def ensure_seed():
    now = _now()
    row = {
        "id": "DO-SEED-0001",
        "origem_tipo": "pedido_venda",
        "origem_ref": "PV-100",
        "parceiro_id": "bp001",
        "parceiro": "Cliente Demo",
        "fonte": "DC-01",
        "fonte_nome": "Armazém Principal",
        "status": "ready",
        "prioridade": "normal",
        "data_agendada": datetime.now().strftime("%Y-%m-%d"),
        "janela": "tarde",
        "recurso_id": "",
        "motorista": "",
        "veiculo": "",
        "expedicao_id": "",
        "observacao": "Seed — entrega pronta (após WMS)",
        "paradas": [
            {
                "parada": 1,
                "rotulo": "Casa do cliente",
                "address_type": "SHIPPING",
                "endereco": "Rua das Flores, 100 — Centro",
                "cidade": "Passo Fundo",
                "uf": "RS",
                "cep": "99010-000",
                "contato": "João Silva",
                "telefone": "(54) 99999-0001",
                "status": "pending",
                "itens": [
                    {
                        "produto_id": "1",
                        "produto": "Produto demo",
                        "qtd": 2,
                    }
                ],
            }
        ],
        "historico": [
            _hist("draft", "seed", "criação"),
            _hist("confirmed", "seed", "confirmada"),
            _hist("ready", "seed", "estoque ok / WMS"),
        ],
        "cancelamento_motivo": "",
        "origem_dado": "seed",
        "criado_em": now,
        "atualizado_em": now,
    }
    data = {"seq": 1, "atualizado_em": now, "orders": [row], "total": 1}
    _save(data, changed=row)
    return data


def _norm_stops(paradas_in):
    out = []
    for i, st in enumerate(paradas_in or [], start=1):
        if not isinstance(st, dict):
            continue
        itens = []
        for it in st.get("itens") or []:
            if not isinstance(it, dict):
                continue
            itens.append({
                "produto_id": str(it.get("produto_id") or ""),
                "produto": str(it.get("produto") or "item"),
                "qtd": float(it.get("qtd") or 1),
            })
        if not itens:
            itens = [{"produto_id": "", "produto": "item", "qtd": 1}]
        out.append({
            "parada": int(st.get("parada") or i),
            "rotulo": str(st.get("rotulo") or f"Parada {i}"),
            "address_type": str(st.get("address_type") or "SHIPPING").upper(),
            "endereco": str(st.get("endereco") or "").strip(),
            "cidade": str(st.get("cidade") or "").strip(),
            "uf": str(st.get("uf") or "").strip().upper(),
            "cep": str(st.get("cep") or "").strip(),
            "contato": str(st.get("contato") or "").strip(),
            "telefone": str(st.get("telefone") or "").strip(),
            "status": str(st.get("status") or "pending"),
            "itens": itens,
        })
    return out


def _enrich(row):
    out = dict(row)
    out["status_label"] = STATUSES.get(out.get("status"), out.get("status") or "")
    prio = str(out.get("prioridade") or "normal").strip().lower() or "normal"
    if prio not in PRIORITIES:
        prio = "normal"
    out["prioridade"] = prio
    out["prioridade_label"] = PRIORITIES.get(prio, prio)
    paradas = []
    itens_total = 0
    for st in out.get("paradas") or []:
        ss = dict(st)
        ss["status_label"] = STOP_STATUSES.get(ss.get("status"), ss.get("status") or "")
        ss["itens_count"] = len(ss.get("itens") or [])
        itens_total += ss["itens_count"]
        paradas.append(ss)
    out["paradas"] = paradas
    out["paradas_count"] = len(paradas)
    out["itens_count"] = itens_total
    st = out.get("status")
    out["acoes"] = [a for (fr, a), _to in TRANSITIONS.items() if fr == st]
    return out


def meta():
    data = _load_raw()
    return {
        "total": len(data.get("orders") or []),
        "status": STATUSES,
        "parada_status": STOP_STATUSES,
        "prioridades": PRIORITIES,
        "atualizado_em": data.get("atualizado_em"),
    }


def list_orders(q=None, status=None, fonte=None, parceiro=None):
    rows = list(_load_raw().get("orders") or [])
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r for r in rows
            if qq in str(r.get("id") or "").lower()
            or qq in str(r.get("origem_ref") or "").lower()
            or qq in str(r.get("parceiro") or "").lower()
            or qq in str(r.get("motorista") or "").lower()
        ]
    if status:
        st = str(status).strip().lower()
        if st not in STATUSES:
            raise ValueError("status inválido")
        rows = [r for r in rows if r.get("status") == st]
    if fonte:
        fk = str(fonte).strip().upper()
        rows = [r for r in rows if str(r.get("fonte") or "").upper() == fk]
    if parceiro:
        pk = str(parceiro).strip().lower()
        rows = [
            r for r in rows
            if pk in str(r.get("parceiro") or "").lower()
            or pk == str(r.get("parceiro_id") or "").lower()
        ]
    order = {s: i for i, s in enumerate(STATUSES)}
    rows.sort(key=lambda r: (order.get(r.get("status"), 99), str(r.get("id") or "")))
    return {
        "total": len(_load_raw().get("orders") or []),
        "filtrado": len(rows),
        "status_opcoes": STATUSES,
        "orders": [_enrich(r) for r in rows],
    }


def get_order(oid):
    key = str(oid or "").strip().upper()
    for r in _load_raw().get("orders") or []:
        if str(r.get("id") or "").upper() == key:
            return _enrich(r)
    return None


def create_order(payload, usuario=""):
    body = dict(payload or {})
    if body.get("expedicao_id") and not body.get("paradas") and not body.get("endereco"):
        return create_from_shipping(body.get("expedicao_id"), usuario=usuario)

    data = _load_raw()
    oid = str(body.get("id") or "").strip().upper() or _next_id(data)
    if any(str(r.get("id") or "").upper() == oid for r in data["orders"]):
        raise ValueError(f"já existe entrega {oid}")

    paradas = _norm_stops(body.get("paradas"))
    if not paradas and body.get("endereco"):
        # atalho: uma parada a partir de campos flat
        paradas = _norm_stops([{
            "rotulo": body.get("rotulo") or "Entrega",
            "endereco": body.get("endereco"),
            "cidade": body.get("cidade") or "",
            "uf": body.get("uf") or "",
            "cep": body.get("cep") or "",
            "contato": body.get("contato") or body.get("parceiro") or "",
            "telefone": body.get("telefone") or "",
            "itens": body.get("itens") or [{"produto": body.get("produto") or "item", "qtd": body.get("qtd") or 1}],
        }])
    if not paradas:
        raise ValueError("informe ao menos uma parada (ou endereco)")

    fonte = str(body.get("fonte") or "DC-01").strip().upper()
    row = {
        "id": oid,
        "origem_tipo": str(body.get("origem_tipo") or "manual").strip(),
        "origem_ref": str(body.get("origem_ref") or "").strip(),
        "parceiro_id": str(body.get("parceiro_id") or "").strip(),
        "parceiro": str(body.get("parceiro") or "").strip() or "Cliente",
        "fonte": fonte,
        "fonte_nome": str(body.get("fonte_nome") or "").strip(),
        "status": "draft",
        "prioridade": (
            str(body.get("prioridade") or "normal").strip().lower()
            if str(body.get("prioridade") or "normal").strip().lower() in PRIORITIES
            else "normal"
        ),
        "data_agendada": str(body.get("data_agendada") or "").strip(),
        "janela": str(body.get("janela") or "").strip(),
        "slot_id": str(body.get("slot_id") or "").strip(),
        "scheduling_status": str(body.get("scheduling_status") or "").strip(),
        "recurso_id": "",
        "motorista": str(body.get("motorista") or "").strip(),
        "veiculo": str(body.get("veiculo") or "").strip(),
        "expedicao_id": str(body.get("expedicao_id") or "").strip().upper(),
        "observacao": str(body.get("observacao") or "").strip(),
        "paradas": paradas,
        "historico": [_hist("draft", usuario, "criação")],
        "cancelamento_motivo": "",
        "origem_dado": "manual",
        "criado_em": _now(),
        "atualizado_em": _now(),
    }
    data["orders"].append(row)
    _save(data, changed=row)
    return _enrich(row)


def find_by_expedicao(expedicao_id):
    key = str(expedicao_id or "").strip().upper()
    if not key:
        return None
    for r in _load_raw().get("orders") or []:
        if str(r.get("expedicao_id") or "").upper() == key:
            return _enrich(r)
    return None


def find_by_origem(origem_tipo, origem_ref):
    ot = str(origem_tipo or "").strip()
    ref = str(origem_ref or "").strip()
    if not ref:
        return None
    for r in _load_raw().get("orders") or []:
        if str(r.get("origem_tipo") or "") == ot and str(r.get("origem_ref") or "") == ref:
            return _enrich(r)
    return None


def create_from_pedido_b2b(pedido, usuario=""):
    """
    Handoff Sales B2B → Delivery Order (idempotente).
    Não move estoque — só agenda entrega do pedido aprovado/faturado.
    """
    pedido = pedido or {}
    ref = str(pedido.get("numero") or pedido.get("id") or "").strip()
    if not ref:
        raise ValueError("pedido sem número/id")
    existing = find_by_origem("pedido_venda", ref)
    if existing:
        return existing

    itens = []
    for it in pedido.get("itens") or []:
        itens.append({
            "produto_id": it.get("prod_id") or it.get("produto_id") or "",
            "produto": it.get("produto") or "item",
            "qtd": it.get("qtd") or 1,
        })
    if not itens:
        itens = [{"produto": "pedido " + ref, "qtd": 1}]

    endereco = (
        pedido.get("endereco_entrega")
        or pedido.get("endereco_cobranca")
        or ""
    )
    if not endereco:
        endereco = "A combinar — " + (pedido.get("razao_social") or "cliente")

    return create_order({
        "origem_tipo": "pedido_venda",
        "origem_ref": ref,
        "parceiro_id": pedido.get("cliente_id") or "",
        "parceiro": pedido.get("razao_social") or pedido.get("cliente_nome") or "Cliente",
        "fonte": "DC-01",
        "data_agendada": pedido.get("data") or "",
        "endereco": endereco,
        "cidade": pedido.get("cidade") or "",
        "uf": pedido.get("uf") or "",
        "contato": pedido.get("razao_social") or "",
        "telefone": pedido.get("telefone") or "",
        "itens": itens,
        "observacao": f"Handoff B2B {ref}" + (
            f" · fatura {pedido.get('fatura_numero')}" if pedido.get("fatura_numero") else ""
        ),
        "prioridade": "normal",
    }, usuario=usuario)


def create_from_shipping(expedicao_id, usuario=""):
    """Gera DO a partir de expedição WMS (RFC-9008).

    Estoque NÃO é movido aqui — baixa B2B ocorre no depart da DO.
    """
    import wms_shipping
    sh = wms_shipping.get_expedicao(expedicao_id)
    if not sh:
        raise ValueError("expedição não encontrada")
    if sh.get("status") not in ("dispatched", "completed", "loading", "packing"):
        raise ValueError("expedição ainda não está pronta para entrega")

    existing = find_by_expedicao(sh["id"])
    if existing:
        return existing

    itens = []
    for ln in sh.get("linhas") or []:
        if ln.get("inspecao") == "rejected" or ln.get("status") == "short":
            continue
        itens.append({
            "produto_id": ln.get("produto_id") or "",
            "produto": ln.get("produto") or "item",
            "qtd": float(ln.get("qtd_conferida") or ln.get("qtd_esperada") or 1),
        })
    if not itens:
        itens = [{"produto": "carga", "qtd": 1}]

    return create_order({
        "origem_tipo": "expedicao_wms",
        "origem_ref": sh.get("documento_ref") or sh.get("id"),
        "parceiro": sh.get("parceiro") or "Cliente",
        "fonte": sh.get("armazem") or "DC-01",
        "expedicao_id": sh.get("id"),
        "motorista": sh.get("motorista") or "",
        "veiculo": sh.get("veiculo") or "",
        "paradas": [{
            "rotulo": "Destino",
            "address_type": "SHIPPING",
            "endereco": "",
            "contato": sh.get("parceiro") or "",
            "itens": itens,
        }],
        "observacao": f"Gerada de {sh.get('id')} (WMS despacho — sem baixa de estoque)",
    }, usuario=usuario)


def ensure_from_shipping(expedicao_id, usuario=""):
    """Idempotente: retorna (order, created:bool)."""
    existing = find_by_expedicao(expedicao_id)
    if existing:
        return existing, False
    return create_from_shipping(expedicao_id, usuario=usuario), True


def _find(data, oid):
    key = str(oid or "").strip().upper()
    for i, r in enumerate(data.get("orders") or []):
        if str(r.get("id") or "").upper() == key:
            return i, r
    return None, None


def set_priority(oid, prioridade, usuario=""):
    """Altera prioridade operacional (RFC-18102) sem mudar status."""
    prio = str(prioridade or "").strip().lower()
    if prio not in PRIORITIES:
        raise ValueError("prioridade inválida")
    data = _load_raw()
    idx, row = _find(data, oid)
    if row is None:
        raise ValueError("entrega não encontrada")
    if row.get("status") in ("completed", "cancelled"):
        raise ValueError("entrega fechada")
    row["prioridade"] = prio
    row["atualizado_em"] = _now()
    hist = list(row.get("historico") or [])
    hist.append(_hist(row.get("status") or "draft", usuario, f"prioridade {prio}"))
    row["historico"] = hist
    data["orders"][idx] = row
    _save(data, changed=row)
    return _enrich(row)


def update_stop(oid, parada, payload, usuario=""):
    data = _load_raw()
    idx, row = _find(data, oid)
    if row is None:
        raise ValueError("entrega não encontrada")
    if row.get("status") in ("completed", "cancelled"):
        raise ValueError("entrega fechada")

    found = None
    for st in row.get("paradas") or []:
        if int(st.get("parada") or 0) == int(parada):
            found = st
            break
    if found is None:
        raise ValueError("parada não encontrada")

    body = dict(payload or {})
    for field in ("rotulo", "endereco", "cidade", "uf", "cep", "contato", "telefone"):
        if body.get(field) is not None:
            found[field] = str(body.get(field) or "").strip()
    if body.get("address_type") is not None:
        found["address_type"] = str(body.get("address_type") or "SHIPPING").upper()
    if body.get("status") is not None:
        st = str(body.get("status")).strip().lower()
        if st not in STOP_STATUSES:
            raise ValueError("status de parada inválido")
        found["status"] = st

    row["atualizado_em"] = _now()
    data["orders"][idx] = row
    _save(data, changed=row)
    return _enrich(row)


def _pedido_b2b_from_do(order):
    """Resolve pedido B2B a partir da origem da DO."""
    if str((order or {}).get("origem_tipo") or "") != "pedido_venda":
        return None
    ref = str((order or {}).get("origem_ref") or "").strip()
    if not ref:
        return None
    try:
        import pedidos_b2b_store
        for p in pedidos_b2b_store.listar() or []:
            if str(p.get("numero") or "") == ref or str(p.get("id") or "") == ref:
                return p
    except Exception:
        return None
    return None


def apply_sales_stock_move(order, usuario=""):
    """
    RFC Sales: stock move na saída da entrega (não no faturar).
    Idempotente via pedido.estoque_baixado (persiste no COBOL do pedido).
    """
    row = dict(order or {})
    if str(row.get("origem_tipo") or "") != "pedido_venda":
        return {"skipped": True, "reason": "origem nao e pedido_venda"}

    pedido = _pedido_b2b_from_do(row)
    if not pedido:
        raise ValueError("pedido B2B da entrega não encontrado para baixa de estoque")

    import inventory_mvp
    import sales_reservation

    venda_ref = "do-" + str(row.get("id") or "")
    # idempotência: já existe movimento sale com este ref
    try:
        for m in inventory_mvp.load_movements() or []:
            if (
                str(m.get("ref_tipo") or "") == "venda"
                and str(m.get("ref_id") or "") == venda_ref
            ):
                sales_reservation.consume_for_order(pedido.get("id"))
                return {
                    "already": True,
                    "entrega_id": row.get("id"),
                    "pedido_id": pedido.get("id"),
                }
    except Exception:
        pass

    linhas = []
    for st in row.get("paradas") or []:
        for it in st.get("itens") or []:
            pid = str(it.get("produto_id") or "").strip()
            if not pid:
                continue
            try:
                qtd = float(it.get("qtd") or 0)
            except (TypeError, ValueError):
                qtd = 0
            if qtd <= 0:
                continue
            linhas.append({
                "id": pid,
                "produto": it.get("produto") or "",
                "qtd": qtd,
            })
    if not linhas:
        for it in (pedido.get("itens") or []):
            pid = str(it.get("prod_id") or it.get("produto_id") or "").strip()
            if not pid:
                continue
            linhas.append({
                "id": pid,
                "produto": it.get("produto") or "",
                "qtd": it.get("qtd") or 0,
                "preco": it.get("preco"),
            })
    if not linhas:
        raise ValueError("entrega/pedido sem linhas para baixa de estoque")

    eid = (
        pedido.get("estabelecimento_id")
        or row.get("estabelecimento_id")
        or ""
    )
    inv = inventory_mvp.inventory_apply_sale(
        eid, linhas, venda_id=venda_ref,
    )
    sales_reservation.consume_for_order(pedido.get("id"))

    return {
        "ok": True,
        "entrega_id": row.get("id"),
        "pedido_id": pedido.get("id"),
        "inventory": inv,
    }


def transition(oid, action, usuario="", motivo="", **extra):
    data = _load_raw()
    idx, row = _find(data, oid)
    if row is None:
        raise ValueError("entrega não encontrada")

    act = str(action or "").strip().lower()
    cur = row.get("status") or "draft"
    nxt = TRANSITIONS.get((cur, act))
    if not nxt:
        raise ValueError(f"ação '{act}' não permitida no status '{cur}'")

    if act == "cancel":
        reason = str(motivo or "").strip()
        if not reason:
            raise ValueError("motivo obrigatório para cancelar")
        row["cancelamento_motivo"] = reason
        nota = reason
    elif act == "assign":
        if extra.get("recurso_id") is not None:
            row["recurso_id"] = str(extra.get("recurso_id") or "").strip()
        if extra.get("motorista") is not None:
            row["motorista"] = str(extra.get("motorista") or "").strip()
        if extra.get("veiculo") is not None:
            row["veiculo"] = str(extra.get("veiculo") or "").strip()
        if not (row.get("motorista") or row.get("recurso_id")):
            raise ValueError("informe motorista ou recurso para atribuir")
        nota = f"atribuído {row.get('motorista') or row.get('recurso_id')}"
    elif act == "deliver":
        # marca paradas pendentes como delivered
        for st in row.get("paradas") or []:
            if st.get("status") in ("pending", "en_route", "arrived"):
                st["status"] = "delivered"
        nota = "entregue"
    else:
        nota = str(motivo or act).strip()

    if extra.get("data_agendada") is not None:
        row["data_agendada"] = str(extra.get("data_agendada") or "").strip()
    if extra.get("janela") is not None:
        row["janela"] = str(extra.get("janela") or "").strip()

    # RFC-18007 — conclusão exige POD confirmado (salvo force=True)
    if act == "complete":
        try:
            import delivery_pod
            delivery_pod.assert_can_complete(
                row["id"], force=bool(extra.get("force")),
            )
        except ValueError:
            raise
        except Exception:
            pass

    # RFC Sales — stock move na saída (depart), não no faturar comercial
    stock_info = None
    if act == "depart" and str(row.get("origem_tipo") or "") == "pedido_venda":
        stock_info = apply_sales_stock_move(row, usuario=usuario)
        if stock_info.get("ok"):
            row["estoque_baixado"] = True
            row["estoque_baixado_em"] = _now()
            row["estoque_baixado_por"] = str(usuario or "")
            nota = (nota + " · estoque baixado").strip(" ·")

    row["status"] = nxt
    row["atualizado_em"] = _now()
    hist = list(row.get("historico") or [])
    hist.append(_hist(nxt, usuario, nota))
    row["historico"] = hist
    data["orders"][idx] = row
    _save(data, changed=row)

    enriched = _enrich(row)
    if stock_info:
        enriched["stock_move"] = stock_info
    # RFC-18006 — tracking best-effort (não bloqueia ciclo da DO)
    try:
        import delivery_tracking
        delivery_tracking.sync_from_order(
            enriched, action=act, usuario=usuario, nota=nota,
        )
    except Exception:
        pass
    # RFC-18007 — cria PODs waiting ao marcar entregue
    if act == "deliver":
        try:
            import delivery_pod
            delivery_pod.on_order_delivered(enriched, usuario=usuario)
        except Exception:
            pass
    return enriched
