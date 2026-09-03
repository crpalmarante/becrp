"""
WMS — Warehouse Locations (RFC-9002 MVP).

CRUD de endereços / posições físicas dentro de armazéns e áreas.
Fonte: dados/wms_locations.json
"""

from __future__ import annotations

import os
from datetime import datetime

import cobol_bridge
import wms_warehouses

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "wms_locations.json")

LOCATION_TYPES = {
    "receiving": "Recebimento",
    "quality": "Inspeção / Qualidade",
    "storage": "Armazenagem",
    "picking": "Picking",
    "packing": "Packing",
    "shipping": "Expedição",
    "transit": "Trânsito",
    "virtual": "Virtual",
}

LOCATION_STATUS = {
    "available": "Disponível",
    "restricted": "Restrita",
    "blocked": "Bloqueada",
    "inactive": "Inativa",
}

SEED = (
    {
        "codigo": "REC-DOCK-01",
        "nome": "Doca Recebimento 01",
        "tipo": "receiving",
        "armazem": "DC-01",
        "area": "REC",
        "status": "available",
    },
    {
        "codigo": "A01-01-01",
        "nome": "Corredor A · Rack 01 · Nível 01",
        "tipo": "storage",
        "armazem": "DC-01",
        "area": "STO",
        "zona": "GERAL",
        "corredor": "A01",
        "rack": "01",
        "nivel": "01",
        "posicao": "01",
        "capacidade_qtd": 40,
        "peso_max_kg": 500,
        "status": "available",
    },
    {
        "codigo": "A01-01-02",
        "nome": "Corredor A · Rack 01 · Nível 02",
        "tipo": "storage",
        "armazem": "DC-01",
        "area": "STO",
        "zona": "GERAL",
        "corredor": "A01",
        "rack": "01",
        "nivel": "02",
        "posicao": "01",
        "capacidade_qtd": 40,
        "peso_max_kg": 400,
        "status": "available",
    },
    {
        "codigo": "PCK-01",
        "nome": "Face Picking 01",
        "tipo": "picking",
        "armazem": "DC-01",
        "area": "PCK",
        "capacidade_qtd": 20,
        "status": "available",
    },
    {
        "codigo": "SHP-STAGE",
        "nome": "Staging Expedição",
        "tipo": "shipping",
        "armazem": "DC-01",
        "area": "SHP",
        "status": "available",
    },
    {
        "codigo": "LJ-STO-01",
        "nome": "Estoque Loja Principal",
        "tipo": "storage",
        "armazem": "LJ-01",
        "area": "STO",
        "capacidade_qtd": 200,
        "status": "available",
    },
    {
        "codigo": "LJ-RETIRA",
        "nome": "Retirada Cliente",
        "tipo": "shipping",
        "armazem": "LJ-01",
        "area": "SHP",
        "status": "available",
    },
)


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load_raw():
    """Lê as localizações direto do COBOL (dados/localizacoes.dat)."""
    rows = cobol_bridge.localizacoes_listar()
    if not rows:
        return ensure_seed()
    return {"atualizado_em": _now(), "localizacoes": rows, "total": len(rows)}


def ensure_seed():
    rows = []
    for s in SEED:
        row = _build_row(s, existing=None, codigo=s["codigo"])
        try:
            cobol_bridge.localizacoes_incluir(row)
        except ValueError as e:
            if "ja existe" not in str(e):
                raise
        rows.append(row)
    data = {"atualizado_em": _now(), "localizacoes": rows, "total": len(rows)}
    return data


def _norm_tipo(val):
    s = str(val or "").strip().lower()
    aliases = {
        "recebimento": "receiving",
        "qualidade": "quality",
        "inspecao": "quality",
        "inspeção": "quality",
        "armazenagem": "storage",
        "estoque": "storage",
        "expedicao": "shipping",
        "expedição": "shipping",
        "transito": "transit",
        "trânsito": "transit",
    }
    s = aliases.get(s, s)
    if s not in LOCATION_TYPES:
        raise ValueError(
            "tipo deve ser: receiving, quality, storage, picking, packing, shipping, transit ou virtual"
        )
    return s


