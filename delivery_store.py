"""
Delivery Orders — store COBOL (fonte da verdade).

.dat SEQUENTIAL:
  dados/entregas.dat
  dados/entregas_paradas.dat
  dados/entregas_itens.dat

Histórico (texto longo): dados/entregas_hist.json (auxiliar)
Projeção: dados/delivery_orders.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import cobol_bridge
import jsonio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "dados", "delivery_orders.json")
HIST_FILE = os.path.join(BASE_DIR, "dados", "entregas_hist.json")
DAT_CORE = os.path.join(BASE_DIR, "dados", "entregas.dat")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _clip(val, n):
    s = str(val if val is not None else "")
    s = s.replace('"', "'").replace("\n", " ").replace("\r", " ")
    return s[:n]


def _parse_blob(out, key):
    text = (out or "").strip()
    marker = '{"' + key + '":'
    start = text.find(marker)
    if start < 0:
        return []
    try:
        return json.loads(text[start:]).get(key) or []
    except json.JSONDecodeError:
        rows = []
        for line in text.splitlines():
            line = line.strip().rstrip(",")
            if line.startswith("{"):
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return rows


def _load_hist():
    if not os.path.exists(HIST_FILE):
        return {}
    with open(HIST_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _save_hist(data):
    os.makedirs(os.path.dirname(HIST_FILE) or ".", exist_ok=True)
    jsonio.save(HIST_FILE, data)


def listar_cabecalhos():
    out, _ = cobol_bridge._run("gerir_entregas", {"ACAO": "listar"})
    return _parse_blob(out, "entregas")


def listar_paradas(entrega_id=None):
    if entrega_id:
        out, _ = cobol_bridge._run(
            "gerir_paradas_ent",
            {"ACAO": "listar-do", "ENTREGA_ID": str(entrega_id)},
        )
    else:
        out, _ = cobol_bridge._run("gerir_paradas_ent", {"ACAO": "listar"})
    return _parse_blob(out, "paradas")


def listar_itens(entrega_id=None):
    if entrega_id:
        out, _ = cobol_bridge._run(
            "gerir_itens_ent",
            {"ACAO": "listar-do", "ENTREGA_ID": str(entrega_id)},
        )
    else:
        out, _ = cobol_bridge._run("gerir_itens_ent", {"ACAO": "listar"})
    return _parse_blob(out, "itens")


def max_seq():
    m = 0
    for h in listar_cabecalhos():
        try:
            m = max(m, int(h.get("seq") or 0))
        except (TypeError, ValueError):
            pass
    return m


def _assemble(headers, paradas, itens, hist_map):
    by_pa, by_it = {}, {}
    for p in paradas:
        eid = str(p.get("entrega_id") or "").upper()
        by_pa.setdefault(eid, []).append(p)
    for it in itens:
        eid = str(it.get("entrega_id") or "").upper()
        by_it.setdefault(eid, []).append(it)

    orders = []
    for h in headers:
        eid = str(h.get("id") or "")
        key = eid.upper()
        stops = []
        for p in sorted(by_pa.get(key, []), key=lambda x: int(x.get("parada") or 0)):
            pn = int(p.get("parada") or 0)
            its = [
                {
                    "produto_id": it.get("produto_id") or "",
                    "produto": it.get("produto") or "item",
                    "qtd": float(it.get("qtd") or 1),
                }
                for it in sorted(
                    [x for x in by_it.get(key, []) if int(x.get("parada") or 0) == pn],
                    key=lambda x: int(x.get("seq") or 0),
                )
            ]
            if not its:
                its = [{"produto_id": "", "produto": "item", "qtd": 1}]
            stops.append({
                "parada": pn,
                "rotulo": p.get("rotulo") or f"Parada {pn}",
                "address_type": p.get("address_type") or "SHIPPING",
                "endereco": p.get("endereco") or "",
                "cidade": p.get("cidade") or "",
                "uf": p.get("uf") or "",
                "cep": p.get("cep") or "",
                "contato": p.get("contato") or "",
                "telefone": p.get("telefone") or "",
                "status": p.get("status") or "pending",
                "itens": its,
            })
        orders.append({
            "id": eid,
            "origem_tipo": h.get("origem_tipo") or "manual",
            "origem_ref": h.get("origem_ref") or "",
            "parceiro_id": h.get("parceiro_id") or "",
            "parceiro": h.get("parceiro") or "",
            "fonte": h.get("fonte") or "DC-01",
            "fonte_nome": h.get("fonte_nome") or "",
            "status": h.get("status") or "draft",
            "prioridade": h.get("prioridade") or "normal",
            "data_agendada": h.get("data_agendada") or "",
            "janela": h.get("janela") or "",
            "recurso_id": h.get("recurso_id") or "",
            "motorista": h.get("motorista") or "",
            "veiculo": h.get("veiculo") or "",
            "expedicao_id": h.get("expedicao_id") or "",
            "manifesto_id": h.get("manifesto_id") or "",
            "observacao": h.get("observacao") or "",
            "seq": int(h.get("seq") or 0),
            "paradas": stops,
            "historico": list(hist_map.get(eid) or hist_map.get(key) or []),
            "cancelamento_motivo": "",
            "origem_dado": "cobol",
            "atualizado_em": _now(),
        })
    return orders


def listar():
    return _assemble(
        listar_cabecalhos(),
        listar_paradas(),
        listar_itens(),
        _load_hist(),
    )


def get(entrega_id):
    key = str(entrega_id or "").strip().upper()
    for o in listar():
        if str(o.get("id") or "").upper() == key:
            return o
    return None


def _replace_children(oid, paradas):
    cobol_bridge._run("gerir_paradas_ent", {"ACAO": "limpar", "ENTREGA_ID": oid})
    cobol_bridge._run("gerir_itens_ent", {"ACAO": "limpar", "ENTREGA_ID": oid})
    for st in paradas or []:
        pn = int(st.get("parada") or 1)
        cobol_bridge._run(
            "gerir_paradas_ent",
            {
                "ACAO": "incluir",
                "ENTREGA_ID": oid,
                "PARADA": str(pn),
                "ROTULO": _clip(st.get("rotulo"), 30),
                "ADDRESS_TYPE": _clip(st.get("address_type") or "SHIPPING", 16),
                "ENDERECO": _clip(st.get("endereco"), 60),
                "CIDADE": _clip(st.get("cidade"), 30),
                "UF": _clip(st.get("uf"), 2),
                "CEP": _clip(st.get("cep"), 10),
                "CONTATO": _clip(st.get("contato"), 30),
                "TELEFONE": _clip(st.get("telefone"), 20),
                "STATUS": _clip(st.get("status") or "pending", 12),
            },
        )
        for i, it in enumerate(st.get("itens") or [], start=1):
            cobol_bridge._run(
                "gerir_itens_ent",
                {
                    "ACAO": "incluir",
                    "ENTREGA_ID": oid,
                    "PARADA": str(pn),
                    "SEQ": str(i),
                    "PRODUTO_ID": _clip(it.get("produto_id"), 10),
                    "PRODUTO": _clip(it.get("produto") or "item", 40),
                    "QTD": str(it.get("qtd") or 1),
                },
            )


def save(order, *, is_new=False):
    o = dict(order or {})
    oid = str(o.get("id") or "").strip()
    seq = int(o.get("seq") or 0)
    env = {
        "ORIGEM_TIPO": _clip(o.get("origem_tipo") or "manual", 20),
        "ORIGEM_REF": _clip(o.get("origem_ref"), 20),
        "PARCEIRO_ID": _clip(o.get("parceiro_id"), 12),
        "PARCEIRO": _clip(o.get("parceiro") or "Cliente", 40),
        "FONTE": _clip(o.get("fonte") or "DC-01", 12),
        "FONTE_NOME": _clip(o.get("fonte_nome"), 30),
        "STATUS": _clip(o.get("status") or "draft", 16),
        "PRIORIDADE": _clip(o.get("prioridade") or "normal", 12),
        "DATA_AGENDADA": _clip(o.get("data_agendada"), 10),
        "JANELA": _clip(o.get("janela"), 12),
        "RECURSO_ID": _clip(o.get("recurso_id"), 12),
        "MOTORISTA": _clip(o.get("motorista"), 30),
        "VEICULO": _clip(o.get("veiculo"), 12),
        "EXPEDICAO_ID": _clip(o.get("expedicao_id"), 20),
        "MANIFESTO_ID": _clip(o.get("manifesto_id"), 20),
        "OBSERVACAO": _clip(o.get("observacao"), 60),
        "SEQ": str(seq),
    }
    if is_new or not oid:
        env["ACAO"] = "incluir"
        if oid:
            env["ID"] = _clip(oid, 24)
        out, err = cobol_bridge._run("gerir_entregas", env)
        new_id = None
        for line in (out or "").splitlines():
            line = line.strip()
            if line.startswith("ERRO:"):
                raise ValueError(line)
            if line.startswith("DO-") or line.startswith("do-"):
                new_id = line
                break
            if line and "ERRO" not in line and not line.startswith("{"):
                new_id = line
        if not new_id:
            raise ValueError("falha ao incluir entrega: " + (out or err or ""))
        oid = new_id
    else:
        env["ACAO"] = "alterar"
        env["ID"] = _clip(oid, 24)
        out, err = cobol_bridge._run("gerir_entregas", env)
        if "ERRO:" in (out or ""):
            raise ValueError((out or err or "").strip())

    _replace_children(oid, o.get("paradas") or [])
    hist = _load_hist()
    hist[oid] = list(o.get("historico") or [])
    _save_hist(hist)
    sync_json()
    return get(oid)


def delete(entrega_id):
    oid = str(entrega_id or "").strip()
    out, _ = cobol_bridge._run("gerir_entregas", {"ACAO": "excluir", "ID": oid})
    if "ERRO:" in (out or ""):
        raise ValueError((out or "").strip())
    cobol_bridge._run("gerir_paradas_ent", {"ACAO": "limpar", "ENTREGA_ID": oid})
    cobol_bridge._run("gerir_itens_ent", {"ACAO": "limpar", "ENTREGA_ID": oid})
    hist = _load_hist()
    hist.pop(oid, None)
    _save_hist(hist)
    sync_json()
    return True


def sync_json(orders=None):
    rows = orders if orders is not None else listar()
    payload = {
        "seq": max_seq(),
        "orders": rows,
        "total": len(rows),
        "source": "cobol:entregas.dat",
        "atualizado_em": _now(),
    }
    os.makedirs(os.path.dirname(JSON_FILE) or ".", exist_ok=True)
    jsonio.save(JSON_FILE, payload)
    return payload


def migrate_json_to_cobol(force=False):
    if os.path.exists(DAT_CORE) and os.path.getsize(DAT_CORE) > 0 and not force:
        return {"migrated": 0, "message": "dat ja existe"}
    if not os.path.exists(JSON_FILE):
        return {"migrated": 0, "message": "sem json"}
    if force:
        for name in (
            "entregas.dat", "entregas.tmp",
            "entregas_paradas.dat", "entregas_paradas.tmp",
            "entregas_itens.dat", "entregas_itens.tmp",
            "entregas_hist.json",
        ):
            p = os.path.join(BASE_DIR, "dados", name)
            if os.path.exists(p):
                os.remove(p)
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("orders") if isinstance(data, dict) else []
    n = 0
    for i, o in enumerate(rows or [], start=1):
        try:
            row = dict(o)
            if not row.get("seq"):
                row["seq"] = i
            save(row, is_new=True)
            n += 1
        except Exception:
            continue
    sync_json()
    return {"migrated": n, "message": "ok"}
