"""
Reservas de venda B2B — store COBOL (fonte da verdade).

.dat SEQUENTIAL:
  dados/reservas_venda.dat
  dados/reservas_linhas.dat

Avisos (texto): dados/reservas_hist.json (auxiliar)
Projeção: dados/sales_reservations.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import cobol_bridge
import jsonio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "dados", "sales_reservations.json")
HIST_FILE = os.path.join(BASE_DIR, "dados", "reservas_hist.json")
DAT_CORE = os.path.join(BASE_DIR, "dados", "reservas_venda.dat")
DAT_LIN = os.path.join(BASE_DIR, "dados", "reservas_linhas.dat")


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
    out, _ = cobol_bridge._run("gerir_reservas_venda", {"ACAO": "listar"})
    return _parse_blob(out, "reservas")


def listar_linhas(reserva_id=None):
    if reserva_id:
        out, _ = cobol_bridge._run(
            "gerir_lin_reserva",
            {"ACAO": "listar-sr", "RESERVA_ID": str(reserva_id)},
        )
    else:
        out, _ = cobol_bridge._run("gerir_lin_reserva", {"ACAO": "listar"})
    return _parse_blob(out, "linhas")


def max_seq():
    m = 0
    for h in listar_cabecalhos():
        try:
            m = max(m, int(h.get("seq") or 0))
        except (TypeError, ValueError):
            pass
    return m


def _assemble(headers, linhas, hist_map):
    by_ln = {}
    for ln in linhas:
        rid = str(ln.get("reserva_id") or "").upper()
        by_ln.setdefault(rid, []).append({
            "produto_id": ln.get("produto_id") or "",
            "produto": ln.get("produto") or "",
            "qtd": int(ln.get("qtd") or 0),
            "qtd_pedida": int(ln.get("qtd_pedida") or 0),
        })

    rows = []
    for h in headers:
        rid = str(h.get("id") or "")
        key = rid.upper()
        meta = hist_map.get(rid) or hist_map.get(key) or {}
        rows.append({
            "id": rid,
            "pedido_id": h.get("pedido_id") or "",
            "pedido_numero": h.get("pedido_numero") or "",
            "estabelecimento_id": h.get("estabelecimento_id") or "",
            "status": h.get("status") or "",
            "usuario": h.get("usuario") or "",
            "seq": int(h.get("seq") or 0),
            "linhas": by_ln.get(key, []),
            "warnings": list(meta.get("warnings") or []),
            "criado_em": meta.get("criado_em") or "",
            "atualizado_em": meta.get("atualizado_em") or "",
        })
    return rows


def listar():
    return _assemble(listar_cabecalhos(), listar_linhas(), _load_hist())


def get(reserva_id):
    key = str(reserva_id or "").strip().upper()
    for r in listar():
        if str(r.get("id") or "").upper() == key:
            return r
    return None


def get_active_for_pedido(pedido_id):
    key = str(pedido_id or "").strip()
    for r in listar():
        if str(r.get("pedido_id") or "") == key and r.get("status") == "active":
            return r
    return None


def _replace_linhas(rid, linhas):
    cobol_bridge._run(
        "gerir_lin_reserva",
        {"ACAO": "limpar", "RESERVA_ID": rid},
    )
    for i, ln in enumerate(linhas or [], start=1):
        cobol_bridge._run(
            "gerir_lin_reserva",
            {
                "ACAO": "incluir",
                "RESERVA_ID": rid,
                "SEQ": str(i),
                "PRODUTO_ID": _clip(ln.get("produto_id"), 10),
                "PRODUTO": _clip(ln.get("produto"), 40),
                "QTD": str(int(ln.get("qtd") or 0)),
                "QTD_PEDIDA": str(int(ln.get("qtd_pedida") or ln.get("qtd") or 0)),
            },
        )


def _header_env(row, *, with_id=False):
    env = {
        "PEDIDO_ID": _clip(row.get("pedido_id"), 12),
        "PEDIDO_NUM": _clip(row.get("pedido_numero"), 12),
        "ESTAB": _clip(row.get("estabelecimento_id"), 16),
        "STATUS": _clip(row.get("status") or "active", 12),
        "USUARIO": _clip(row.get("usuario"), 30),
        "SEQ": str(int(row.get("seq") or 0)),
    }
    if with_id and row.get("id"):
        env["ID"] = _clip(row.get("id"), 12)
    return env


def save(row, *, is_new=False):
    r = dict(row or {})
    rid = str(r.get("id") or "").strip()
    env = _header_env(r, with_id=bool(rid))
    if is_new or not rid:
        env["ACAO"] = "incluir"
        if rid:
            env["ID"] = _clip(rid, 12)
        out, err = cobol_bridge._run("gerir_reservas_venda", env)
        new_id = None
        for line in (out or "").splitlines():
            line = line.strip()
            if line.startswith("ERRO:"):
                raise ValueError(line)
            if line.startswith("SR-") or line.startswith("sr-"):
                new_id = line
                break
            if line and "ERRO" not in line and not line.startswith("{"):
                new_id = line
        if not new_id:
            raise ValueError("falha ao incluir reserva: " + (out or err or ""))
        rid = new_id
    else:
        env["ACAO"] = "alterar"
        env["ID"] = _clip(rid, 12)
        out, err = cobol_bridge._run("gerir_reservas_venda", env)
        if "ERRO:" in (out or ""):
            raise ValueError((out or err or "").strip())

    _replace_linhas(rid, r.get("linhas") or [])
    hist = _load_hist()
    prev = hist.get(rid) or {}
    hist[rid] = {
        "warnings": list(r.get("warnings") or prev.get("warnings") or []),
        "criado_em": r.get("criado_em") or prev.get("criado_em") or _now(),
        "atualizado_em": _now(),
    }
    _save_hist(hist)
    sync_json()
    return get(rid)


def set_status(reserva_id, status):
    """Altera só status, preservando linhas e demais campos."""
    cur = get(reserva_id)
    if not cur:
        return None
    cur["status"] = str(status or "").strip() or cur.get("status")
    cur["atualizado_em"] = _now()
    return save(cur, is_new=False)


def sync_json(rows=None):
    data_rows = rows if rows is not None else listar()
    payload = {
        "seq": max_seq(),
        "reservations": data_rows,
        "total": len(data_rows),
        "source": "cobol:reservas_venda.dat",
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
            "reservas_venda.dat",
            "reservas_venda.tmp",
            "reservas_linhas.dat",
            "reservas_linhas.tmp",
            "reservas_hist.json",
        ):
            p = os.path.join(BASE_DIR, "dados", name)
            if os.path.exists(p):
                os.remove(p)
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("reservations") if isinstance(data, dict) else []
    n = 0
    for i, r in enumerate(rows or [], start=1):
        try:
            row = dict(r)
            if not row.get("seq"):
                row["seq"] = i
            save(row, is_new=True)
            n += 1
        except Exception:
            continue
    sync_json()
    return {"migrated": n, "message": "ok"}