def _norm_status(val):
    s = str(val or "").strip().lower()
    aliases = {
        "disponivel": "available",
        "disponível": "available",
        "restrita": "restricted",
        "restrito": "restricted",
        "bloqueada": "blocked",
        "bloqueado": "blocked",
        "inativa": "inactive",
        "inativo": "inactive",
    }
    s = aliases.get(s, s)
    if s not in LOCATION_STATUS:
        raise ValueError("status deve ser: available, restricted, blocked ou inactive")
    return s


def _opt_str(body, existing, key, upper=False, max_len=32):
    if key in body:
        val = str(body.get(key) or "").strip()
    else:
        val = str((existing or {}).get(key) or "").strip()
    if upper:
        val = val.upper()
    if len(val) > max_len:
        raise ValueError(f"{key} deve ter até {max_len} caracteres")
    return val


def _opt_num(body, existing, key):
    if key in body:
        raw = body.get(key)
    else:
        raw = (existing or {}).get(key)
    if raw is None or raw == "":
        return None
    try:
        n = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{key} deve ser número") from None
    if n < 0:
        raise ValueError(f"{key} não pode ser negativo")
    return n


def _validate_warehouse_area(armazem, area):
    wh = wms_warehouses.get_armazem(armazem)
    if not wh:
        raise ValueError(f"armazém não encontrado: {armazem}")
    if not wh.get("ativo", True):
        raise ValueError(f"armazém inativo: {armazem}")
    area_key = str(area or "").strip().upper()
    if not area_key:
        raise ValueError("área obrigatória")
    areas = {str(a.get("codigo") or "").upper(): a for a in (wh.get("areas") or [])}
    if area_key not in areas:
        raise ValueError(f"área {area_key} não existe no armazém {armazem}")
    if areas[area_key].get("ativo") is False:
        raise ValueError(f"área inativa: {area_key}")
    return wh, areas[area_key]


def _enrich(row):
    out = dict(row)
    out["tipo_label"] = LOCATION_TYPES.get(out.get("tipo"), out.get("tipo") or "")
    out["status_label"] = LOCATION_STATUS.get(out.get("status"), out.get("status") or "")
    wh = wms_warehouses.get_armazem(out.get("armazem"))
    out["armazem_nome"] = (wh or {}).get("nome") or ""
    area_cod = str(out.get("area") or "").upper()
    area_nome = ""
    if wh:
        for a in wh.get("areas") or []:
            if str(a.get("codigo") or "").upper() == area_cod:
                area_nome = a.get("nome") or ""
                break
    out["area_nome"] = area_nome
    return out


def _build_row(payload, existing=None, codigo=None):
    body = payload if isinstance(payload, dict) else {}
    cod = str(
        codigo
        or body.get("codigo")
        or (existing or {}).get("codigo")
        or ""
    ).strip().upper()
    if not cod:
        raise ValueError("codigo obrigatório")
    if len(cod) > 32:
        raise ValueError("codigo deve ter até 32 caracteres")

    nome = str(
        body.get("nome") if body.get("nome") is not None else (existing or {}).get("nome") or ""
    ).strip()
    if not nome:
        raise ValueError("nome obrigatório")

    tipo = _norm_tipo(
        body.get("tipo") if body.get("tipo") is not None else (existing or {}).get("tipo") or "storage"
    )
    status = _norm_status(
        body.get("status")
        if body.get("status") is not None
        else (existing or {}).get("status")
        or "available"
    )

    armazem = _opt_str(body, existing, "armazem", upper=True, max_len=16)
    if not armazem and "armazem" not in body:
        armazem = str((existing or {}).get("armazem") or "").strip().upper()
    # allow alias warehouse
    if not armazem:
        armazem = _opt_str(body, existing, "warehouse", upper=True, max_len=16)
    if not armazem:
        raise ValueError("armazém obrigatório")

    area = _opt_str(body, existing, "area", upper=True, max_len=12)
    if not area:
        raise ValueError("área obrigatória")

    _validate_warehouse_area(armazem, area)

    motivo = _opt_str(body, existing, "bloqueio_motivo", max_len=120)
    if status == "blocked" and not motivo:
        motivo = "bloqueio operacional"
    if status != "blocked":
        motivo = ""

    return {
        "codigo": cod,
        "nome": nome,
        "tipo": tipo,
        "armazem": armazem,
        "area": area,
        "zona": _opt_str(body, existing, "zona", upper=True, max_len=24),
        "corredor": _opt_str(body, existing, "corredor", upper=True, max_len=12),
        "rack": _opt_str(body, existing, "rack", upper=True, max_len=12),
        "nivel": _opt_str(body, existing, "nivel", upper=True, max_len=12),
        "posicao": _opt_str(body, existing, "posicao", upper=True, max_len=12),
        "capacidade_qtd": _opt_num(body, existing, "capacidade_qtd"),
        "peso_max_kg": _opt_num(body, existing, "peso_max_kg"),
        "volume_max_m3": _opt_num(body, existing, "volume_max_m3"),
        "status": status,
        "bloqueio_motivo": motivo,
        "origem": (existing or {}).get("origem") or "manual",
        "atualizado_em": _now(),
    }


