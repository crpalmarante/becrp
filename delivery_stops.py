"""
Delivery — Stops (RFC-18108 MVP).

Parada = menor unidade de execução da Trip.
Projeção enriquecida (pedido + POD + tempos) + ações.
Não move estoque.
"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

import delivery_orders
import delivery_pod
import delivery_trip

STATUSES = delivery_trip.STOP_STATUSES

EXCEPTIONS = {
    "customer_absent": "Cliente ausente",
    "wrong_address": "Endereço errado",
    "access": "Acesso negado",
    "damaged": "Mercadoria avariada",
    "partial": "Entrega parcial",
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


def _duration_min(chegada, saida):
    if not chegada or not saida:
        return None
    try:
        a = datetime.fromisoformat(str(chegada)[:19])
        b = datetime.fromisoformat(str(saida)[:19])
        return max(0, int((b - a).total_seconds() // 60))
    except ValueError:
        return None


def _enrich_stop(st, trip):
    order = delivery_orders.get_order(st.get("entrega_id")) if st.get("entrega_id") else None
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
    status = st.get("status") or "pending"
    pod = None
    if st.get("entrega_id"):
        try:
            pods = delivery_pod.list_pods(entrega_id=st["entrega_id"]).get("pods") or []
            pn = int(st.get("parada") or 1)
            pod = next((p for p in pods if int(p.get("parada") or 1) == pn), None)
        except ValueError:
            pod = None

    acoes = []
    tstatus = trip.get("status")
    if tstatus == "ready" and status in ("pending", "current"):
        acoes.append("note")
    if tstatus in ("started", "in_progress"):
        if status == "current":
            acoes.extend(["navigate", "arrive", "skip", "fail", "note"])
        elif status == "arrived":
            acoes.extend(["navigate", "start_service", "finish", "skip", "fail", "note", "pod"])
        elif status == "servicing":
            acoes.extend(["finish", "skip", "fail", "note", "pod"])

    return {
        "id": f"{trip.get('id')}-{st.get('seq')}",
        "trip_id": trip.get("id"),
        "manifesto_id": trip.get("manifesto_id"),
        "seq": st.get("seq"),
        "parada": st.get("parada") or 1,
        "entrega_id": st.get("entrega_id"),
        "status": status,
        "status_label": STATUSES.get(status, status),
        "parceiro": st.get("parceiro") or order.get("parceiro") or "",
        "endereco": endereco,
        "cidade": cidade,
        "contato": st.get("contato") or (match or {}).get("contato") or "",
        "telefone": st.get("telefone") or (match or {}).get("telefone") or "",
        "janela": order.get("janela") or "",
        "itens": itens,
        "observacao": st.get("observacao") or order.get("observacao") or "",
        "notas": st.get("notas") or [],
        "chegada_em": st.get("chegada_em") or "",
        "servico_em": st.get("servico_em") or "",
        "saida_em": st.get("saida_em") or "",
        "duracao_min": _duration_min(st.get("chegada_em"), st.get("saida_em")),
        "lat": st.get("lat"),
        "lng": st.get("lng"),
        "resultado": st.get("resultado") or "",
        "navigate_url": _maps_url(endereco, cidade),
        "pod": pod,
        "trip_status": tstatus,
        "trip_status_label": trip.get("status_label"),
        "motorista": trip.get("motorista"),
        "veiculo": trip.get("veiculo"),
        "acoes": acoes,
    }


def meta():
    return {
        "status": STATUSES,
        "excecoes": EXCEPTIONS,
        "nota": "Stop = unidade de execução. Trip organiza. Sem inventário.",
    }


def list_stops(trip_id=None, status=None, q=None, data=None, only_active_trips=False):
    trips = delivery_trip.list_trips(data=data).get("trips") or []
    if trip_id:
        tid = str(trip_id).strip().upper()
        trips = [t for t in trips if str(t.get("id") or "").upper() == tid]
    if only_active_trips:
        trips = [t for t in trips if t.get("status") in delivery_trip.ACTIVE]

    rows = []
    for t in trips:
        for st in t.get("stops") or []:
            rows.append(_enrich_stop(st, t))

    if status:
        st = str(status).strip().lower()
        if st not in STATUSES:
            raise ValueError("status inválido")
        rows = [r for r in rows if r.get("status") == st]

    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r for r in rows
            if qq in str(r.get("id") or "").lower()
            or qq in str(r.get("entrega_id") or "").lower()
            or qq in str(r.get("parceiro") or "").lower()
            or qq in str(r.get("trip_id") or "").lower()
        ]

    rows.sort(key=lambda r: (str(r.get("trip_id") or ""), int(r.get("seq") or 0)))
    return {
        "total": len(rows),
        "filtrado": len(rows),
        "status_opcoes": STATUSES,
        "stops": rows,
        "meta": meta(),
    }


def get_stop(trip_id, seq):
    trip = delivery_trip.get_trip(trip_id)
    if not trip:
        raise ValueError("trip não encontrado")
    try:
        seq_n = int(seq)
    except (TypeError, ValueError):
        raise ValueError("seq inválida")
    st = next((s for s in (trip.get("stops") or []) if int(s.get("seq") or 0) == seq_n), None)
    if not st:
        raise ValueError("parada não encontrada")
    return _enrich_stop(st, trip)


def action(trip_id, seq, action_name, usuario="", motivo="", **extra):
    act = str(action_name or "").strip().lower()
    tid = str(trip_id or "").strip().upper()
    if not tid:
        raise ValueError("trip_id obrigatório")
    try:
        seq_n = int(seq)
    except (TypeError, ValueError):
        raise ValueError("seq inválida")

    # valida parada alvo = atual quando ação de execução
    stop = get_stop(tid, seq_n)

    if act == "navigate":
        return {"stop": stop, "client_only": True, "href": stop.get("navigate_url")}

    if act == "note":
        note = str(motivo or extra.get("nota") or extra.get("observacao") or "").strip()
        if not note:
            raise ValueError("nota obrigatória")
        delivery_trip.update_stop(tid, seq_n, {"nota": note}, usuario=usuario)
        return {"stop": get_stop(tid, seq_n)}

    if act == "reorder":
        order = extra.get("seq_order") or extra.get("ordem")
        trip = delivery_trip.reorder_stops(tid, order, usuario=usuario)
        return {"trip": trip, "stops": list_stops(trip_id=tid)["stops"]}

    if act == "arrive":
        if stop.get("status") != "current":
            raise ValueError("só a parada atual pode registrar chegada")
        trip = delivery_trip.transition(
            tid, "arrive_stop", usuario=usuario,
            lat=extra.get("lat"), lng=extra.get("lng"),
        )
        return {"trip": trip, "stop": get_stop(tid, seq_n)}

    if act == "start_service":
        trip = delivery_trip.transition(tid, "start_service", usuario=usuario)
        return {"trip": trip, "stop": get_stop(tid, seq_n)}

    if act in ("finish", "complete", "finish_stop"):
        # POD opcional
        if extra.get("receptor_nome") or extra.get("pod"):
            eid = stop.get("entrega_id")
            if eid:
                try:
                    delivery_pod.ensure_for_order(eid, usuario=usuario)
                    pods = delivery_pod.list_pods(entrega_id=eid).get("pods") or []
                    pn = int(stop.get("parada") or 1)
                    pod = next((p for p in pods if int(p.get("parada") or 1) == pn), None)
                    if pod and pod.get("status") in ("created", "waiting"):
                        delivery_pod.confirm(
                            pod["id"],
                            {
                                "receptor_nome": str(extra.get("receptor_nome") or stop.get("contato") or "Receptor"),
                                "assinatura": str(extra.get("assinatura") or "ok"),
                                "observacao": str(extra.get("observacao") or motivo or "").strip(),
                                "itens_ok": True,
                            },
                            usuario=usuario,
                        )
                except ValueError:
                    pass
        trip = delivery_trip.transition(tid, "complete_stop", usuario=usuario, motivo=motivo)
        return {"trip": trip, "stop": get_stop(tid, seq_n)}

    if act == "skip":
        trip = delivery_trip.transition(tid, "skip_stop", usuario=usuario, motivo=motivo or "pulado")
        return {"trip": trip, "stop": get_stop(tid, seq_n)}

    if act == "fail":
        tipo = str(extra.get("tipo") or "other").strip().lower()
        label = EXCEPTIONS.get(tipo, EXCEPTIONS["other"])
        note = str(motivo or label).strip()
        trip = delivery_trip.transition(tid, "fail_stop", usuario=usuario, motivo=note)
        return {"trip": trip, "stop": get_stop(tid, seq_n), "excecao": {"tipo": tipo, "label": label}}

    if act == "pod":
        eid = stop.get("entrega_id")
        if not eid:
            raise ValueError("parada sem entrega")
        out = delivery_pod.ensure_for_order(eid, usuario=usuario)
        return {"stop": get_stop(tid, seq_n), "pod": out}

    raise ValueError(f"ação '{act}' não suportada")
