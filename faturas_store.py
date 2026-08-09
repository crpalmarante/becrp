"""
Faturas de venda B2B — store COBOL (fonte da verdade).

.dat SEQUENTIAL: dados/faturas_venda.dat
Auxiliar (AR ids / meta): dados/faturas_venda_hist.json
Projeção: dados/faturas_venda.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import cobol_bridge
import jsonio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "dados", "faturas_venda.json")
HIST_FILE = os.path.join(BASE_DIR, "dados", "faturas_venda_hist.json")
DAT_CORE = os.path.join(BASE_DIR, "dados", "faturas_venda.dat")


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


def listar_raw():
    out, _ = cobol_bridge._run("gerir_faturas_venda", {"ACAO": "listar"})
    return _parse_blob(out, "faturas")


def max_id():
    m = 0
    for h in listar_raw():
        try:
            m = max(m, int(h.get("id") or 0))
        except (TypeError, ValueError):
            pass
    return m


def _merge(row, hist_map):
    r = dict(row or {})
    try:
        r["id"] = int(r.get("id") or 0)
    except (TypeError, ValueError):
        pass
    try:
        nfe = int(r.get("nfe_numero") or 0)
        if nfe:
            r["nfe_numero"] = nfe
        else:
            r.pop("nfe_numero", None)
    except (TypeError, ValueError):
        pass
    if not r.get("entrega_id"):
        r.pop("entrega_id", None)
    if not r.get("nfe_status"):
        r.pop("nfe_status", None)
    key = str(r.get("id") or "")
    meta = hist_map.get(key) or {}
    if meta.get("ar_titulos") is not None:
        r["ar_titulos"] = list(meta.get("ar_titulos") or [])
    if meta.get("atualizado_em"):
        r["atualizado_em"] = meta["atualizado_em"]
    return r


def listar():
    hist = _load_hist()
    rows = [_merge(h, hist) for h in listar_raw()]
    rows.sort(key=lambda x: int(x.get("id") or 0), reverse=True)
    return rows


def get(fatura_id):
    key = str(fatura_id or "").strip()
    if not key:
        return None
    out, _ = cobol_bridge._run(
        "gerir_faturas_venda", {"ACAO": "buscar", "ID": key}
    )
    text = (out or "").strip()
    if '"status":"erro"' in text.replace(" ", ""):
        return None
    start = text.find('{"id":')
    if start < 0:
        return None
    line = text[start:].splitlines()[0].strip()
    try:
        return _merge(json.loads(line), _load_hist())
    except json.JSONDecodeError:
        return None


def _env(row, *, with_id=False):
    r = row or {}
    env = {
        "NUMERO": _clip(r.get("numero"), 12),
        "PEDIDO_ID": _clip(r.get("pedido_id"), 10),
        "PEDIDO_NUM": _clip(r.get("pedido_numero"), 12),
        "PARTNER_ID": _clip(r.get("partner_id") or r.get("cliente_id"), 12),
        "CLIENTE": _clip(r.get("cliente"), 60),
        "CNPJ": _clip(r.get("cnpj"), 18),
        "EMISSAO": _clip(r.get("data_emissao"), 10),
        "VENCIMENTO": _clip(r.get("data_vencimento"), 10),
        "SUBTOTAL": str(r.get("subtotal") or 0),
        "IMPOSTOS": str(r.get("impostos") or 0),
        "TOTAL": str(r.get("total") or 0),
        "STATUS": _clip(r.get("status") or "PENDENTE", 12),
        "ITENS_COUNT": str(int(r.get("itens_count") or 0)),
        "ENTREGA_ID": _clip(r.get("entrega_id"), 24),
        "NFE_NUMERO": str(r.get("nfe_numero") or 0),
        "NFE_STATUS": _clip(r.get("nfe_status"), 12),
    }
    if with_id and r.get("id") not in (None, ""):
        env["ID"] = str(r.get("id"))
    return env


def save(row, *, is_new=False):
    r = dict(row or {})
    fid = r.get("id")
    if is_new or not fid:
        env = _env(r, with_id=bool(fid))
        env["ACAO"] = "incluir"
        if fid not in (None, ""):
            env["ID"] = str(fid)
        out, err = cobol_bridge._run("gerir_faturas_venda", env)
        new_id = None
        for line in (out or "").splitlines():
            line = line.strip()
            if line.startswith("ERRO:"):
                raise ValueError(line)
            if line.isdigit():
                new_id = int(line)
                break
        if new_id is None:
            raise ValueError("falha ao incluir fatura: " + (out or err or ""))
        fid = new_id
        r["id"] = fid
        if not r.get("numero"):
            r["numero"] = f"FV{int(fid):05d}"
    else:
        env = _env(r, with_id=True)
        env["ACAO"] = "alterar"
        env["ID"] = str(fid)
        out, err = cobol_bridge._run("gerir_faturas_venda", env)
        if "ERRO:" in (out or ""):
            raise ValueError((out or err or "").strip())

    hist = _load_hist()
    key = str(fid)
    prev = hist.get(key) or {}
    hist[key] = {
        "ar_titulos": list(r.get("ar_titulos") if r.get("ar_titulos") is not None
                           else prev.get("ar_titulos") or []),
        "atualizado_em": _now(),
    }
    _save_hist(hist)
    sync_json()
    return get(fid)


def sync_json(rows=None):
    data_rows = rows if rows is not None else listar()
    payload = {
        "faturas": data_rows,
        "total": len(data_rows),
        "source": "cobol:faturas_venda.dat",
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
            "faturas_venda.dat",
            "faturas_venda.tmp",
            "faturas_venda_hist.json",
        ):
            p = os.path.join(BASE_DIR, "dados", name)
            if os.path.exists(p):
                os.remove(p)
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("faturas") if isinstance(data, dict) else []
    n = 0
    for r in rows or []:
        try:
            save(dict(r), is_new=True)
            n += 1
        except Exception:
            continue
    sync_json()
    return {"migrated": n, "message": "ok"}