def meta():
    data = _load_raw()
    return {
        "total": len(data.get("localizacoes") or []),
        "tipos": LOCATION_TYPES,
        "status": LOCATION_STATUS,
        "atualizado_em": data.get("atualizado_em"),
    }


def list_localizacoes(q=None, armazem=None, area=None, tipo=None, status=None):
    rows = list(_load_raw().get("localizacoes") or [])
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r
            for r in rows
            if qq in str(r.get("codigo") or "").lower()
            or qq in str(r.get("nome") or "").lower()
            or qq in str(r.get("armazem") or "").lower()
            or qq in str(r.get("area") or "").lower()
            or qq in str(r.get("zona") or "").lower()
            or qq in str(r.get("corredor") or "").lower()
        ]
    if armazem:
        ak = str(armazem).strip().upper()
        rows = [r for r in rows if str(r.get("armazem") or "").upper() == ak]
    if area:
        aa = str(area).strip().upper()
        rows = [r for r in rows if str(r.get("area") or "").upper() == aa]
    if tipo:
        t = _norm_tipo(tipo)
        rows = [r for r in rows if r.get("tipo") == t]
    if status:
        st = _norm_status(status)
        rows = [r for r in rows if r.get("status") == st]
    rows.sort(
        key=lambda r: (
            str(r.get("armazem") or ""),
            str(r.get("area") or ""),
            str(r.get("codigo") or ""),
        )
    )
    return {
        "total": len(_load_raw().get("localizacoes") or []),
        "filtrado": len(rows),
        "tipos": LOCATION_TYPES,
        "status_opcoes": LOCATION_STATUS,
        "localizacoes": [_enrich(r) for r in rows],
    }


def get_localizacao(codigo):
    key = str(codigo or "").strip().upper()
    if not key:
        return None
    row = cobol_bridge.localizacoes_buscar(key)
    return _enrich(row) if row else None


def create_localizacao(payload):
    body = dict(payload or {})
    codigo = str(body.get("codigo") or "").strip().upper()
    if not codigo:
        raise ValueError("codigo obrigatório")
    if any(str(r.get("codigo") or "").upper() == codigo for r in _load_raw().get("localizacoes") or []):
        raise ValueError(f"já existe localização com código {codigo}")
    row = _build_row(body, codigo=codigo)
    row["origem"] = "manual"
    cobol_bridge.localizacoes_incluir(row)
    return _enrich(row)


def update_localizacao(codigo, payload):
    key = str(codigo or "").strip().upper()
    existing = next(
        (
            r
            for r in _load_raw().get("localizacoes") or []
            if str(r.get("codigo") or "").upper() == key
        ),
        None,
    )
    if existing is None:
        raise ValueError("localização não encontrada")
    body = dict(payload or {})
    body.pop("codigo", None)
    row = _build_row(body, existing=existing, codigo=existing.get("codigo"))
    row["origem"] = existing.get("origem") or "manual"
    cobol_bridge.localizacoes_alterar(row)
    return _enrich(row)


def delete_localizacao(codigo):
    key = str(codigo or "").strip().upper()
    if not any(str(r.get("codigo") or "").upper() == key for r in _load_raw().get("localizacoes") or []):
        raise ValueError("localização não encontrada")
    cobol_bridge.localizacoes_excluir(key)
    return True


def set_status(codigo, status, motivo=None):
    body = {"status": status}
    if motivo is not None:
        body["bloqueio_motivo"] = motivo
    return update_localizacao(codigo, body)
