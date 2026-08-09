"""
Delivery — Trip (RFC-18106 MVP).

Execução física de um Manifest liberado.
Manifest = planning; Trip = execution. Não move estoque.
Fonte: dados/delivery_trips.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import delivery_manifest
import delivery_orders
import delivery_tracking

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "delivery_trips.json")

STATUSES = {
    "ready": "Pronto",
    "started": "Partiu",
    "in_progress": "Em andamento",
    "paused": "Pausado",
    "completed": "Concluído",
    "closed": "Fechado",
    "cancelled": "Cancelado",
}

ACTIVE = {"ready", "started", "in_progress", "paused"}

STOP_STATUSES = {
    "pending": "Pendente",
    "current": "Atual",
    "arrived": "No cliente",
    "servicing": "Em atendimento",
    "completed": "Concluída",
    "skipped": "Pulado",
    "failed": "Falhou",
}

TRANSITIONS = {
    ("ready", "start"): "started",
    ("ready", "cancel"): "cancelled",
    ("started", "progress"): "in_progress",
    ("started", "pause"): "paused",
    ("started", "complete"): "completed",
    ("started", "cancel"): "cancelled",
    ("in_progress", "pause"): "paused",
    ("in_progress", "complete"): "completed",
    ("in_progress", "cancel"): "cancelled",
    ("paused", "resume"): "in_progress",
    ("paused", "cancel"): "cancelled",
    ("completed", "close"): "closed",
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _load_raw():
    if not os.path.exists(DATA_FILE):
        return {"seq": 0, "trips": [], "atualizado_em": _now(), "total": 0}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"seq": 0, "trips": [], "atualizado_em": _now(), "total": 0}
    data.setdefault("trips", [])
    data.setdefault("seq", len(data["trips"]))
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("trips") or [])
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
    return f"TR-{datetime.now().strftime('%Y%m%d')}-{seq:04d}"


def _find(data, tid):
    key = str(tid or "").strip().upper()
    for i, r in enumerate(data.get("trips") or []):
        if str(r.get("id") or "").upper() == key:
            return i, r
    return None, None


def _active_for_manifest(manifest_id, exclude_tid=None):
    mid = str(manifest_id or "").strip().upper()
    excl = str(exclude_tid or "").strip().upper()
    for r in _load_raw().get("trips") or []:
        if r.get("status") not in ACTIVE:
            continue
        if excl and str(r.get("id") or "").upper() == excl:
            continue
        if str(r.get("manifesto_id") or "").upper() == mid:
            return r
    return None


def _build_stops(manifest):
    stops = []
    seq = 0
    for eid in manifest.get("entrega_ids") or []:
        do = delivery_orders.get_order(eid)
        if not do:
            seq += 1
            stops.append({
                "seq": seq,
                "entrega_id": eid,
                "parada": 1,
                "parceiro": "?",
                "endereco": "",
                "cidade": "",
                "status": "pending",
                "missing": True,
            })
            continue
        paradas = do.get("paradas") or [{}]
        for st in paradas:
            seq += 1
            stops.append({
                "seq": seq,
                "entrega_id": do.get("id"),
                "parada": st.get("parada") or 1,
                "parceiro": do.get("parceiro") or "",
                "endereco": st.get("endereco") or "",
                "cidade": st.get("cidade") or "",
                "contato": st.get("contato") or "",
                "telefone": st.get("telefone") or "",
                "status": "pending",
                "missing": False,
            })
    if stops:
        stops[0]["status"] = "current"
    return stops


def _progress(stops):
    stops = stops or []
    done = sum(1 for s in stops if s.get("status") in ("completed", "skipped", "failed"))
    cur = next((s for s in stops if s.get("status") in ("current", "arrived", "servicing")), None)
    return {
        "total": len(stops),
        "concluidas": done,
        "restantes": max(0, len(stops) - done),
        "atual_seq": (cur or {}).get("seq"),
        "atual_entrega": (cur or {}).get("entrega_id"),
    }


def _enrich(row):
    out = dict(row)
    out["status_label"] = STATUSES.get(out.get("status"), out.get("status") or "")
    stops = list(out.get("stops") or [])
    for s in stops:
        s["status_label"] = STOP_STATUSES.get(s.get("status"), s.get("status") or "")
    out["stops"] = stops
    out["progresso"] = _progress(stops)
    st = out.get("status")
    out["acoes"] = [a for (fr, a), _to in TRANSITIONS.items() if fr == st]
    if st in ("started", "in_progress"):
        for extra in ("arrive_stop", "start_service", "complete_stop", "skip_stop", "fail_stop"):
            if extra not in out["acoes"]:
                out["acoes"].append(extra)
    return out


def meta():
    data = _load_raw()
    return {
        "total": len(data.get("trips") or []),
        "status": STATUSES,
        "stop_status": STOP_STATUSES,
        "nota": "Trip = execução do Manifest. Sem inventário.",
        "atualizado_em": data.get("atualizado_em"),
    }


def list_trips(q=None, status=None, data=None, manifesto_id=None):
    rows = list(_load_raw().get("trips") or [])
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r for r in rows
            if qq in str(r.get("id") or "").lower()
            or qq in str(r.get("manifesto_id") or "").lower()
            or qq in str(r.get("motorista") or "").lower()
        ]
    if status:
        st = str(status).strip().lower()
        if st not in STATUSES:
            raise ValueError("status inválido")
        rows = [r for r in rows if r.get("status") == st]
    if data:
        rows = [r for r in rows if r.get("data") == str(data).strip()]
    if manifesto_id:
        mid = str(manifesto_id).strip().upper()
        rows = [r for r in rows if str(r.get("manifesto_id") or "").upper() == mid]
    order = {s: i for i, s in enumerate(STATUSES)}
    rows.sort(key=lambda r: (order.get(r.get("status"), 99), str(r.get("id") or "")))
    return {
        "total": len(_load_raw().get("trips") or []),
        "filtrado": len(rows),
        "status_opcoes": STATUSES,
        "trips": [_enrich(r) for r in rows],
        "meta": meta(),
    }


def get_trip(tid):
    key = str(tid or "").strip().upper()
    for r in _load_raw().get("trips") or []:
        if str(r.get("id") or "").upper() == key:
            return _enrich(r)
    return None


def create_from_manifest(manifesto_id, usuario=""):
    mid = str(manifesto_id or "").strip().upper()
    mf = delivery_manifest.get_manifest(mid)
    if not mf:
        raise ValueError("manifesto não encontrado")
    if mf.get("status") not in ("released", "in_progress"):
        raise ValueError("manifesto precisa estar liberado (released)")
    other = _active_for_manifest(mid)
    if other:
        raise ValueError(f"já existe trip ativo {other.get('id')} para este manifesto")

    stops = _build_stops(mf)
    if not stops:
        raise ValueError("manifesto sem paradas/entregas")

    data = _load_raw()
    tid = _next_id(data)
    row = {
        "id": tid,
        "manifesto_id": mid,
        "data": mf.get("data") or _today(),
        "fonte": mf.get("fonte") or "DC-01",
        "status": "ready",
        "motorista": mf.get("motorista") or "",
        "veiculo": mf.get("veiculo") or "",
        "recurso_id": mf.get("recurso_id") or "",
        "partida_em": "",
        "retorno_em": "",
        "stops": stops,
        "observacao": mf.get("observacao") or "",
        "historico": [_hist("ready", usuario, f"criado do manifesto {mid}")],
        "cancelamento_motivo": "",
        "criado_em": _now(),
        "atualizado_em": _now(),
    }
    data["trips"].append(row)
    _save(data)
    return _enrich(row)


def _advance_current(stops, from_statuses, to_status):
    """Marca a parada atual e promove a próxima pending → current."""
    idx = next(
        (i for i, s in enumerate(stops) if s.get("status") in from_statuses),
        None,
    )
    if idx is None:
        raise ValueError("nenhuma parada atual")
    stops[idx]["status"] = to_status
    if to_status in ("completed", "skipped", "failed"):
        nxt = next(
            (i for i, s in enumerate(stops) if s.get("status") == "pending"),
            None,
        )
        if nxt is not None:
            stops[nxt]["status"] = "current"
    return stops[idx]


def transition(tid, action, usuario="", motivo="", **extra):
    data = _load_raw()
    idx, row = _find(data, tid)
    if row is None:
        raise ValueError("trip não encontrado")
    if row.get("status") == "closed":
        raise ValueError("trip fechado é imutável")

    act = str(action or "").strip().lower()
    cur = row.get("status") or "ready"
    stops = list(row.get("stops") or [])

    # ações de parada
    if act == "arrive_stop":
        if cur not in ("started", "in_progress"):
            raise ValueError("trip precisa estar em execução")
        st = _advance_current(stops, ("current",), "arrived")
        st["chegada_em"] = st.get("chegada_em") or _now()
        if extra.get("lat") is not None:
            st["lat"] = extra.get("lat")
        if extra.get("lng") is not None:
            st["lng"] = extra.get("lng")
        row["stops"] = stops
        if cur == "started":
            row["status"] = "in_progress"
        nota = f"chegou parada {st.get('seq')} · {st.get('entrega_id')}"
        row["atualizado_em"] = _now()
        row.setdefault("historico", []).append(_hist(row["status"], usuario, nota))
        data["trips"][idx] = row
        _save(data)
        return _enrich(row)

    if act == "start_service":
        if cur not in ("started", "in_progress"):
            raise ValueError("trip precisa estar em execução")
        st = _advance_current(stops, ("arrived", "current"), "servicing")
        if not st.get("chegada_em"):
            st["chegada_em"] = _now()
        st["servico_em"] = st.get("servico_em") or _now()
        row["stops"] = stops
        if cur == "started":
            row["status"] = "in_progress"
        nota = f"atendendo parada {st.get('seq')} · {st.get('entrega_id')}"
        row["atualizado_em"] = _now()
        row.setdefault("historico", []).append(_hist(row["status"], usuario, nota))
        data["trips"][idx] = row
        _save(data)
        return _enrich(row)

    if act == "complete_stop":
        if cur not in ("started", "in_progress"):
            raise ValueError("trip precisa estar em execução")
        st = _advance_current(stops, ("current", "arrived", "servicing"), "completed")
        st["saida_em"] = st.get("saida_em") or _now()
        if not st.get("chegada_em"):
            st["chegada_em"] = st["saida_em"]
        row["stops"] = stops
        if cur == "started":
            row["status"] = "in_progress"
        eid = st.get("entrega_id")
        if eid:
            do = delivery_orders.get_order(eid)
            try:
                if do and do.get("status") == "in_transit":
                    delivery_orders.transition(eid, "deliver", usuario=usuario)
                elif do and do.get("status") == "assigned":
                    delivery_orders.transition(eid, "depart", usuario=usuario)
                    delivery_orders.transition(eid, "deliver", usuario=usuario)
            except ValueError:
                pass
        nota = f"concluiu parada {st.get('seq')} · {st.get('entrega_id')}"
        prog = _progress(stops)
        if prog["restantes"] == 0:
            row["status"] = "completed"
            row["retorno_em"] = _now()
            nota += " · trip concluído"
        row["atualizado_em"] = _now()
        row.setdefault("historico", []).append(_hist(row["status"], usuario, nota))
        data["trips"][idx] = row
        _save(data)
        return _enrich(row)

    if act in ("skip_stop", "fail_stop"):
        if cur not in ("started", "in_progress"):
            raise ValueError("trip precisa estar em execução")
        reason = str(motivo or "").strip() or ("falhou" if act == "fail_stop" else "pulado")
        end = "failed" if act == "fail_stop" else "skipped"
        st = _advance_current(stops, ("current", "arrived", "servicing"), end)
        st["saida_em"] = st.get("saida_em") or _now()
        st["resultado"] = reason
        row["stops"] = stops
        if cur == "started":
            row["status"] = "in_progress"
        nota = f"{'falhou' if end == 'failed' else 'pulou'} parada {st.get('seq')}: {reason}"
        prog = _progress(stops)
        if prog["restantes"] == 0:
            row["status"] = "completed"
            row["retorno_em"] = _now()
        row["atualizado_em"] = _now()
        row.setdefault("historico", []).append(_hist(row["status"], usuario, nota))
        data["trips"][idx] = row
        _save(data)
        return _enrich(row)

    nxt = TRANSITIONS.get((cur, act))
    if not nxt:
        raise ValueError(f"ação '{act}' não permitida no status '{cur}'")

    if act == "cancel":
        reason = str(motivo or "").strip()
        if not reason:
            raise ValueError("motivo obrigatório")
        row["cancelamento_motivo"] = reason
        nota = reason
    elif act == "start":
        mid = row.get("manifesto_id")
        mf = delivery_manifest.get_manifest(mid)
        if mf and mf.get("status") == "released":
            try:
                delivery_manifest.transition(mid, "start", usuario=usuario)
            except ValueError:
                pass
        for eid in {s.get("entrega_id") for s in stops if s.get("entrega_id")}:
            do = delivery_orders.get_order(eid)
            if do and do.get("status") == "assigned":
                try:
                    delivery_orders.transition(eid, "depart", usuario=usuario)
                except ValueError:
                    pass
            try:
                delivery_tracking.ensure_track(eid, usuario=usuario)
            except ValueError:
                pass
        row["partida_em"] = _now()
        # primeira parada current
        for s in stops:
            if s.get("status") == "pending":
                s["status"] = "current"
                break
        row["stops"] = stops
        nota = "partida"
        # auto progress after start
        nxt = "in_progress"
    elif act == "pause":
        nota = str(motivo or "pausado").strip()
    elif act == "resume":
        nota = "retomado"
    elif act == "complete":
        row["retorno_em"] = row.get("retorno_em") or _now()
        nota = "concluído"
    elif act == "close":
        nota = "fechado"
    else:
        nota = str(motivo or act).strip()

    row["status"] = nxt
    row["atualizado_em"] = _now()
    row.setdefault("historico", []).append(_hist(nxt, usuario, nota))
    data["trips"][idx] = row
    _save(data)

    # espelha manifesto complete se trip completed
    if nxt == "completed" and row.get("manifesto_id"):
        try:
            mf = delivery_manifest.get_manifest(row["manifesto_id"])
            if mf and mf.get("status") == "in_progress":
                delivery_manifest.transition(row["manifesto_id"], "complete", usuario=usuario)
        except ValueError:
            pass

    return _enrich(row)


def update_stop(tid, seq, fields=None, usuario=""):
    """Atualiza campos operacionais da parada (notas, GPS, etc.)."""
    data = _load_raw()
    idx, row = _find(data, tid)
    if row is None:
        raise ValueError("trip não encontrado")
    if row.get("status") == "closed":
        raise ValueError("trip fechado é imutável")
    try:
        seq_n = int(seq)
    except (TypeError, ValueError):
        raise ValueError("seq inválida")
    fields = fields or {}
    stops = list(row.get("stops") or [])
    st = next((s for s in stops if int(s.get("seq") or 0) == seq_n), None)
    if not st:
        raise ValueError("parada não encontrada")
    if "nota" in fields or "observacao" in fields:
        note = str(fields.get("nota") or fields.get("observacao") or "").strip()
        if note:
            st["observacao"] = note
            hist = list(st.get("notas") or [])
            hist.append({"em": _now(), "usuario": usuario, "texto": note})
            st["notas"] = hist[-20:]
    if "lat" in fields:
        st["lat"] = fields.get("lat")
    if "lng" in fields:
        st["lng"] = fields.get("lng")
    if "resultado" in fields:
        st["resultado"] = str(fields.get("resultado") or "").strip()
    row["stops"] = stops
    row["atualizado_em"] = _now()
    row.setdefault("historico", []).append(_hist(row.get("status"), usuario, f"parada {seq_n} atualizada"))
    data["trips"][idx] = row
    _save(data)
    return _enrich(row)


def reorder_stops(tid, seq_order, usuario=""):
    """Reordena paradas — só com trip ready."""
    data = _load_raw()
    idx, row = _find(data, tid)
    if row is None:
        raise ValueError("trip não encontrado")
    if row.get("status") != "ready":
        raise ValueError("reordenação só com trip pronta (ready)")
    order = [int(x) for x in (seq_order or [])]
    stops = list(row.get("stops") or [])
    by_seq = {int(s.get("seq") or 0): s for s in stops}
    if sorted(order) != sorted(by_seq.keys()):
        raise ValueError("seq_order deve listar todas as paradas")
    new_stops = []
    for i, old_seq in enumerate(order, start=1):
        st = dict(by_seq[old_seq])
        st["seq"] = i
        st["status"] = "current" if i == 1 else "pending"
        new_stops.append(st)
    row["stops"] = new_stops
    row["atualizado_em"] = _now()
    row.setdefault("historico", []).append(_hist("ready", usuario, "paradas reordenadas"))
    data["trips"][idx] = row
    _save(data)
    return _enrich(row)
