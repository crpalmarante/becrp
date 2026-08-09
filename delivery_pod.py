"""
Delivery — Proof of Delivery (RFC-18007 MVP).

Evidência de entrega por parada: receptor, assinatura, fotos, docs, notas.
Não agenda, não despacha, não substitui fiscal, não move estoque.
Fonte: dados/delivery_pod.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import delivery_orders

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "delivery_pod.json")

STATUSES = {
    "created": "Criado",
    "waiting": "Aguardando confirmação",
    "confirmed": "Confirmado",
    "rejected": "Rejeitado",
    "reviewed": "Revisado",
    "closed": "Fechado",
}

TRANSITIONS = {
    ("created", "wait"): "waiting",
    ("created", "confirm"): "confirmed",
    ("created", "reject"): "rejected",
    ("waiting", "confirm"): "confirmed",
    ("waiting", "reject"): "rejected",
    ("confirmed", "review"): "reviewed",
    ("rejected", "review"): "reviewed",
    ("reviewed", "close"): "closed",
    ("confirmed", "close"): "closed",
    ("rejected", "close"): "closed",
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load_raw():
    if not os.path.exists(DATA_FILE):
        return ensure_seed()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("pods"), list):
        return ensure_seed()
    if not data["pods"]:
        return ensure_seed()
    data.setdefault("seq", len(data["pods"]))
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("pods") or [])
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
    seq = int(data.get("seq") or 0) + 1
    data["seq"] = seq
    return f"POD-{datetime.now().strftime('%Y%m%d')}-{seq:04d}"


def ensure_seed():
    delivery_orders.ensure_seed()
    now = _now()
    order = delivery_orders.get_order("DO-SEED-0001") or {}
    parada = 1
    if order.get("paradas"):
        parada = int((order["paradas"][0] or {}).get("parada") or 1)
    row = {
        "id": "POD-SEED-0001",
        "entrega_id": "DO-SEED-0001",
        "parada": parada,
        "status": "waiting",
        "receptor_nome": "",
        "receptor_doc": "",
        "entregador": order.get("motorista") or "Carlos Motorista",
        "confirmado_em": "",
        "lat": None,
        "lng": None,
        "assinatura": "",
        "fotos": [],
        "documentos": [],
        "observacao": "Seed — aguardando confirmação",
        "motivo_rejeicao": "",
        "itens_ok": True,
        "historico": [_hist("waiting", "seed", "seed")],
        "evidencias": [],
        "criado_em": now,
        "atualizado_em": now,
        "imutavel": False,
    }
    data = {"seq": 1, "atualizado_em": now, "pods": [row], "total": 1}
    _save(data)
    return data


def meta():
    return {
        "statuses": [{"id": k, "label": v} for k, v in STATUSES.items()],
        "required_fields": ["receptor_nome", "entregador"],
        "optional_evidence": ["assinatura", "fotos", "documentos", "lat", "lng", "observacao"],
    }


def _enrich(row, order=None):
    out = dict(row)
    out["status_label"] = STATUSES.get(out.get("status"), out.get("status") or "")
    oid = out.get("entrega_id")
    if order is None and oid:
        order = delivery_orders.get_order(oid)
    if order:
        out["parceiro"] = order.get("parceiro") or ""
        out["fonte"] = order.get("fonte") or ""
        out["order_status"] = order.get("status")
        out["order_status_label"] = order.get("status_label") or order.get("status")
        stop = None
        for st in order.get("paradas") or []:
            if int(st.get("parada") or 0) == int(out.get("parada") or 0):
                stop = st
                break
        if stop:
            out["parada_rotulo"] = stop.get("rotulo") or ""
            out["parada_endereco"] = stop.get("endereco") or ""
            out["parada_status"] = stop.get("status")
            out["parada_status_label"] = stop.get("status_label") or stop.get("status")
    out["fotos_count"] = len(out.get("fotos") or [])
    out["documentos_count"] = len(out.get("documentos") or [])
    out["tem_assinatura"] = bool(out.get("assinatura"))
    out["acoes"] = _actions(out)
    return out


def _actions(row):
    st = row.get("status")
    acts = []
    if st in ("created", "waiting"):
        acts.extend(["capture", "confirm", "reject"])
    if st in ("confirmed", "rejected"):
        acts.append("review")
    if st in ("confirmed", "rejected", "reviewed"):
        acts.append("close")
    return acts


def _find(data, pod_id=None, entrega_id=None, parada=None):
    if pod_id:
        key = str(pod_id or "").strip().upper()
        for i, r in enumerate(data.get("pods") or []):
            if str(r.get("id") or "").upper() == key:
                return i, r
    if entrega_id is not None and parada is not None:
        eid = str(entrega_id).strip().upper()
        pn = int(parada)
        for i, r in enumerate(data.get("pods") or []):
            if str(r.get("entrega_id") or "").upper() == eid and int(r.get("parada") or 0) == pn:
                return i, r
    return None, None


def list_pods(q=None, status=None, entrega_id=None):
    raw = _load_raw()
    rows = [_enrich(r) for r in raw.get("pods") or []]
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r for r in rows
            if qq in (r.get("id") or "").lower()
            or qq in (r.get("entrega_id") or "").lower()
            or qq in (r.get("parceiro") or "").lower()
            or qq in (r.get("receptor_nome") or "").lower()
        ]
    if status:
        rows = [r for r in rows if r.get("status") == status]
    if entrega_id:
        key = str(entrega_id).strip().upper()
        rows = [r for r in rows if str(r.get("entrega_id") or "").upper() == key]
    rows.sort(key=lambda r: (r.get("entrega_id") or "", int(r.get("parada") or 0)))
    return {
        "pods": rows,
        "total": len(raw.get("pods") or []),
        "filtrado": len(rows),
        "atualizado_em": raw.get("atualizado_em"),
    }


def get_pod(pod_id):
    raw = _load_raw()
    _, row = _find(raw, pod_id=pod_id)
    return _enrich(row) if row else None


def summary(entrega_id):
    order = delivery_orders.get_order(entrega_id)
    if not order:
        raise ValueError("entrega não encontrada")
    pods = list_pods(entrega_id=order["id"])["pods"]
    stops = order.get("paradas") or []
    required = len(stops) or 1
    confirmed = sum(1 for p in pods if p.get("status") in ("confirmed", "reviewed", "closed"))
    rejected = sum(1 for p in pods if p.get("status") == "rejected")
    pending = sum(1 for p in pods if p.get("status") in ("created", "waiting"))
    return {
        "entrega_id": order["id"],
        "paradas": len(stops),
        "pods": len(pods),
        "required": required,
        "confirmed": confirmed,
        "rejected": rejected,
        "pending": pending,
        "completo": confirmed >= required and rejected == 0 and pending == 0,
        "pode_concluir": confirmed >= required and rejected == 0,
        "pods_list": pods,
    }


def ensure_for_order(entrega_id, usuario=""):
    """Cria POD waiting para cada parada sem POD."""
    order = delivery_orders.get_order(entrega_id)
    if not order:
        raise ValueError("entrega não encontrada")
    stops = order.get("paradas") or [{"parada": 1}]
    raw = _load_raw()
    created = []
    for st in stops:
        pn = int(st.get("parada") or 1)
        _, existing = _find(raw, entrega_id=order["id"], parada=pn)
        if existing:
            continue
        now = _now()
        row = {
            "id": _next_id(raw),
            "entrega_id": order["id"],
            "parada": pn,
            "status": "waiting",
            "receptor_nome": "",
            "receptor_doc": "",
            "entregador": order.get("motorista") or "",
            "confirmado_em": "",
            "lat": None,
            "lng": None,
            "assinatura": "",
            "fotos": [],
            "documentos": [],
            "observacao": "",
            "motivo_rejeicao": "",
            "itens_ok": True,
            "historico": [_hist("waiting", usuario, "criado na entrega")],
            "evidencias": [],
            "criado_em": now,
            "atualizado_em": now,
            "imutavel": False,
        }
        raw.setdefault("pods", []).append(row)
        created.append(row)
    if created:
        _save(raw)
    return {
        "entrega_id": order["id"],
        "criados": len(created),
        "pods": list_pods(entrega_id=order["id"])["pods"],
    }


def create_pod(body, usuario=""):
    body = body or {}
    eid = str(body.get("entrega_id") or "").strip().upper()
    if not eid:
        raise ValueError("entrega_id obrigatório")
    order = delivery_orders.get_order(eid)
    if not order:
        raise ValueError("entrega não encontrada")
    try:
        parada = int(body.get("parada") if body.get("parada") is not None else 1)
    except (TypeError, ValueError):
        raise ValueError("parada inválida")
    stops = {int(s.get("parada") or 0) for s in (order.get("paradas") or [])}
    if stops and parada not in stops:
        raise ValueError(f"parada {parada} não existe na entrega")

    raw = _load_raw()
    _, existing = _find(raw, entrega_id=eid, parada=parada)
    if existing:
        return _enrich(existing, order)

    now = _now()
    row = {
        "id": _next_id(raw),
        "entrega_id": eid,
        "parada": parada,
        "status": "waiting",
        "receptor_nome": str(body.get("receptor_nome") or "").strip(),
        "receptor_doc": str(body.get("receptor_doc") or "").strip(),
        "entregador": str(body.get("entregador") or order.get("motorista") or "").strip(),
        "confirmado_em": "",
        "lat": body.get("lat"),
        "lng": body.get("lng"),
        "assinatura": str(body.get("assinatura") or "").strip(),
        "fotos": list(body.get("fotos") or []),
        "documentos": list(body.get("documentos") or []),
        "observacao": str(body.get("observacao") or "").strip(),
        "motivo_rejeicao": "",
        "itens_ok": bool(body.get("itens_ok", True)),
        "historico": [_hist("waiting", usuario, "criação")],
        "evidencias": [],
        "criado_em": now,
        "atualizado_em": now,
        "imutavel": False,
    }
    raw.setdefault("pods", []).append(row)
    _save(raw)
    return _enrich(row, order)


def _append_evidence(row, tipo, ref, usuario=""):
    ev = {
        "tipo": tipo,
        "ref": ref,
        "em": _now(),
        "usuario": str(usuario or "").strip(),
    }
    evs = list(row.get("evidencias") or [])
    evs.append(ev)
    row["evidencias"] = evs
    return ev


def capture(pod_id, body=None, usuario=""):
    """Acrescenta evidências (append-only). Não fecha o POD."""
    body = body or {}
    raw = _load_raw()
    idx, row = _find(raw, pod_id=pod_id)
    if row is None:
        raise ValueError("POD não encontrado")
    if row.get("status") in ("closed",):
        raise ValueError("POD fechado")
    if row.get("imutavel") and row.get("status") in ("confirmed", "rejected", "reviewed", "closed"):
        # ainda permite anexar evidência pós-confirmação? RFC diz immutable records —
        # permitimos só em waiting/created
        if row.get("status") not in ("created", "waiting"):
            raise ValueError("POD já confirmado — evidência imutável")

    if body.get("receptor_nome") is not None:
        row["receptor_nome"] = str(body.get("receptor_nome") or "").strip()
    if body.get("receptor_doc") is not None:
        row["receptor_doc"] = str(body.get("receptor_doc") or "").strip()
    if body.get("entregador") is not None:
        row["entregador"] = str(body.get("entregador") or "").strip()
    if body.get("observacao") is not None:
        row["observacao"] = str(body.get("observacao") or "").strip()
    if body.get("itens_ok") is not None:
        row["itens_ok"] = bool(body.get("itens_ok"))
    if body.get("lat") is not None:
        try:
            row["lat"] = float(body.get("lat"))
        except (TypeError, ValueError):
            raise ValueError("lat inválida")
    if body.get("lng") is not None:
        try:
            row["lng"] = float(body.get("lng"))
        except (TypeError, ValueError):
            raise ValueError("lng inválida")

    if body.get("assinatura") is not None:
        sig = str(body.get("assinatura") or "").strip()
        row["assinatura"] = sig
        if sig:
            _append_evidence(row, "signature", sig[:80], usuario=usuario)

    for foto in body.get("fotos") or []:
        ref = str(foto or "").strip()
        if not ref:
            continue
        fotos = list(row.get("fotos") or [])
        if ref not in fotos:
            fotos.append(ref)
            row["fotos"] = fotos
            _append_evidence(row, "photo", ref, usuario=usuario)

    for doc in body.get("documentos") or []:
        ref = str(doc or "").strip()
        if not ref:
            continue
        docs = list(row.get("documentos") or [])
        if ref not in docs:
            docs.append(ref)
            row["documentos"] = docs
            _append_evidence(row, "document", ref, usuario=usuario)

    if row.get("status") == "created":
        row["status"] = "waiting"

    row["atualizado_em"] = _now()
    row.setdefault("historico", []).append(_hist(row["status"], usuario, "evidência capturada"))
    raw["pods"][idx] = row
    _save(raw)
    return _enrich(row)


def _require_confirm_fields(row):
    if not str(row.get("receptor_nome") or "").strip():
        raise ValueError("receptor_nome obrigatório para confirmar")
    if not str(row.get("entregador") or "").strip():
        raise ValueError("entregador obrigatório para confirmar")


def confirm(pod_id, body=None, usuario=""):
    body = body or {}
    # permite capturar campos no mesmo request
    if any(k in body for k in (
        "receptor_nome", "entregador", "assinatura", "fotos", "documentos",
        "observacao", "lat", "lng", "receptor_doc", "itens_ok",
    )):
        capture(pod_id, body, usuario=usuario)

    raw = _load_raw()
    idx, row = _find(raw, pod_id=pod_id)
    if row is None:
        raise ValueError("POD não encontrado")
    cur = row.get("status") or "created"
    nxt = TRANSITIONS.get((cur, "confirm"))
    if not nxt:
        raise ValueError(f"não é possível confirmar no status '{cur}'")

    _require_confirm_fields(row)
    now = _now()
    row["status"] = nxt
    row["confirmado_em"] = now
    row["imutavel"] = True
    row["atualizado_em"] = now
    row.setdefault("historico", []).append(_hist(nxt, usuario, "confirmado pelo receptor"))
    raw["pods"][idx] = row
    _save(raw)

    # atualiza parada da DO
    try:
        delivery_orders.update_stop(
            row["entrega_id"], row["parada"], {"status": "delivered"}, usuario=usuario,
        )
    except Exception:
        pass

    # tracking event
    try:
        import delivery_tracking
        delivery_tracking.add_event(
            row["entrega_id"], "delivered", usuario=usuario,
            mensagem=f"POD {row['id']} confirmado por {row.get('receptor_nome')}",
            parada=row.get("parada"),
            lat=row.get("lat"),
            lng=row.get("lng"),
        )
    except Exception:
        pass

    return _enrich(row)


def reject(pod_id, body=None, usuario=""):
    body = body or {}
    motivo = str(body.get("motivo") or body.get("motivo_rejeicao") or "").strip()
    if not motivo:
        raise ValueError("motivo obrigatório para rejeitar")

    if body.get("fotos") or body.get("observacao") or body.get("lat") is not None:
        try:
            capture(pod_id, {
                k: body[k] for k in ("fotos", "observacao", "lat", "lng", "documentos")
                if k in body
            }, usuario=usuario)
        except ValueError:
            pass

    raw = _load_raw()
    idx, row = _find(raw, pod_id=pod_id)
    if row is None:
        raise ValueError("POD não encontrado")
    cur = row.get("status") or "created"
    nxt = TRANSITIONS.get((cur, "reject"))
    if not nxt:
        raise ValueError(f"não é possível rejeitar no status '{cur}'")

    now = _now()
    row["status"] = nxt
    row["motivo_rejeicao"] = motivo
    row["imutavel"] = True
    row["atualizado_em"] = now
    if body.get("receptor_nome"):
        row["receptor_nome"] = str(body.get("receptor_nome") or "").strip()
    row.setdefault("historico", []).append(_hist(nxt, usuario, motivo))
    raw["pods"][idx] = row
    _save(raw)

    try:
        delivery_orders.update_stop(
            row["entrega_id"], row["parada"], {"status": "failed"}, usuario=usuario,
        )
    except Exception:
        pass

    try:
        import delivery_tracking
        delivery_tracking.add_event(
            row["entrega_id"], "failed", usuario=usuario,
            mensagem=f"POD {row['id']} rejeitado: {motivo}",
            parada=row.get("parada"),
        )
    except Exception:
        pass

    return _enrich(row)


def transition(pod_id, action, usuario="", motivo=""):
    act = str(action or "").strip().lower()
    if act == "confirm":
        return confirm(pod_id, {}, usuario=usuario)
    if act == "reject":
        return reject(pod_id, {"motivo": motivo}, usuario=usuario)
    if act == "capture":
        raise ValueError("use action capture com body de evidências")

    raw = _load_raw()
    idx, row = _find(raw, pod_id=pod_id)
    if row is None:
        raise ValueError("POD não encontrado")
    cur = row.get("status") or "created"
    nxt = TRANSITIONS.get((cur, act))
    if not nxt:
        raise ValueError(f"ação '{act}' não permitida no status '{cur}'")
    row["status"] = nxt
    row["atualizado_em"] = _now()
    row.setdefault("historico", []).append(_hist(nxt, usuario, motivo or act))
    raw["pods"][idx] = row
    _save(raw)
    return _enrich(row)


def on_order_delivered(order, usuario=""):
    """Hook best-effort: garante PODs waiting quando DO vai para delivered."""
    if not order or not order.get("id"):
        return None
    try:
        return ensure_for_order(order["id"], usuario=usuario)
    except Exception:
        return None


def assert_can_complete(entrega_id, force=False):
    """Bloqueia conclusão da DO se PODs obrigatórios não confirmados."""
    if force:
        return summary(entrega_id)
    sm = summary(entrega_id)
    # se não há POD ainda, cria e exige
    if sm["pods"] == 0:
        ensure_for_order(entrega_id)
        sm = summary(entrega_id)
    if not sm.get("pode_concluir"):
        raise ValueError(
            f"POD pendente: {sm['confirmed']}/{sm['required']} confirmados"
            + (f", {sm['rejected']} rejeitados" if sm["rejected"] else "")
        )
    return sm
