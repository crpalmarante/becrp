"""
WMS — Operation Types (RFC-9003 MVP).

Catálogo de tipos de operação (comportamento padrão do armazém).
Fonte: dados/wms_operation_types.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "wms_operation_types.json")

DIRECTIONS = {
    "incoming": "Entrada",
    "internal": "Interna",
    "outgoing": "Saída",
}

# Templates padrão da RFC-9003
TEMPLATES = {
    "purchase_receipt": "Recebimento de Compra",
    "customer_shipment": "Expedição ao Cliente",
    "internal_transfer": "Transferência Interna",
    "repair_shipment": "Envio para Reparo",
    "customer_return": "Devolução de Cliente",
    "inventory_adjustment": "Ajuste de Inventário",
    "cross_docking": "Cross Docking",
    "custom": "Personalizado",
}

# Tipos de localização (RFC-9002) usados como regra opcional origem/destino
LOCATION_TYPE_HINTS = {
    "receiving": "Recebimento",
    "quality": "Qualidade",
    "storage": "Armazenagem",
    "picking": "Picking",
    "packing": "Packing",
    "shipping": "Expedição",
    "transit": "Trânsito",
    "virtual": "Virtual",
    "": "Qualquer",
}

SEED = (
    {
        "codigo": "REC-COMPRA",
        "nome": "Recebimento de Compra",
        "template": "purchase_receipt",
        "direcao": "incoming",
        "documentos": ["pedido_compra", "nfe"],
        "workflow": ["receive", "inspect", "putaway"],
        "origem_loc_tipo": "",
        "destino_loc_tipo": "receiving",
        "gera_tarefas": True,
        "descricao": "Recebe produtos do fornecedor até a área de recebimento.",
    },
    {
        "codigo": "EXP-CLIENTE",
        "nome": "Expedição ao Cliente",
        "template": "customer_shipment",
        "direcao": "outgoing",
        "documentos": ["pedido_venda"],
        "workflow": ["pick", "pack", "ship"],
        "origem_loc_tipo": "storage",
        "destino_loc_tipo": "shipping",
        "gera_tarefas": True,
        "descricao": "Separa, embala e expede pedidos de venda.",
    },
    {
        "codigo": "TRF-INT",
        "nome": "Transferência Interna",
        "template": "internal_transfer",
        "direcao": "internal",
        "documentos": ["transferencia"],
        "workflow": ["pick", "transit", "receive"],
        "origem_loc_tipo": "storage",
        "destino_loc_tipo": "storage",
        "gera_tarefas": True,
        "descricao": "Move estoque entre armazéns ou áreas.",
    },
    {
        "codigo": "REP-ENVIO",
        "nome": "Envio para Reparo",
        "template": "repair_shipment",
        "direcao": "outgoing",
        "documentos": ["ordem_reparo"],
        "workflow": ["pick", "ship", "return"],
        "origem_loc_tipo": "storage",
        "destino_loc_tipo": "virtual",
        "gera_tarefas": True,
        "descricao": "Envia produto para assistência (empresa mantém posse).",
    },
    {
        "codigo": "DEV-CLIENTE",
        "nome": "Devolução de Cliente",
        "template": "customer_return",
        "direcao": "incoming",
        "documentos": ["devolucao"],
        "workflow": ["receive", "inspect", "putaway"],
        "origem_loc_tipo": "",
        "destino_loc_tipo": "returns",
        "gera_tarefas": True,
        "descricao": "Recebe devolução, inspeciona e decide destino.",
    },
    {
        "codigo": "AJUSTE-INV",
        "nome": "Ajuste de Inventário",
        "template": "inventory_adjustment",
        "direcao": "internal",
        "documentos": ["contagem"],
        "workflow": ["count", "adjust"],
        "origem_loc_tipo": "storage",
        "destino_loc_tipo": "virtual",
        "gera_tarefas": False,
        "descricao": "Corrige diferenças físicas (requer autorização).",
    },
    {
        "codigo": "XDOCK",
        "nome": "Cross Docking",
        "template": "cross_docking",
        "direcao": "internal",
        "documentos": ["pedido_compra", "pedido_venda"],
        "workflow": ["receive", "ship"],
        "origem_loc_tipo": "receiving",
        "destino_loc_tipo": "shipping",
        "gera_tarefas": True,
        "descricao": "Recebe e expede sem armazenagem intermediária.",
    },
)


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load_raw():
    if not os.path.exists(DATA_FILE):
        return ensure_seed()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return ensure_seed()
    if not isinstance(data.get("tipos"), list):
        data["tipos"] = []
    if not data["tipos"]:
        return ensure_seed()
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("tipos") or [])
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def ensure_seed():
    rows = [_build_row(s, existing=None, codigo=s["codigo"]) for s in SEED]
    data = {"atualizado_em": _now(), "tipos": rows, "total": len(rows)}
    _save(data)
    return data


def _norm_direcao(val):
    s = str(val or "").strip().lower()
    aliases = {
        "entrada": "incoming",
        "in": "incoming",
        "interna": "internal",
        "interno": "internal",
        "saida": "outgoing",
        "saída": "outgoing",
        "out": "outgoing",
    }
    s = aliases.get(s, s)
    if s not in DIRECTIONS:
        raise ValueError("direcao deve ser: incoming, internal ou outgoing")
    return s


def _norm_template(val):
    s = str(val or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "recebimento": "purchase_receipt",
        "recebimento_compra": "purchase_receipt",
        "expedicao": "customer_shipment",
        "expedição": "customer_shipment",
        "transferencia": "internal_transfer",
        "transferência": "internal_transfer",
        "reparo": "repair_shipment",
        "devolucao": "customer_return",
        "devolução": "customer_return",
        "ajuste": "inventory_adjustment",
        "inventario": "inventory_adjustment",
        "inventário": "inventory_adjustment",
        "crossdock": "cross_docking",
        "cross_dock": "cross_docking",
    }
    s = aliases.get(s, s)
    if s not in TEMPLATES:
        raise ValueError(
            "template deve ser: purchase_receipt, customer_shipment, internal_transfer, "
            "repair_shipment, customer_return, inventory_adjustment, cross_docking ou custom"
        )
    return s


def _norm_loc_tipo(val):
    s = str(val or "").strip().lower()
    if not s:
        return ""
    # returns exists as area tipo in warehouses; map to storage/shipping if needed for locs
    aliases = {
        "recebimento": "receiving",
        "qualidade": "quality",
        "armazenagem": "storage",
        "estoque": "storage",
        "expedicao": "shipping",
        "expedição": "shipping",
        "transito": "transit",
        "trânsito": "transit",
        "devolucao": "shipping",
        "devolução": "shipping",
        "returns": "shipping",
    }
    s = aliases.get(s, s)
    if s not in LOCATION_TYPE_HINTS:
        raise ValueError(
            "origem/destino loc_tipo deve ser tipo de localização válido ou vazio"
        )
    return s


def _as_str_list(val, field):
    if val is None:
        return []
    if isinstance(val, str):
        parts = [p.strip() for p in val.replace(";", ",").split(",") if p.strip()]
        return parts
    if isinstance(val, list):
        out = []
        for item in val:
            s = str(item or "").strip()
            if s:
                out.append(s)
        return out
    raise ValueError(f"{field} deve ser lista ou texto separado por vírgula")


def _enrich(row):
    out = dict(row)
    out["direcao_label"] = DIRECTIONS.get(out.get("direcao"), out.get("direcao") or "")
    out["template_label"] = TEMPLATES.get(out.get("template"), out.get("template") or "")
    ol = out.get("origem_loc_tipo") or ""
    dl = out.get("destino_loc_tipo") or ""
    out["origem_loc_tipo_label"] = LOCATION_TYPE_HINTS.get(ol, ol or "Qualquer")
    out["destino_loc_tipo_label"] = LOCATION_TYPE_HINTS.get(dl, dl or "Qualquer")
    out["documentos_txt"] = ", ".join(out.get("documentos") or [])
    out["workflow_txt"] = " → ".join(out.get("workflow") or [])
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
    if len(cod) > 24:
        raise ValueError("codigo deve ter até 24 caracteres")

    nome = str(
        body.get("nome") if body.get("nome") is not None else (existing or {}).get("nome") or ""
    ).strip()
    if not nome:
        raise ValueError("nome obrigatório")

    template = _norm_template(
        body.get("template")
        if body.get("template") is not None
        else (existing or {}).get("template")
        or "custom"
    )
    direcao = _norm_direcao(
        body.get("direcao")
        if body.get("direcao") is not None
        else (existing or {}).get("direcao")
        or "internal"
    )

    if "documentos" in body:
        documentos = _as_str_list(body.get("documentos"), "documentos")
    else:
        documentos = list((existing or {}).get("documentos") or [])

    if "workflow" in body:
        workflow = _as_str_list(body.get("workflow"), "workflow")
    else:
        workflow = list((existing or {}).get("workflow") or [])

    if "origem_loc_tipo" in body:
        origem = _norm_loc_tipo(body.get("origem_loc_tipo"))
    else:
        origem = _norm_loc_tipo((existing or {}).get("origem_loc_tipo") or "")

    if "destino_loc_tipo" in body:
        destino = _norm_loc_tipo(body.get("destino_loc_tipo"))
    else:
        destino = _norm_loc_tipo((existing or {}).get("destino_loc_tipo") or "")

    if "gera_tarefas" in body:
        gera = bool(body.get("gera_tarefas"))
    else:
        gera = bool((existing or {}).get("gera_tarefas", True))

    if "ativo" in body:
        ativo = bool(body.get("ativo"))
    else:
        ativo = bool((existing or {}).get("ativo", True))

    descricao = str(
        body.get("descricao")
        if body.get("descricao") is not None
        else (existing or {}).get("descricao")
        or ""
    ).strip()

    return {
        "codigo": cod,
        "nome": nome,
        "template": template,
        "direcao": direcao,
        "documentos": documentos,
        "workflow": workflow,
        "origem_loc_tipo": origem,
        "destino_loc_tipo": destino,
        "gera_tarefas": gera,
        "ativo": ativo,
        "descricao": descricao,
        "origem": (existing or {}).get("origem") or "manual",
        "atualizado_em": _now(),
    }


def meta():
    data = _load_raw()
    return {
        "total": len(data.get("tipos") or []),
        "direcoes": DIRECTIONS,
        "templates": TEMPLATES,
        "loc_tipos": LOCATION_TYPE_HINTS,
        "atualizado_em": data.get("atualizado_em"),
    }


def list_tipos(q=None, direcao=None, template=None, ativos=None):
    rows = list(_load_raw().get("tipos") or [])
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r
            for r in rows
            if qq in str(r.get("codigo") or "").lower()
            or qq in str(r.get("nome") or "").lower()
            or qq in str(r.get("template") or "").lower()
            or qq in str(r.get("descricao") or "").lower()
            or any(qq in str(d).lower() for d in (r.get("documentos") or []))
        ]
    if direcao:
        d = _norm_direcao(direcao)
        rows = [r for r in rows if r.get("direcao") == d]
    if template:
        t = _norm_template(template)
        rows = [r for r in rows if r.get("template") == t]
    if ativos is True:
        rows = [r for r in rows if r.get("ativo", True)]
    elif ativos is False:
        rows = [r for r in rows if not r.get("ativo", True)]
    rows.sort(key=lambda r: (str(r.get("direcao") or ""), str(r.get("codigo") or "")))
    return {
        "total": len(_load_raw().get("tipos") or []),
        "filtrado": len(rows),
        "direcoes": DIRECTIONS,
        "templates": TEMPLATES,
        "loc_tipos": LOCATION_TYPE_HINTS,
        "tipos": [_enrich(r) for r in rows],
    }


def get_tipo(codigo):
    key = str(codigo or "").strip().upper()
    if not key:
        return None
    for r in _load_raw().get("tipos") or []:
        if str(r.get("codigo") or "").upper() == key:
            return _enrich(r)
    return None


def create_tipo(payload):
    data = _load_raw()
    body = dict(payload or {})
    codigo = str(body.get("codigo") or "").strip().upper()
    if not codigo:
        raise ValueError("codigo obrigatório")
    if any(str(r.get("codigo") or "").upper() == codigo for r in data["tipos"]):
        raise ValueError(f"já existe tipo de operação com código {codigo}")
    row = _build_row(body, codigo=codigo)
    row["origem"] = "manual"
    data["tipos"].append(row)
    _save(data)
    return _enrich(row)


def update_tipo(codigo, payload):
    data = _load_raw()
    key = str(codigo or "").strip().upper()
    idx = None
    existing = None
    for i, r in enumerate(data.get("tipos") or []):
        if str(r.get("codigo") or "").upper() == key:
            idx = i
            existing = r
            break
    if existing is None:
        raise ValueError("tipo de operação não encontrado")
    body = dict(payload or {})
    body.pop("codigo", None)
    row = _build_row(body, existing=existing, codigo=existing.get("codigo"))
    row["origem"] = existing.get("origem") or "manual"
    data["tipos"][idx] = row
    _save(data)
    return _enrich(row)


def delete_tipo(codigo):
    data = _load_raw()
    key = str(codigo or "").strip().upper()
    idx = None
    for i, r in enumerate(data.get("tipos") or []):
        if str(r.get("codigo") or "").upper() == key:
            idx = i
            break
    if idx is None:
        raise ValueError("tipo de operação não encontrado")
    data["tipos"].pop(idx)
    _save(data)
    return True
