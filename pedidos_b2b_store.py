"""
Pedidos B2B — store COBOL (fonte da verdade).

.dat SEQUENTIAL:
  dados/pedidos_b2b.dat       — cabeçalho
  dados/itens_pedido_b2b.dat  — linhas

Projeção: dados/pedidos_b2b.json (consulta/relatório).
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime

import cobol_bridge
import jsonio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "dados", "pedidos_b2b.json")
DAT_HEADER = os.path.join(BASE_DIR, "dados", "pedidos_b2b.dat")
DAT_ITENS = os.path.join(BASE_DIR, "dados", "itens_pedido_b2b.dat")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _clip(val, n):
    s = str(val if val is not None else "")
    s = s.replace('"', "'").replace("\n", " ").replace("\r", " ")
    return s[:n]


def _parse_json_blob(out, key):
    text = (out or "").strip()
    marker = '{"' + key + '":'
    start = text.find(marker)
    if start < 0:
        return []
    try:
        data = json.loads(text[start:])
        return data.get(key) or []
    except json.JSONDecodeError:
        rows = []
        for line in text.splitlines():
            line = line.strip().rstrip(",")
            if line.startswith("{") and '"id"' in line or '"prod_id"' in line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return rows


def _header_env(pedido, *, with_id=True):
    p = pedido or {}
    smart = p.get("smart") or {}
    env = {
        "NUMERO": _clip(p.get("numero"), 12),
        "TIPO": _clip(p.get("tipo") or "pedido", 10),
        "STATUS": _clip(p.get("status") or "rascunho", 12),
        "DATA": _clip(p.get("data"), 10),
        "VALIDADE": _clip(p.get("validade"), 10),
        "CLIENTE_ID": _clip(p.get("cliente_id"), 12),
        "RAZAO_SOCIAL": _clip(p.get("razao_social"), 60),
        "CNPJ": _clip(p.get("cnpj"), 18),
        "IE": _clip(p.get("ie"), 20),
        "CIDADE": _clip(p.get("cidade"), 30),
        "UF": _clip(p.get("uf"), 2),
        "ENDERECO_COBRANCA": _clip(p.get("endereco_cobranca"), 80),
        "ENDERECO_ENTREGA": _clip(p.get("endereco_entrega"), 80),
        "LISTA_PRECOS": _clip(p.get("lista_precos"), 40),
        "LISTA_PRECOS_ID": _clip(p.get("lista_precos_id"), 20),
        "VENDEDOR": _clip(p.get("vendedor"), 30),
        "PAYMENT_TERMS": _clip(p.get("payment_terms") or p.get("condicao_pg"), 20),
        "FORMA_PG": _clip(p.get("forma_pg"), 20),
        "TOTAL": str(p.get("total") or 0),
        "FATURA_ID": _clip(p.get("fatura_id"), 10),
        "FATURA_NUMERO": _clip(p.get("fatura_numero"), 12),
        "NFE_NUMERO": str(p.get("nfe_numero") or 0),
        "NFE_STATUS": _clip(p.get("nfe_status"), 12),
        "ENTREGA_ID": _clip(p.get("entrega_id"), 24),
        "RESERVA_ID": _clip(p.get("reserva_id"), 16),
        "SMART_ENTREGAS": str(smart.get("entregas") or 0),
        "SMART_FATURAS": str(smart.get("faturas") or 0),
        "NOTAS": _clip(p.get("notas"), 80),
    }
    if with_id and p.get("id") is not None:
        env["ID"] = str(p.get("id"))
    return env


def _normalize_header(h):
    if not isinstance(h, dict):
        return {}
    out = dict(h)
    try:
        out["id"] = int(out.get("id") or 0)
    except (TypeError, ValueError):
        out["id"] = out.get("id")
    smart = out.get("smart")
    if not isinstance(smart, dict):
        out["smart"] = {"entregas": 0, "faturas": 0, "compras": 0,
                        "assinaturas": 0, "projetos": 0, "tarefas": 0}
    else:
        out["smart"] = {
            "entregas": int(smart.get("entregas") or 0),
            "faturas": int(smart.get("faturas") or 0),
            "compras": int(smart.get("compras") or 0),
            "assinaturas": int(smart.get("assinaturas") or 0),
            "projetos": int(smart.get("projetos") or 0),
            "tarefas": int(smart.get("tarefas") or 0),
        }
    # nfe_numero 0 → omitir
    try:
        if int(out.get("nfe_numero") or 0) == 0:
            out.pop("nfe_numero", None)
    except (TypeError, ValueError):
        pass
    if not out.get("fatura_id"):
        out.pop("fatura_id", None)
    if not out.get("entrega_id"):
        out.pop("entrega_id", None)
    if not out.get("reserva_id"):
        out.pop("reserva_id", None)
    return out


def _normalize_item(it):
    qtd = float(it.get("qtd") or 0)
    preco = float(it.get("preco") or 0)
    desc = float(it.get("desconto") or 0)
    sub = qtd * preco * (1 - desc / 100.0)
    return {
        "prod_id": it.get("prod_id") or "",
        "produto": it.get("produto") or "",
        "qtd": qtd,
        "uom": it.get("uom") or "UN",
        "preco": preco,
        "desconto": desc,
        "imposto": float(it.get("imposto") or 0),
        "subtotal": round(sub, 2),
    }


def listar_cabecalhos():
    out, _ = cobol_bridge._run("gerir_pedidos_b2b", {"ACAO": "listar"})
    return [_normalize_header(h) for h in _parse_json_blob(out, "pedidos")]


def listar_itens(pedido_id=None):
    if pedido_id is None:
        out, _ = cobol_bridge._run("gerir_itens_ped_b2b", {"ACAO": "listar"})
    else:
        out, _ = cobol_bridge._run(
            "gerir_itens_ped_b2b",
            {"ACAO": "listar-ped", "PEDIDO_ID": str(pedido_id)},
        )
    return [_normalize_item(i) for i in _parse_json_blob(out, "itens")]


def listar():
    """Pedidos completos (header + itens) — ordem id desc (recente primeiro)."""
    headers = listar_cabecalhos()
    all_items = listar_itens()
    by_pid = {}
    for it in all_items:
        # listar all doesn't include pedido_id in normalize - fix
        pass
    # reload raw for pedido_id
    out, _ = cobol_bridge._run("gerir_itens_ped_b2b", {"ACAO": "listar"})
    raw_items = _parse_json_blob(out, "itens")
    by_pid = {}
    for it in raw_items:
        pid = str(it.get("pedido_id") or "")
        by_pid.setdefault(pid, []).append(_normalize_item(it))

    pedidos = []
    for h in headers:
        p = dict(h)
        p["itens"] = by_pid.get(str(p.get("id")), [])
        if p.get("payment_terms") and not p.get("condicao_pg"):
            p["condicao_pg"] = p["payment_terms"]
        pedidos.append(p)
    pedidos.sort(key=lambda x: int(x.get("id") or 0), reverse=True)
    return pedidos


def get(pedido_id):
    out, _ = cobol_bridge._run(
        "gerir_pedidos_b2b", {"ACAO": "buscar", "ID": str(pedido_id)}
    )
    text = (out or "").strip()
    if '"status":"erro"' in text.replace(" ", ""):
        return None
    start = text.find('{"id":')
    if start < 0:
        return None
    # pode ter só uma linha
    line = text[start:].splitlines()[0].strip()
    try:
        h = _normalize_header(json.loads(line))
    except json.JSONDecodeError:
        return None
    h["itens"] = listar_itens(pedido_id)
    return h


def _replace_itens(pedido_id, itens):
    cobol_bridge._run(
        "gerir_itens_ped_b2b",
        {"ACAO": "limpar", "PEDIDO_ID": str(pedido_id)},
    )
    for i, it in enumerate(itens or [], start=1):
        cobol_bridge._run(
            "gerir_itens_ped_b2b",
            {
                "ACAO": "incluir",
                "PEDIDO_ID": str(pedido_id),
                "SEQ": str(i),
                "PROD_ID": _clip(it.get("prod_id") or it.get("id"), 10),
                "PRODUTO": _clip(it.get("produto"), 40),
                "UOM": _clip(it.get("uom") or "UN", 4),
                "QTD": str(it.get("qtd") or 0),
                "PRECO": str(it.get("preco") or 0),
                "DESCONTO": str(it.get("desconto") or 0),
                "IMPOSTO": str(it.get("imposto") or 0),
            },
        )


def _calc_total(itens):
    total = 0.0
    for it in itens or []:
        qtd = float(it.get("qtd") or 0)
        preco = float(it.get("preco") or 0)
        desc = float(it.get("desconto") or 0)
        line = qtd * preco * (1 - desc / 100.0)
        total += line + line * (float(it.get("imposto") or 0) / 100.0)
    return round(total, 2)


def save(pedido, *, is_new=False):
    """Inclui ou altera cabeçalho + substitui itens. Retorna pedido completo."""
    p = dict(pedido or {})
    itens = list(p.get("itens") or [])
    p["total"] = _calc_total(itens)
    env = _header_env(p, with_id=not is_new and p.get("id") is not None)
    if is_new or not p.get("id"):
        env["ACAO"] = "incluir"
        if p.get("id") is not None:
            env["ID"] = str(p["id"])
        out, err = cobol_bridge._run("gerir_pedidos_b2b", env)
        pid = None
        for line in (out or "").splitlines():
            line = line.strip()
            if line.isdigit():
                pid = int(line)
                break
            if line.startswith("ERRO:"):
                raise ValueError(line)
        if pid is None:
            raise ValueError("falha ao incluir pedido: " + (out or err or ""))
        p["id"] = pid
    else:
        env["ACAO"] = "alterar"
        env["ID"] = str(p["id"])
        out, err = cobol_bridge._run("gerir_pedidos_b2b", env)
        if "ERRO:" in (out or ""):
            raise ValueError((out or err or "").strip())
    _replace_itens(p["id"], itens)
    sync_json()
    return get(p["id"])


def delete(pedido_id):
    out, _ = cobol_bridge._run(
        "gerir_pedidos_b2b", {"ACAO": "excluir", "ID": str(pedido_id)}
    )
    if "ERRO:" in (out or ""):
        raise ValueError((out or "").strip())
    cobol_bridge._run(
        "gerir_itens_ped_b2b",
        {"ACAO": "limpar", "PEDIDO_ID": str(pedido_id)},
    )
    sync_json()
    return True


def sync_json(pedidos=None):
    """Projeção JSON para consultas/relatórios."""
    rows = pedidos if pedidos is not None else listar()
    payload = {
        "pedidos": rows,
        "total": len(rows),
        "source": "cobol:pedidos_b2b.dat",
        "atualizado_em": _now(),
    }
    os.makedirs(os.path.dirname(JSON_FILE) or ".", exist_ok=True)
    jsonio.save(JSON_FILE, payload)
    return payload


def migrate_json_to_cobol(force=False):
    """Importa pedidos_b2b.json → .dat (uma vez)."""
    if (
        os.path.exists(DAT_HEADER)
        and os.path.getsize(DAT_HEADER) > 0
        and not force
    ):
        return {"migrated": 0, "message": "dat ja existe"}
    if not os.path.exists(JSON_FILE):
        return {"migrated": 0, "message": "sem json"}
    # limpa dats se force
    if force:
        for p in (DAT_HEADER, DAT_ITENS):
            if os.path.exists(p):
                os.remove(p)
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("pedidos") if isinstance(data, dict) else data
    n = 0
    for p in rows or []:
        try:
            env = _header_env(p, with_id=True)
            env["ACAO"] = "incluir"
            env["ID"] = str(p.get("id"))
            out, _ = cobol_bridge._run("gerir_pedidos_b2b", env)
            if "ERRO:" in (out or ""):
                continue
            _replace_itens(p.get("id"), p.get("itens") or [])
            n += 1
        except Exception:
            continue
    sync_json()
    return {"migrated": n, "message": "ok"}
