"""
Delivery — Driver Workspace (RFC-18107 MVP).

Interface de execução do motorista: trip ativo, parada atual,
ações rápidas, navegação e POD. Não planeja; não move estoque.
"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

import delivery_orders
import delivery_pod
import delivery_tracking
import delivery_trip

ACTIVE_TRIP = frozenset({"ready", "started", "in_progress", "paused"})

PROBLEM_TYPES = {
    "customer_absent": "Cliente ausente",
    "wrong_address": "Endereço errado",
    "damaged": "Mercadoria avariada",
    "access": "Restrição de acesso",
    "vehicle": "Problema no veículo",
    "refused": "Entrega recusada",
    "other": "Outro",
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _maps_url(endereco, cidade=""):
    q = " ".join(x for x in [str(endereco or "").strip(), str(cidade or "").strip()] if x)
    if not q:
        return ""
    return "https://www.google.com/maps/dir/?api=1&destination=" + quote(q)


def _tel_href(telefone):
    digits = "".join(c for c in str(telefone or "") if c.isdigit() or c == "+")
    return f"tel:{digits}" if digits else ""


def _slim_stop(st, order=None):
    order = order or {}
    paradas = order.get("paradas") or []
    match = next(
        (p for p in paradas if int(p.get("parada") or 1) == int(st.get("parada") or 1)),
        paradas[0] if paradas else {},
    )
    itens = []
    for it in (match or {}).get("itens") or []:
        itens.append({
            "produto": it.get("produto") or it.get("produto_id") or "",
            "qtd": it.get("qtd") or 1,
        })
    endereco = st.get("endereco") or (match or {}).get("endereco") or ""
    cidade = st.get("cidade") or (match or {}).get("cidade") or ""
    telefone = st.get("telefone") or (match or {}).get("telefone") or order.get("telefone") or ""
    return {
        "seq": st.get("seq"),
        "entrega_id": st.get("entrega_id"),
        "parada": st.get("parada") or 1,
        "status": st.get("status"),
        "status_label": st.get("status_label") or delivery_trip.STOP_STATUSES.get(st.get("status"), ""),
        "parceiro": st.get("parceiro") or order.get("parceiro") or "",
        "endereco": endereco,
        "cidade": cidade,
        "contato": st.get("contato") or (match or {}).get("contato") or "",
        "telefone": telefone,
        "telefone_href": _tel_href(telefone),
        "navigate_url": _maps_url(endereco, cidade),
        "janela": order.get("janela") or "",
        "observacao": order.get("observacao") or st.get("observacao") or "",
        "itens": itens,
        "instrucoes": (match or {}).get("instrucoes") or order.get("instrucoes") or "",
    }


def _pick_active_trip(recurso_id=None, motorista=None, trip_id=None):
    trips = delivery_trip.list_trips().get("trips") or []
    if trip_id:
        t = delivery_trip.get_trip(trip_id)
        if not t:
            raise ValueError("trip não encontrado")
        return t

    rid = str(recurso_id or "").strip().upper()
    mot = str(motorista or "").strip().lower()

    active = [t for t in trips if t.get("status") in ACTIVE_TRIP]
    if rid:
        hit = [t for t in active if str(t.get("recurso_id") or "").upper() == rid]
        if hit:
            return hit[0]
    if mot:
        hit = [t for t in active if mot in str(t.get("motorista") or "").lower()]
        if hit:
            return hit[0]
    if active:
        # default: primeira ativa (demo / single-driver)
        return active[0]
    return None


def _quick_actions(trip, current):
    st = trip.get("status")
    acts = []
    if st == "ready":
        acts.append({"action": "start", "label": "Partir", "primary": True})
    if st == "paused":
        acts.append({"action": "resume", "label": "Retomar", "primary": True})
    if st in ("started", "in_progress"):
        acts.append({"action": "pause", "label": "Pausar", "primary": False})
        if current:
            if current.get("navigate_url"):
                acts.append({"action": "navigate", "label": "Navegar", "primary": False, "href": current["navigate_url"]})
            if current.get("telefone_href"):
                acts.append({"action": "call", "label": "Ligar", "primary": False, "href": current["telefone_href"]})
            if current.get("status") == "current":
                acts.append({"action": "arrive_stop", "label": "Cheguei", "primary": True})
            if current.get("status") == "arrived":
                acts.append({"action": "start_service", "label": "Iniciar atendimento", "primary": True})
            if current.get("status") in ("current", "arrived", "servicing"):
                acts.append({"action": "complete_delivery", "label": "Entregar + POD", "primary": True})
                acts.append({"action": "complete_stop", "label": "Concluir parada", "primary": False})
                acts.append({"action": "skip_stop", "label": "Pular", "primary": False})
                acts.append({"action": "report_problem", "label": "Problema", "primary": False})
    if st in ("started", "in_progress", "paused") and (trip.get("progresso") or {}).get("restantes", 1) == 0:
        acts.append({"action": "complete", "label": "Finalizar trip", "primary": True})
    if st == "completed":
        acts.append({"action": "close", "label": "Fechar trip", "primary": True})
    if st in ACTIVE_TRIP:
        acts.append({"action": "cancel", "label": "Cancelar", "primary": False})
    return acts


def cockpit(recurso_id=None, motorista=None, trip_id=None):
    """Projeção do workspace do motorista."""
    trip = _pick_active_trip(recurso_id=recurso_id, motorista=motorista, trip_id=trip_id)

    ready_pool = [
        t for t in (delivery_trip.list_trips(status="ready").get("trips") or [])
        if not trip or t.get("id") != trip.get("id")
    ]
    # se filtro motorista/recurso, restringe pool
    rid = str(recurso_id or "").strip().upper()
    mot = str(motorista or "").strip().lower()
    if rid:
        ready_pool = [t for t in ready_pool if str(t.get("recurso_id") or "").upper() == rid]
    if mot:
        ready_pool = [t for t in ready_pool if mot in str(t.get("motorista") or "").lower()]

    if not trip:
        return {
            "tem_trip": False,
            "trip": None,
            "parada_atual": None,
            "proxima_parada": None,
            "progresso": {"total": 0, "concluidas": 0, "restantes": 0},
            "acoes": [],
            "problemas": PROBLEM_TYPES,
            "viagens_prontas": [
                {
                    "id": t.get("id"),
                    "manifesto_id": t.get("manifesto_id"),
                    "motorista": t.get("motorista"),
                    "veiculo": t.get("veiculo"),
                    "paradas": (t.get("progresso") or {}).get("total") or len(t.get("stops") or []),
                }
                for t in ready_pool[:10]
            ],
            "nota": "Nenhuma viagem ativa. Selecione uma trip pronta ou peça ao despacho.",
            "atualizado_em": _now(),
        }

    stops = list(trip.get("stops") or [])
    current_raw = next((s for s in stops if s.get("status") in ("current", "arrived", "servicing")), None)
    next_raw = None
    if current_raw:
        next_raw = next(
            (s for s in stops if s.get("status") == "pending" and int(s.get("seq") or 0) > int(current_raw.get("seq") or 0)),
            None,
        )
    else:
        next_raw = next((s for s in stops if s.get("status") == "pending"), None)

    cur_order = delivery_orders.get_order(current_raw["entrega_id"]) if current_raw and current_raw.get("entrega_id") else None
    nxt_order = delivery_orders.get_order(next_raw["entrega_id"]) if next_raw and next_raw.get("entrega_id") else None

    current = _slim_stop(current_raw, cur_order) if current_raw else None
    nxt = _slim_stop(next_raw, nxt_order) if next_raw else None

    pod_info = None
    if current and current.get("entrega_id"):
        try:
            pod_info = delivery_pod.summary(current["entrega_id"])
        except ValueError:
            pod_info = None

    progresso = trip.get("progresso") or delivery_trip._progress(stops)
    acoes = _quick_actions(trip, current)

    return {
        "tem_trip": True,
        "trip": {
            "id": trip.get("id"),
            "manifesto_id": trip.get("manifesto_id"),
            "status": trip.get("status"),
            "status_label": trip.get("status_label"),
            "data": trip.get("data"),
            "motorista": trip.get("motorista"),
            "veiculo": trip.get("veiculo"),
            "recurso_id": trip.get("recurso_id"),
            "partida_em": trip.get("partida_em"),
            "retorno_em": trip.get("retorno_em"),
            "fonte": trip.get("fonte"),
        },
        "parada_atual": current,
        "proxima_parada": nxt,
        "progresso": progresso,
        "pod": pod_info,
        "acoes": acoes,
        "problemas": PROBLEM_TYPES,
        "viagens_prontas": [],
        "nota": "Execute a viagem. Sem inventário.",
        "atualizado_em": _now(),
    }


def action(trip_id, action_name, usuario="", motivo="", **extra):
    """Executa ação do motorista sobre a trip (e POD quando preciso)."""
    act = str(action_name or "").strip().lower()
    tid = str(trip_id or "").strip().upper()
    if not tid:
        raise ValueError("trip_id obrigatório")
    if not act:
        raise ValueError("action obrigatória")

    # navigate / call são client-side
    if act in ("navigate", "call"):
        return {"trip_id": tid, "action": act, "client_only": True}

    if act == "report_problem":
        tipo = str(extra.get("tipo") or "other").strip().lower()
        label = PROBLEM_TYPES.get(tipo, PROBLEM_TYPES["other"])
        note = str(motivo or extra.get("nota") or label).strip()
        trip = delivery_trip.get_trip(tid)
        if not trip:
            raise ValueError("trip não encontrado")
        cur = next((s for s in (trip.get("stops") or []) if s.get("status") in ("current", "arrived")), None)
        eid = (cur or {}).get("entrega_id")
        if eid:
            try:
                delivery_tracking.ensure_track(eid, usuario=usuario)
                # evento leve via nota no historico da trip
            except ValueError:
                pass
        row = delivery_trip.transition(tid, "pause", usuario=usuario, motivo=f"problema: {note}")
        return {"trip": row, "problema": {"tipo": tipo, "label": label, "nota": note}}

    if act == "complete_delivery":
        trip = delivery_trip.get_trip(tid)
        if not trip:
            raise ValueError("trip não encontrado")
        cur = next((s for s in (trip.get("stops") or []) if s.get("status") in ("current", "arrived")), None)
        if not cur:
            raise ValueError("nenhuma parada atual")
        eid = cur.get("entrega_id")
        parada = int(cur.get("parada") or 1)
        if eid:
            try:
                delivery_pod.ensure_for_order(eid, usuario=usuario)
            except ValueError:
                pass
            pods = delivery_pod.list_pods(entrega_id=eid).get("pods") or []
            pod = next((p for p in pods if int(p.get("parada") or 1) == parada), pods[0] if pods else None)
            if pod and pod.get("status") in ("created", "waiting"):
                receptor = str(extra.get("receptor_nome") or cur.get("contato") or "Receptor").strip()
                delivery_pod.confirm(
                    pod["id"],
                    {
                        "receptor_nome": receptor,
                        "receptor_doc": str(extra.get("receptor_doc") or "").strip(),
                        "observacao": str(extra.get("observacao") or motivo or "confirmado no workspace motorista").strip(),
                        "assinatura": str(extra.get("assinatura") or "ok").strip(),
                        "itens_ok": True,
                    },
                    usuario=usuario,
                )
        if cur.get("status") == "current":
            delivery_trip.transition(tid, "arrive_stop", usuario=usuario)
        row = delivery_trip.transition(tid, "complete_stop", usuario=usuario)
        return {"trip": row, "pod_confirmado": True}

    # demais ações delegam ao trip
    mapped = {
        "start": "start",
        "pause": "pause",
        "resume": "resume",
        "arrive_stop": "arrive_stop",
        "start_service": "start_service",
        "complete_stop": "complete_stop",
        "skip_stop": "skip_stop",
        "fail_stop": "fail_stop",
        "complete": "complete",
        "close": "close",
        "cancel": "cancel",
        "finish_trip": "complete",
    }
    trip_act = mapped.get(act)
    if not trip_act:
        raise ValueError(f"ação '{act}' não suportada")
    row = delivery_trip.transition(tid, trip_act, usuario=usuario, motivo=motivo)
    return {"trip": row}
