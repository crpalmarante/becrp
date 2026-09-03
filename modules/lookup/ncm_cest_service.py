#!/usr/bin/env python3
"""Lookup Engine — NCM / CEST (RFC 0012 + 0013 Sprint 1)"""

from __future__ import annotations

import json
import os
import re
from datetime import date
from functools import lru_cache
from typing import Any

# modules/lookup/ncm_cest_service.py → raiz do projeto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DADOS = os.path.join(BASE_DIR, "dados")


def _load(name: str):
    path = os.path.join(DADOS, name)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        for key in ("items", "ncm", "cest", "ncm_cest", "relacionamentos", "Nomenclaturas"):
            if key in data and isinstance(data[key], list):
                return data[key]
        return []
    return data if isinstance(data, list) else []


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


def _parse_br_date(s: str) -> str:
    """DD/MM/YYYY → YYYY-MM-DD; ISO passa direto."""
    s = (s or "").strip()
    if not s:
        return "1900-01-01"
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return s[:10]


def _load_ncm_tabela_rows():
    """Lê a tabela NCM oficial (Camex / Gecex).

    Fonte primária: dados/Tabela_NCM.json
    Fallback: dados/Tabela_NCM.csv (gerado por scripts/gerar_tabela_ncm_csv.py)
    """
    path = os.path.join(DADOS, "Tabela_NCM.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        rows = data.get("Nomenclaturas") or []
        if rows:
            return [
                {
                    "Codigo": r.get("Codigo", ""),
                    "Descricao": r.get("Descricao", ""),
                    "Data_Inicio": r.get("Data_Inicio", ""),
                    "Data_Fim": r.get("Data_Fim", ""),
                }
                for r in rows
            ]

    csv_path = os.path.join(DADOS, "Tabela_NCM.csv")
    if os.path.exists(csv_path):
        import csv as _csv

        rows = []
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = _csv.DictReader(f, delimiter=";")
            for r in reader:
                rows.append({
                    "Codigo": r.get("codigo", ""),
                    "Descricao": r.get("descricao", ""),
                    "Data_Inicio": r.get("vigencia_inicio", ""),
                    "Data_Fim": r.get("vigencia_fim", ""),
                })
        if rows:
            return rows

    return []


def _build_ncm_from_tabela() -> list:
    """
    Fonte oficial: dados/Tabela_NCM.json (Camex / Gecex), com
    fallback para dados/Tabela_NCM.csv. Expõe apenas códigos de 8 dígitos
    (item NCM do produto), com descrição hierárquica para o autocomplete
    achar por capítulo/posição.
    """
    rows = _load_ncm_tabela_rows()
    by_code: dict[str, dict] = {}
    for r in rows:
        code = _digits(r.get("Codigo", ""))
        if not code:
            continue
        by_code[code] = {
            "codigo": code,
            "descricao_curta": _strip_html(r.get("Descricao", "")),
            "vigencia_inicio": _parse_br_date(r.get("Data_Inicio", "")),
            "vigencia_fim": _parse_br_date(r.get("Data_Fim", "") or "31/12/9999"),
            "ativo": True,
        }

    def chain_desc(code: str) -> str:
        parts = []
        for i in range(2, len(code) + 1):
            node = by_code.get(code[:i])
            if not node:
                continue
            d = node["descricao_curta"]
            if d and (not parts or parts[-1] != d):
                parts.append(d)
        return " › ".join(parts) if parts else ""

    out = []
    for code, row in by_code.items():
        if len(code) != 8:
            continue
        item_desc = row["descricao_curta"].lstrip("-").strip()
        full = item_desc or chain_desc(code) or row["descricao_curta"]
        out.append({
            "id": code,
            "codigo": code,
            "descricao": full,
            "descricao_curta": item_desc,
            "capitulo": code[:2],
            "posicao": code[:4],
            "subposicao": code[:6],
            "item": code,
            "vigencia_inicio": row["vigencia_inicio"],
            "vigencia_fim": row["vigencia_fim"],
            "ativo": True,
        })
    out.sort(key=lambda x: x["codigo"])
    return out


@lru_cache(maxsize=1)
def _ncm_table():
    tabela = _build_ncm_from_tabela()
    if tabela:
        return tabela
    return _load("ncm.json")


@lru_cache(maxsize=1)
def _cest_table():
    return _load("cest.json")


@lru_cache(maxsize=1)
def _ncm_cest_table():
    return _load("ncm_cest.json")


def reload_cache():
    _ncm_table.cache_clear()
    _cest_table.cache_clear()
    _ncm_cest_table.cache_clear()


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _norm(s: str) -> str:
    return (s or "").lower().strip()


def _vigente(row: dict, ref: date | None = None) -> bool:
    if row.get("ativo") is False:
        return False
    ref = ref or date.today()
    ini = row.get("vigencia_inicio") or "1900-01-01"
    fim = row.get("vigencia_fim") or "9999-12-31"
    try:
        d0 = date.fromisoformat(str(ini)[:10])
        d1 = date.fromisoformat(str(fim)[:10])
    except ValueError:
        return True
    return d0 <= ref <= d1


def _rank(item: dict, q: str, code_key: str = "codigo") -> int:
    code = _digits(item.get(code_key, ""))
    desc = _norm(item.get("descricao", ""))
    qd = _digits(q)
    ql = _norm(q)
    if qd and code == qd:
        return 0
    if qd and code.startswith(qd):
        return 1
    if ql and desc.startswith(ql):
        return 2
    if ql and re.search(r"\b" + re.escape(ql) + r"\b", desc):
        return 3
    if ql and ql in desc:
        return 4
    if qd and qd in code:
        return 5
    return 99


def _search_table(table: list, text: str, limit: int = 20) -> list:
    q = (text or "").strip()
    if not q:
        return []
    scored = []
    for row in table:
        if not _vigente(row):
            continue
        r = _rank(row, q)
        if r < 99:
            scored.append((r, row))
    scored.sort(key=lambda x: (x[0], x[1].get("codigo", "")))
    out = []
    for _, row in scored[:limit]:
        desc = re.sub(r"<[^>]+>", "", row.get("descricao") or "")
        desc = desc.replace("›", " ").replace("- ", "")
        desc = re.sub(r"\s+", " ", desc).strip()
        if desc.startswith("- "):
            desc = desc[2:].strip()
        out.append({
            "id": row.get("id") or row.get("codigo"),
            "codigo": row.get("codigo"),
            "descricao": desc,
            "label": f"{row.get('codigo')} — {desc}",
            "segmento": row.get("segmento"),
        })
    return out


def search_ncm(text: str, limit: int = 20) -> list:
    base = _search_table(_ncm_table(), text, limit)
    if len(base) >= limit:
        return base
    # Complemento: aliases vindos do relacionamento NCM↔CEST (descrições comerciais)
    qd, ql = _digits(text), _norm(text)
    if not ql and not qd:
        return base
    seen = {_digits(i["codigo"]) for i in base}
    extra = []
    for rel in _ncm_cest_table():
        if not _vigente(rel):
            continue
        desc = _norm(rel.get("descricao_aplicacao", ""))
        ncm = _digits(rel.get("ncm", rel.get("ncm_codigo", "")))
        if not ncm or ncm in seen:
            continue
        if (ql and ql in desc) or (qd and qd in ncm):
            item = get_ncm(ncm)
            if item:
                item["descricao"] = rel.get("descricao_aplicacao") or item["descricao"]
                item["label"] = f"{item['codigo']} — {item['descricao']}"
                extra.append(item)
                seen.add(ncm)
        if len(base) + len(extra) >= limit:
            break
    return (base + extra)[:limit]


def search_cest(text: str, limit: int = 20, ncm: str | None = None) -> list:
    if ncm:
        related = list_cest_for_ncm(ncm)
        if related:
            q = (text or "").strip()
            if not q:
                return related
            qd, ql = _digits(q), _norm(q)
            return [
                r for r in related
                if qd in _digits(r["codigo"]) or ql in _norm(r["descricao"])
            ][:limit]
    return _search_table(_cest_table(), text, limit)


def get_ncm(code: str) -> dict | None:
    code = _digits(code)
    for row in _ncm_table():
        if _digits(row.get("codigo", "")) == code and _vigente(row):
            desc = re.sub(r"<[^>]+>", "", row.get("descricao") or "")
            desc = desc.replace("›", " ").replace("- ", "")
            desc = re.sub(r"\s+", " ", desc).strip()
            if desc.startswith("- "):
                desc = desc[2:].strip()
            return {
                "id": row.get("id") or row.get("codigo"),
                "codigo": row.get("codigo"),
                "descricao": desc,
                "label": f"{row.get('codigo')} — {desc}",
            }
    return None


def get_cest(code: str) -> dict | None:
    code = _digits(code)
    for row in _cest_table():
        if _digits(row.get("codigo", "")) == code and _vigente(row):
            return {
                "id": row.get("id") or row.get("codigo"),
                "codigo": row.get("codigo"),
                "descricao": row.get("descricao") or "",
                "label": f"{row.get('codigo')} — {row.get('descricao') or ''}",
                "segmento": row.get("segmento"),
            }
    return None


def list_cest_for_ncm(ncm_code: str) -> list:
    ncm_code = _digits(ncm_code)
    cest_by_code = {_digits(c.get("codigo", "")): c for c in _cest_table() if _vigente(c)}
    out = []
    seen = set()
    for rel in _ncm_cest_table():
        if not _vigente(rel):
            continue
        if _digits(rel.get("ncm", rel.get("ncm_codigo", ""))) != ncm_code:
            continue
        cc = _digits(rel.get("cest", rel.get("cest_codigo", "")))
        if not cc or cc in seen:
            continue
        seen.add(cc)
        base = cest_by_code.get(cc) or {"codigo": cc, "descricao": rel.get("descricao_aplicacao", "")}
        out.append({
            "id": base.get("id") or cc,
            "codigo": base.get("codigo") or cc,
            "descricao": re.sub(r"<[^>]+>", "", base.get("descricao") or rel.get("descricao_aplicacao") or ""),
            "label": f"{base.get('codigo') or cc} — {re.sub(r'<[^>]+>', '', base.get('descricao') or '')}",
            "obrigatorio": bool(rel.get("obrigatorio") or rel.get("st_obrigatorio")),
            "fundamento_legal": rel.get("fundamento_legal", ""),
        })
    return out


def resolve_cest_autofill(ncm_code: str) -> dict[str, Any]:
    """RFC: 0 → vazio; 1 → autofill; N → escolha."""
    rels = list_cest_for_ncm(ncm_code)
    if not rels:
        return {"status": "none", "cest": None, "opcoes": [], "mensagem": "Produto sem CEST."}
    if len(rels) == 1:
        return {"status": "single", "cest": rels[0], "opcoes": rels, "mensagem": "CEST preenchido automaticamente."}
    return {"status": "multiple", "cest": None, "opcoes": rels, "mensagem": "Escolha o CEST aplicável."}


def validate_ncm_cest(ncm_code: str, cest_code: str) -> dict:
    ncm = get_ncm(ncm_code)
    if not ncm:
        return {"ok": False, "message": "NCM inválido ou não vigente (RN-001/RN-002)."}
    if not cest_code or not _digits(cest_code):
        return {"ok": True, "message": "Produto sem CEST.", "ncm": ncm, "cest": None}
    cest = get_cest(cest_code)
    if not cest:
        return {"ok": False, "message": "CEST inválido ou não vigente (RN-003)."}
    allowed = {_digits(r["codigo"]) for r in list_cest_for_ncm(ncm_code)}
    if _digits(cest_code) not in allowed:
        return {"ok": False, "message": "CEST incompatível com o NCM (RN-008)."}
    return {"ok": True, "message": "Relacionamento válido.", "ncm": ncm, "cest": cest}
