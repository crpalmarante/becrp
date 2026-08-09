"""
Delivery — Manifest (RFC-18105 MVP).

Pacote de execução: agrupa DOs em uma viagem (motorista + veículo + sequência).
Ponte entre planning e execução. Não move estoque.
Fonte: dados/delivery_manifest.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import delivery_dispatch
import delivery_orders
import delivery_resources
import delivery_tasks
import delivery_tracking

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "delivery_manifest.json")

STATUSES = {
    "draft": "Rascunho",
    "planning": "Planejando",
    "released": "Liberado",
    "in_progress": "Em execução",
    "completed": "Concluído",
    "closed": "Fechado",
    "archived": "Arquivado",
    "cancelled": "Cancelado",
}

ACTIVE = {"draft", "planning", "released", "in_progress"}

# ready for dispatch (WMS / DO)
READY_FOR_MANIFEST = {"ready", "assigned", "confirmed"}

TRANSITIONS = {
    ("draft", "plan"): "planning",
    ("draft", "cancel"): "cancelled",
    ("planning", "release"): "released",
    ("planning", "cancel"): "cancelled",
    ("released", "start"): "in_progress",
    ("released", "cancel"): "cancelled",
    ("in_progress", "complete"): "completed",
    ("completed", "close"): "closed",
    ("closed", "archive"): "archived",
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _load_raw():
    if not os.path.exists(DATA_FILE):
        return ensure_seed()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("manifests"), list):
        return ensure_seed()
    if not data["manifests"]:
        return ensure_seed()
    data.setdefault("seq", len(data["manifests"]))
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("manifests") or [])
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
    return f"MF-{datetime.now().strftime('%Y%m%d')}-{seq:04d}"


def ensure_seed():
    delivery_orders.ensure_seed()
    now = _now()
    row = {
        "id": "MF-SEED-0001",
        "data": _today(),
        "fonte": "DC-01",
        "status": "draft",
        "dispatch_id": "DS-SEED-0001",
        "recurso_id": "DRV-01",
        "motorista": "Carlos Motorista",
        "veiculo": "ABC1D23",
        "partida_estimada": "08:00",
        "retorno_estimado": "18:00",
        "entrega_ids": ["DO-SEED-0001"],
        "observacao": "Seed — manifesto do dia",
        "historico": [_hist("draft", "seed", "criação")],
        "cancelamento_motivo": "",
        "criado_em": now,
        "atualizado_em": now,
    }
    data = {"seq": 1, "atualizado_em": now, "manifests": [row], "total": 1}
    _save(data)
    _link_orders(row["id"], row["entrega_ids"], usuario="seed")
    return data


def _find(data, mid):
    key = str(mid or "").strip().upper()
    for i, r in enumerate(data.get("manifests") or []):
        if str(r.get("id") or "").upper() == key:
            return i, r
    return None, None


def _active_manifest_for_order(eid, exclude_mid=None):
    eid = str(eid or "").strip().upper()
    excl = str(exclude_mid or "").strip().upper()
    for r in _load_raw().get("manifests") or []:
        if r.get("status") not in ACTIVE:
            continue
        if excl and str(r.get("id") or "").upper() == excl:
            continue
        if eid in [str(x).upper() for x in (r.get("entrega_ids") or [])]:
            return r
    return None


def _link_orders(manifest_id, entrega_ids, usuario=""):
    """Grava manifesto_id nas DOs (leve)."""
    mid = str(manifest_id or "").strip().upper()
    raw = delivery_orders._load_raw()
    changed = False
    for eid in entrega_ids or []:
        eid = str(eid).strip().upper()
        idx, row = delivery_orders._find(raw, eid)
        if row is None:
            continue
        if row.get("manifesto_id") == mid:
            continue
        row["manifesto_id"] = mid
        row["atualizado_em"] = _now()
        hist = list(row.get("historico") or [])
        hist.append(delivery_orders._hist(row.get("status"), usuario, f"manifesto {mid}"))
        row["historico"] = hist
        raw["orders"][idx] = row
        changed = True
    if changed:
        delivery_orders._save(raw)


def _unlink_orders(manifest_id, entrega_ids, usuario=""):
    mid = str(manifest_id or "").strip().upper()
    raw = delivery_orders._load_raw()
    changed = False
    for eid in entrega_ids or []:
        eid = str(eid).strip().upper()
        idx, row = delivery_orders._find(raw, eid)
        if row is None:
            continue
        if str(row.get("manifesto_id") or "").upper() != mid:
            continue
        row["manifesto_id"] = ""
        row["atualizado_em"] = _now()
        hist = list(row.get("historico") or [])
        hist.append(delivery_orders._hist(row.get("status"), usuario, f"saiu do manifesto {mid}"))
        row["historico"] = hist
        raw["orders"][idx] = row
        changed = True
    if changed:
        delivery_orders._save(raw)


def _normalize_ids(ids):
    if isinstance(ids, str):
        ids = [x.strip() for x in ids.split(",") if x.strip()]
    return [str(x).strip().upper() for x in (ids or []) if str(x).strip()]


def _stop_lines(order):
    lines = []
    for st in order.get("paradas") or []:
        lines.append({
            "parada": st.get("parada"),
            "rotulo": st.get("rotulo"),
            "endereco": st.get("endereco"),
            "cidade": st.get("cidade"),
            "uf": st.get("uf"),
            "contato": st.get("contato"),
            "telefone": st.get("telefone"),
            "status": st.get("status"),
        })
    return lines


def checklist(row):
    """Checklist de partida antes do release."""
    items = []
    ok = True

    def add(key, label, passed, detail=""):
        nonlocal ok
        if not passed:
            ok = False
        items.append({"id": key, "label": label, "ok": bool(passed), "detail": detail})

    add("motorista", "Motorista atribuído", bool(row.get("motorista") or row.get("recurso_id")))
    add("veiculo", "Veículo atribuído", bool(row.get("veiculo")))
    ids = list(row.get("entrega_ids") or [])
    add("entregas", "Há entregas no manifesto", bool(ids), f"{len(ids)} DO(s)")

    blocked = []
    not_ready = []
    for eid in ids:
        do = delivery_orders.get_order(eid)
        if not do:
            blocked.append(eid)
            continue
        st = do.get("status")
        if st in ("cancelled", "failed"):
            blocked.append(eid)
        elif st not in ("ready", "assigned"):
            not_ready.append(f"{eid}:{st}")

    add("bloqueadas", "Nenhuma entrega bloqueada", not blocked, ", ".join(blocked) if blocked else "")
    add(
        "prontas",
        "Entregas prontas para despacho (ready/assigned)",
        not not_ready,
        ", ".join(not_ready) if not_ready else "",
    )
    return {"ok": ok, "itens": items}


def _enrich(row):
    out = dict(row)
    out["status_label"] = STATUSES.get(out.get("status"), out.get("status") or "")
    ids = list(out.get("entrega_ids") or [])
    out["entregas_count"] = len(ids)
    entregas = []
    paradas_total = 0
    for i, eid in enumerate(ids, start=1):
        do = delivery_orders.get_order(eid)
        if not do:
            entregas.append({"seq": i, "id": eid, "missing": True})
            continue
        stops = _stop_lines(do)
        paradas_total += len(stops)
        entregas.append({
            "seq": i,
            "id": do["id"],
            "parceiro": do.get("parceiro"),
            "status": do.get("status"),
            "status_label": do.get("status_label"),
            "prioridade": do.get("prioridade"),
            "prioridade_label": do.get("prioridade_label"),
            "janela": do.get("janela"),
            "data_agendada": do.get("data_agendada"),
            "paradas_count": do.get("paradas_count") or len(stops),
            "paradas": stops,
            "endereco": (stops[0].get("endereco") if stops else "") or "",
            "cidade": (stops[0].get("cidade") if stops else "") or "",
            "contato": (stops[0].get("contato") if stops else "") or "",
            "telefone": (stops[0].get("telefone") if stops else "") or "",
        })
    out["entregas"] = entregas
    out["paradas_count"] = paradas_total
    out["checklist"] = checklist(out)
    st = out.get("status")
    out["acoes"] = [a for (fr, a), _to in TRANSITIONS.items() if fr == st]
    if st in ("draft", "planning"):
        out["acoes"] = list(dict.fromkeys(
            ["add_entregas", "remove_entregas", "assign", "reorder"] + out["acoes"]
        ))
    return out


def meta():
    data = _load_raw()
    return {
        "total": len(data.get("manifests") or []),
        "status": STATUSES,
        "refresh_seconds": 45,
        "nota": "Manifesto = pacote de execução da viagem. Sem inventário.",
        "atualizado_em": data.get("atualizado_em"),
    }


def candidates(fonte=None, data=None):
    """DOs elegíveis para incluir em manifesto (não em outro ativo)."""
    out = delivery_orders.list_orders(fonte=fonte)
    rows = []
    day = str(data or "").strip()
    for o in out.get("orders") or []:
        if o.get("status") not in READY_FOR_MANIFEST:
            continue
        if day and str(o.get("data_agendada") or "")[:10] != day:
            continue
        active = _active_manifest_for_order(o.get("id"))
        if active:
            continue
        rows.append({
            "id": o.get("id"),
            "parceiro": o.get("parceiro"),
            "status": o.get("status"),
            "status_label": o.get("status_label"),
            "prioridade": o.get("prioridade"),
            "prioridade_label": o.get("prioridade_label"),
            "janela": o.get("janela"),
            "data_agendada": o.get("data_agendada"),
            "motorista": o.get("motorista") or "",
            "fonte": o.get("fonte"),
        })
    return {"filtrado": len(rows), "orders": rows}


def list_manifests(q=None, status=None, fonte=None, data=None):
    rows = list(_load_raw().get("manifests") or [])
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r for r in rows
            if qq in str(r.get("id") or "").lower()
            or qq in str(r.get("motorista") or "").lower()
            or qq in str(r.get("veiculo") or "").lower()
            or any(qq in str(e).lower() for e in (r.get("entrega_ids") or []))
        ]
    if status:
        st = str(status).strip().lower()
        if st not in STATUSES:
            raise ValueError("status inválido")
        rows = [r for r in rows if r.get("status") == st]
    if fonte:
        fk = str(fonte).strip().upper()
        rows = [r for r in rows if str(r.get("fonte") or "").upper() == fk]
    if data:
        rows = [r for r in rows if r.get("data") == str(data).strip()]
    order = {s: i for i, s in enumerate(STATUSES)}
    rows.sort(key=lambda r: (order.get(r.get("status"), 99), str(r.get("id") or "")))
    fontes = sorted({
        str(r.get("fonte") or "").upper()
        for r in (_load_raw().get("manifests") or [])
        if r.get("fonte")
    })
    if "DC-01" not in fontes:
        fontes.insert(0, "DC-01")
    return {
        "total": len(_load_raw().get("manifests") or []),
        "filtrado": len(rows),
        "status_opcoes": STATUSES,
        "fontes": fontes,
        "manifests": [_enrich(r) for r in rows],
        "meta": meta(),
    }


def get_manifest(mid):
    key = str(mid or "").strip().upper()
    for r in _load_raw().get("manifests") or []:
        if str(r.get("id") or "").upper() == key:
            return _enrich(r)
    return None


def document(mid):
    """Documento imprimível / digital do manifesto."""
    m = get_manifest(mid)
    if not m:
        raise ValueError("manifesto não encontrado")
    linhas = []
    for e in m.get("entregas") or []:
        if e.get("missing"):
            continue
        linhas.append({
            "seq": e.get("seq"),
            "entrega_id": e.get("id"),
            "cliente": e.get("parceiro"),
            "endereco": e.get("endereco"),
            "cidade": e.get("cidade"),
            "contato": e.get("contato"),
            "telefone": e.get("telefone"),
            "janela": e.get("janela"),
            "status": e.get("status_label") or e.get("status"),
            "observacao": "",
        })
    return {
        "documento": {
            "titulo": "Manifesto de Entrega",
            "manifesto_id": m.get("id"),
            "data": m.get("data"),
            "fonte": m.get("fonte"),
            "motorista": m.get("motorista"),
            "veiculo": m.get("veiculo"),
            "dispatch_id": m.get("dispatch_id") or "",
            "partida_estimada": m.get("partida_estimada") or "",
            "retorno_estimado": m.get("retorno_estimado") or "",
            "status": m.get("status_label"),
            "observacao": m.get("observacao") or "",
            "linhas": linhas,
            "total_entregas": len(linhas),
            "gerado_em": _now(),
        },
        "manifest": m,
    }


def create_manifest(payload, usuario=""):
    body = dict(payload or {})
    data = _load_raw()
    mid = str(body.get("id") or "").strip().upper() or _next_id(data)
    if any(str(r.get("id") or "").upper() == mid for r in data["manifests"]):
        raise ValueError(f"já existe manifesto {mid}")

    ids = _normalize_ids(body.get("entrega_ids"))
    for eid in ids:
        if not delivery_orders.get_order(eid):
            raise ValueError(f"entrega não encontrada: {eid}")
        other = _active_manifest_for_order(eid)
        if other:
            raise ValueError(f"{eid} já está no manifesto ativo {other.get('id')}")

    dispatch_id = str(body.get("dispatch_id") or "").strip().upper()
    if dispatch_id:
        ds = delivery_dispatch.get_dispatch(dispatch_id)
        if not ds:
            raise ValueError(f"despacho não encontrado: {dispatch_id}")
        if not ids:
            ids = _normalize_ids(ds.get("entrega_ids"))

    recurso_id = str(body.get("recurso_id") or "").strip().upper()
    motorista = str(body.get("motorista") or "").strip()
    veiculo = str(body.get("veiculo") or "").strip()
    if recurso_id:
        rec = delivery_resources.get_recurso(recurso_id)
        if not rec:
            raise ValueError(f"recurso não encontrado: {recurso_id}")
        if not motorista and rec.get("tipo") == "driver":
            motorista = rec.get("nome") or ""
        if not veiculo and rec.get("placa"):
            veiculo = rec.get("placa") or ""

    # herda do dispatch se vazio
    if dispatch_id and delivery_dispatch.get_dispatch(dispatch_id):
        ds = delivery_dispatch.get_dispatch(dispatch_id)
        motorista = motorista or ds.get("motorista") or ""
        veiculo = veiculo or ds.get("veiculo") or ""
        recurso_id = recurso_id or ds.get("recurso_id") or ""

    row = {
        "id": mid,
        "data": str(body.get("data") or _today()),
        "fonte": str(body.get("fonte") or "DC-01").strip().upper(),
        "status": "draft",
        "dispatch_id": dispatch_id,
        "recurso_id": recurso_id,
        "motorista": motorista,
        "veiculo": veiculo,
        "partida_estimada": str(body.get("partida_estimada") or "").strip(),
        "retorno_estimado": str(body.get("retorno_estimado") or "").strip(),
        "entrega_ids": ids,
        "observacao": str(body.get("observacao") or "").strip(),
        "historico": [_hist("draft", usuario, "criação")],
        "cancelamento_motivo": "",
        "criado_em": _now(),
        "atualizado_em": _now(),
    }
    data["manifests"].append(row)
    _save(data)
    if ids:
        _link_orders(mid, ids, usuario=usuario)
    return _enrich(row)


def add_entregas(mid, entrega_ids, usuario=""):
    data = _load_raw()
    idx, row = _find(data, mid)
    if row is None:
        raise ValueError("manifesto não encontrado")
    if row.get("status") not in ("draft", "planning"):
        raise ValueError("só é possível incluir entregas em draft/planning")

    ids = _normalize_ids(entrega_ids)
    if not ids:
        raise ValueError("informe entrega_ids")
    cur = list(row.get("entrega_ids") or [])
    added = []
    for eid in ids:
        if not delivery_orders.get_order(eid):
            raise ValueError(f"entrega não encontrada: {eid}")
        other = _active_manifest_for_order(eid, exclude_mid=mid)
        if other:
            raise ValueError(f"{eid} já está no manifesto ativo {other.get('id')}")
        do = delivery_orders.get_order(eid)
        if do.get("status") not in READY_FOR_MANIFEST:
            raise ValueError(f"{eid} status {do.get('status')} não elegível")
        if eid not in cur:
            cur.append(eid)
            added.append(eid)
    row["entrega_ids"] = cur
    row["atualizado_em"] = _now()
    hist = list(row.get("historico") or [])
    hist.append(_hist(row.get("status"), usuario, f"add {', '.join(added) or '—'}"))
    row["historico"] = hist
    data["manifests"][idx] = row
    _save(data)
    if added:
        _link_orders(mid, added, usuario=usuario)
    return _enrich(row)


def remove_entregas(mid, entrega_ids, usuario=""):
    data = _load_raw()
    idx, row = _find(data, mid)
    if row is None:
        raise ValueError("manifesto não encontrado")
    if row.get("status") not in ("draft", "planning"):
        raise ValueError("só é possível remover entregas em draft/planning")

    ids = set(_normalize_ids(entrega_ids))
    if not ids:
        raise ValueError("informe entrega_ids")
    cur = list(row.get("entrega_ids") or [])
    removed = [e for e in cur if e in ids]
    row["entrega_ids"] = [e for e in cur if e not in ids]
    row["atualizado_em"] = _now()
    hist = list(row.get("historico") or [])
    hist.append(_hist(row.get("status"), usuario, f"remove {', '.join(removed)}"))
    row["historico"] = hist
    data["manifests"][idx] = row
    _save(data)
    if removed:
        _unlink_orders(mid, removed, usuario=usuario)
    return _enrich(row)


def reorder(mid, entrega_ids, usuario=""):
    data = _load_raw()
    idx, row = _find(data, mid)
    if row is None:
        raise ValueError("manifesto não encontrado")
    if row.get("status") not in ("draft", "planning"):
        raise ValueError("só é possível reordenar em draft/planning")
    ids = _normalize_ids(entrega_ids)
    cur = set(row.get("entrega_ids") or [])
    if set(ids) != cur:
        raise ValueError("entrega_ids deve conter exatamente as mesmas entregas")
    row["entrega_ids"] = ids
    row["atualizado_em"] = _now()
    hist = list(row.get("historico") or [])
    hist.append(_hist(row.get("status"), usuario, "reordenou sequência"))
    row["historico"] = hist
    data["manifests"][idx] = row
    _save(data)
    return _enrich(row)


def assign(mid, usuario="", motorista="", veiculo="", recurso_id=""):
    data = _load_raw()
    idx, row = _find(data, mid)
    if row is None:
        raise ValueError("manifesto não encontrado")
    if row.get("status") not in ("draft", "planning", "released"):
        raise ValueError("não é possível atribuir neste status")

    rid = str(recurso_id or "").strip().upper()
    if rid:
        rec = delivery_resources.get_recurso(rid)
        if not rec:
            raise ValueError(f"recurso não encontrado: {rid}")
        row["recurso_id"] = rid
        if rec.get("tipo") == "driver" and not motorista:
            motorista = rec.get("nome") or row.get("motorista") or ""
        if rec.get("placa") and not veiculo:
            veiculo = rec.get("placa") or row.get("veiculo") or ""
    if motorista is not None and str(motorista).strip() != "":
        row["motorista"] = str(motorista).strip()
    if veiculo is not None and str(veiculo).strip() != "":
        row["veiculo"] = str(veiculo).strip()
    if not (row.get("motorista") or row.get("recurso_id")):
        raise ValueError("informe motorista ou recurso")

    # propaga para DOs
    for eid in row.get("entrega_ids") or []:
        do = delivery_orders.get_order(eid)
        if not do:
            continue
        try:
            if do.get("status") == "ready":
                delivery_orders.transition(
                    eid, "assign", usuario=usuario,
                    motorista=row.get("motorista"),
                    veiculo=row.get("veiculo"),
                    recurso_id=row.get("recurso_id"),
                )
            elif do.get("status") == "assigned":
                # atualiza recurso sem mudar status
                raw = delivery_orders._load_raw()
                i2, r2 = delivery_orders._find(raw, eid)
                if r2:
                    r2["motorista"] = row.get("motorista") or ""
                    r2["veiculo"] = row.get("veiculo") or ""
                    r2["recurso_id"] = row.get("recurso_id") or ""
                    r2["atualizado_em"] = _now()
                    raw["orders"][i2] = r2
                    delivery_orders._save(raw)
        except ValueError:
            pass

    if row.get("status") == "draft":
        row["status"] = "planning"
        nota = f"atribuído → planning · {row.get('motorista') or row.get('recurso_id')}"
    else:
        nota = f"atribuído {row.get('motorista') or row.get('recurso_id')}"

    row["atualizado_em"] = _now()
    hist = list(row.get("historico") or [])
    hist.append(_hist(row.get("status"), usuario, nota))
    row["historico"] = hist
    data["manifests"][idx] = row
    _save(data)
    return _enrich(row)


def transition(mid, action, usuario="", motivo="", **extra):
    data = _load_raw()
    idx, row = _find(data, mid)
    if row is None:
        raise ValueError("manifesto não encontrado")

    act = str(action or "").strip().lower()
    if act == "assign":
        return assign(
            mid, usuario=usuario,
            motorista=extra.get("motorista") or "",
            veiculo=extra.get("veiculo") or "",
            recurso_id=extra.get("recurso_id") or "",
        )
    if act == "add_entregas":
        return add_entregas(mid, extra.get("entrega_ids"), usuario=usuario)
    if act == "remove_entregas":
        return remove_entregas(mid, extra.get("entrega_ids"), usuario=usuario)
    if act == "reorder":
        return reorder(mid, extra.get("entrega_ids"), usuario=usuario)

    cur = row.get("status") or "draft"
    nxt = TRANSITIONS.get((cur, act))
    if not nxt:
        raise ValueError(f"ação '{act}' não permitida no status '{cur}'")

    if act == "cancel":
        reason = str(motivo or "").strip()
        if not reason:
            raise ValueError("motivo obrigatório")
        row["cancelamento_motivo"] = reason
        _unlink_orders(mid, row.get("entrega_ids") or [], usuario=usuario)
        nota = reason
    elif act == "plan":
        nota = "planejando"
    elif act == "release":
        chk = checklist(row)
        if not chk["ok"]:
            fails = [i["label"] for i in chk["itens"] if not i["ok"]]
            raise ValueError("checklist incompleto: " + "; ".join(fails))
        for eid in row.get("entrega_ids") or []:
            try:
                delivery_tasks.generate_from_order(eid, usuario=usuario)
            except ValueError:
                pass
            try:
                delivery_tracking.ensure_track(eid, usuario=usuario)
            except ValueError:
                pass
        if row.get("recurso_id"):
            try:
                delivery_resources.set_status(row["recurso_id"], "busy", usuario=usuario)
            except ValueError:
                pass
        nota = "liberado para execução"
    elif act == "start":
        for eid in row.get("entrega_ids") or []:
            do = delivery_orders.get_order(eid)
            if do and do.get("status") == "assigned":
                try:
                    delivery_orders.transition(eid, "depart", usuario=usuario)
                except ValueError:
                    pass
        nota = "viagem iniciada"
    elif act == "complete":
        nota = "viagem concluída"
    elif act == "close":
        if row.get("recurso_id"):
            try:
                delivery_resources.set_status(row["recurso_id"], "available", usuario=usuario)
            except ValueError:
                pass
        nota = "fechado"
    elif act == "archive":
        nota = "arquivado"
    else:
        nota = str(motivo or act).strip()

    row["status"] = nxt
    row["atualizado_em"] = _now()
    hist = list(row.get("historico") or [])
    hist.append(_hist(nxt, usuario, nota))
    row["historico"] = hist
    data["manifests"][idx] = row
    _save(data)
    return _enrich(row)


def action(mid, action_name, usuario="", **kwargs):
    return transition(mid, action_name, usuario=usuario, **kwargs)
