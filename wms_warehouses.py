"""
WMS — Warehouse Structure (RFC-9001 MVP).

CRUD de armazéns e áreas operacionais.
Fonte: dados/wms_warehouses.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "wms_warehouses.json")

WAREHOUSE_TYPES = {
    "distribution_center": "Centro de Distribuição",
    "retail_store": "Loja",
    "repair_center": "Centro de Reparo",
    "transit": "Trânsito",
}

AREA_TYPES = {
    "receiving": "Recebimento",
    "storage": "Armazenagem",
    "picking": "Picking",
    "packing": "Packing",
    "shipping": "Expedição",
    "returns": "Devoluções",
    "other": "Outra",
}

DEFAULT_AREAS = (
    {"codigo": "REC", "nome": "Recebimento", "tipo": "receiving"},
    {"codigo": "STO", "nome": "Armazenagem", "tipo": "storage"},
    {"codigo": "PCK", "nome": "Picking", "tipo": "picking"},
    {"codigo": "PKG", "nome": "Packing", "tipo": "packing"},
    {"codigo": "SHP", "nome": "Expedição", "tipo": "shipping"},
    {"codigo": "RET", "nome": "Devoluções", "tipo": "returns"},
)

SEED = (
    {
        "codigo": "DC-01",
        "nome": "Armazém Principal",
        "tipo": "distribution_center",
        "endereco": "",
        "responsavel": "",
        "areas": list(DEFAULT_AREAS),
    },
    {
        "codigo": "LJ-01",
        "nome": "Loja Matriz",
        "tipo": "retail_store",
        "endereco": "",
        "responsavel": "",
        "areas": [
            {"codigo": "STO", "nome": "Estoque Loja", "tipo": "storage"},
            {"codigo": "SHP", "nome": "Retirada / Expedição", "tipo": "shipping"},
        ],
    },
)


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _empty():
    return {"atualizado_em": None, "armazens": []}


def _load_raw():
    if not os.path.exists(DATA_FILE):
        return ensure_seed()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return ensure_seed()
    if not isinstance(data.get("armazens"), list):
        data["armazens"] = []
    if not data["armazens"]:
        return ensure_seed()
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("armazens") or [])
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def ensure_seed():
    rows = [_build_warehouse(s, existing=None, codigo=s["codigo"]) for s in SEED]
    data = {"atualizado_em": _now(), "armazens": rows, "total": len(rows)}
    _save(data)
    return data


def _norm_wh_tipo(val):
    s = str(val or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "cd": "distribution_center",
        "dc": "distribution_center",
        "distribuicao": "distribution_center",
        "distribuição": "distribution_center",
        "loja": "retail_store",
        "store": "retail_store",
        "retail": "retail_store",
        "reparo": "repair_center",
        "repair": "repair_center",
        "transito": "transit",
        "trânsito": "transit",
    }
    s = aliases.get(s, s)
    if s not in WAREHOUSE_TYPES:
        raise ValueError(
            "tipo deve ser: distribution_center, retail_store, repair_center ou transit"
        )
    return s


def _norm_area_tipo(val):
    s = str(val or "").strip().lower()
    aliases = {
        "recebimento": "receiving",
        "armazenagem": "storage",
        "estoque": "storage",
        "expedicao": "shipping",
        "expedição": "shipping",
        "devolucao": "returns",
        "devolução": "returns",
        "devolucoes": "returns",
        "outra": "other",
    }
    s = aliases.get(s, s)
    if s not in AREA_TYPES:
        raise ValueError(
            "tipo de área deve ser: receiving, storage, picking, packing, shipping, returns ou other"
        )
    return s


def _build_area(payload, existing=None):
    body = payload if isinstance(payload, dict) else {}
    codigo = str(
        body.get("codigo") or (existing or {}).get("codigo") or ""
    ).strip().upper()
    if not codigo:
        raise ValueError("código da área obrigatório")
    if len(codigo) > 12:
        raise ValueError("código da área deve ter até 12 caracteres")
    nome = str(
        body.get("nome") if body.get("nome") is not None else (existing or {}).get("nome") or ""
    ).strip()
    if not nome:
        raise ValueError("nome da área obrigatório")
    tipo = _norm_area_tipo(
        body.get("tipo") if body.get("tipo") is not None else (existing or {}).get("tipo") or "other"
    )
    ativo = body.get("ativo") if "ativo" in body else (existing or {}).get("ativo", True)
    return {
        "codigo": codigo,
        "nome": nome,
        "tipo": tipo,
        "ativo": bool(ativo),
    }


def _normalize_areas(raw):
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("areas deve ser lista")
    seen = set()
    out = []
    for item in raw:
        area = _build_area(item)
        if area["codigo"] in seen:
            raise ValueError(f"área duplicada: {area['codigo']}")
        seen.add(area["codigo"])
        out.append(area)
    return out


def _enrich(row):
    out = dict(row)
    out["tipo_label"] = WAREHOUSE_TYPES.get(out.get("tipo"), out.get("tipo") or "")
    areas = []
    for a in out.get("areas") or []:
        aa = dict(a)
        aa["tipo_label"] = AREA_TYPES.get(aa.get("tipo"), aa.get("tipo") or "")
        areas.append(aa)
    out["areas"] = areas
    out["areas_count"] = len(areas)
    return out


def _build_warehouse(payload, existing=None, codigo=None):
    body = payload if isinstance(payload, dict) else {}
    cod = str(
        codigo
        or body.get("codigo")
        or (existing or {}).get("codigo")
        or ""
    ).strip().upper()
    if not cod:
        raise ValueError("codigo obrigatório")
    if len(cod) > 16:
        raise ValueError("codigo deve ter até 16 caracteres")
    nome = str(
        body.get("nome") if body.get("nome") is not None else (existing or {}).get("nome") or ""
    ).strip()
    if not nome:
        raise ValueError("nome obrigatório")
    tipo = _norm_wh_tipo(
        body.get("tipo")
        if body.get("tipo") is not None
        else (existing or {}).get("tipo")
        or "distribution_center"
    )
    endereco = str(
        body.get("endereco")
        if body.get("endereco") is not None
        else (existing or {}).get("endereco")
        or ""
    ).strip()
    responsavel = str(
        body.get("responsavel")
        if body.get("responsavel") is not None
        else (existing or {}).get("responsavel")
        or ""
    ).strip()
    ativo = body.get("ativo") if "ativo" in body else (existing or {}).get("ativo", True)
    if "areas" in body:
        areas = _normalize_areas(body.get("areas"))
    else:
        areas = _normalize_areas((existing or {}).get("areas") or [])
    return {
        "codigo": cod,
        "nome": nome,
        "tipo": tipo,
        "endereco": endereco,
        "responsavel": responsavel,
        "ativo": bool(ativo),
        "areas": areas,
        "origem": (existing or {}).get("origem") or "manual",
        "atualizado_em": _now(),
    }


def meta():
    data = _load_raw()
    return {
        "total": len(data.get("armazens") or []),
        "tipos": WAREHOUSE_TYPES,
        "tipos_area": AREA_TYPES,
        "atualizado_em": data.get("atualizado_em"),
    }


def list_armazens(q=None, tipo=None, ativos=None):
    rows = list(_load_raw().get("armazens") or [])
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            w
            for w in rows
            if qq in str(w.get("codigo") or "").lower()
            or qq in str(w.get("nome") or "").lower()
            or qq in str(w.get("tipo") or "").lower()
            or qq in str(w.get("responsavel") or "").lower()
        ]
    if tipo:
        t = _norm_wh_tipo(tipo)
        rows = [w for w in rows if w.get("tipo") == t]
    if ativos is True:
        rows = [w for w in rows if w.get("ativo", True)]
    elif ativos is False:
        rows = [w for w in rows if not w.get("ativo", True)]
    rows.sort(key=lambda w: str(w.get("codigo") or ""))
    return {
        "total": len(_load_raw().get("armazens") or []),
        "filtrado": len(rows),
        "tipos": WAREHOUSE_TYPES,
        "tipos_area": AREA_TYPES,
        "armazens": [_enrich(w) for w in rows],
    }


def get_armazem(codigo):
    key = str(codigo or "").strip().upper()
    if not key:
        return None
    for w in _load_raw().get("armazens") or []:
        if str(w.get("codigo") or "").upper() == key:
            return _enrich(w)
    return None


def map_armazem_to_estabelecimento(armazem_codigo):
    """Mapeamento inverso: armazém -> estabelecimento_id."""
    key = str(armazem_codigo or "").strip().upper()
    if not key:
        return None
    rows = _load_raw().get("armazens") or []
    for w in rows:
        if str(w.get("codigo") or "").upper() == key:
            eid = w.get("estabelecimento_id")
            if eid:
                return str(eid)
            return w["codigo"]
    return None


def map_estabelecimento_to_armazem(estabelecimento_id):
    """Mapeamento simples: estabelecimento_id -> primeiro armazém ou DC-01."""
    eid = str(estabelecimento_id or "").strip().upper()
    if not eid:
        return None
    rows = _load_raw().get("armazens") or []
    # tenta match direto
    for w in rows:
        if str(w.get("codigo") or "").upper() == eid:
            return w["codigo"]
    for w in rows:
        if str(w.get("estabelecimento_id") or "").upper() == eid:
            return w["codigo"]
    # fallback: primeiro CD, depois primeiro armazém
    for w in rows:
        if w.get("tipo") == "distribution_center":
            return w["codigo"]
    return rows[0]["codigo"] if rows else None


def get_default_receiving_location(armazem_codigo):
    wh = get_armazem(armazem_codigo)
    if not wh:
        return "REC-DOCK-01"
    for area in wh.get("areas") or []:
        if area.get("tipo") == "receiving":
            return f"{area['codigo']}-DOCK-01"
    return "REC-DOCK-01"


def create_armazem(payload):
    data = _load_raw()
    body = dict(payload or {})
    codigo = str(body.get("codigo") or "").strip().upper()
    if not codigo:
        raise ValueError("codigo obrigatório")
    if any(str(w.get("codigo") or "").upper() == codigo for w in data["armazens"]):
        raise ValueError(f"já existe armazém com código {codigo}")
    if "areas" not in body:
        body["areas"] = list(DEFAULT_AREAS)
    row = _build_warehouse(body, codigo=codigo)
    row["origem"] = "manual"
    data["armazens"].append(row)
    _save(data)
    return _enrich(row)


def update_armazem(codigo, payload):
    data = _load_raw()
    key = str(codigo or "").strip().upper()
    idx = None
    existing = None
    for i, w in enumerate(data.get("armazens") or []):
        if str(w.get("codigo") or "").upper() == key:
            idx = i
            existing = w
            break
    if existing is None:
        raise ValueError("armazém não encontrado")
    body = dict(payload or {})
    body.pop("codigo", None)
    row = _build_warehouse(body, existing=existing, codigo=existing.get("codigo"))
    row["origem"] = existing.get("origem") or "manual"
    data["armazens"][idx] = row
    _save(data)
    return _enrich(row)


def delete_armazem(codigo):
    data = _load_raw()
    key = str(codigo or "").strip().upper()
    idx = None
    for i, w in enumerate(data.get("armazens") or []):
        if str(w.get("codigo") or "").upper() == key:
            idx = i
            break
    if idx is None:
        raise ValueError("armazém não encontrado")
    data["armazens"].pop(idx)
    _save(data)
    return True


def set_areas(codigo, areas):
    """Substitui a lista de áreas do armazém."""
    return update_armazem(codigo, {"areas": areas})
