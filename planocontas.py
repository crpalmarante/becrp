"""
Plano de contas do sistema.

Fonte: dados/planocontas.json (importado do Plano Referencial.xls local).
A planilha .xls não é versionada — só o JSON operacional.
"""

from __future__ import annotations

import json
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "planocontas.json")
XLS_CANDIDATES = (
    os.path.join(BASE_DIR, "Plano Referencial.xls"),
    os.path.join(BASE_DIR, "Plano Referencial.xlsx"),
)

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load_raw():
    if not os.path.exists(DATA_FILE):
        return {"fonte": "", "importado_em": None, "total": 0, "contas": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"fonte": "", "importado_em": None, "total": 0, "contas": []}
    if not isinstance(data.get("contas"), list):
        data["contas"] = []
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["total"] = len(data.get("contas") or [])
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def list_contas(q=None, tipo=None, analiticas=None, limit=500):
    rows = list(_load_raw().get("contas") or [])
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            c
            for c in rows
            if qq in str(c.get("codigo") or "").lower()
            or qq in str(c.get("classificacao") or "").lower()
            or qq in str(c.get("nome") or "").lower()
            or qq in str(c.get("descricao") or "").lower()
        ]
    if tipo:
        t = str(tipo).strip().upper()
        rows = [c for c in rows if str(c.get("tipo") or "").upper() == t]
    if analiticas is True:
        rows = [c for c in rows if str(c.get("tipo") or "").upper() == "A"]
    elif analiticas is False:
        rows = [c for c in rows if str(c.get("tipo") or "").upper() == "S"]
    try:
        lim = max(1, min(int(limit or 500), 5000))
    except (TypeError, ValueError):
        lim = 500
    meta = _load_raw()
    return {
        "fonte": meta.get("fonte") or "",
        "importado_em": meta.get("importado_em"),
        "total": len(meta.get("contas") or []),
        "filtrado": len(rows),
        "contas": rows[:lim],
    }


def get_conta(codigo_or_classif):
    key = str(codigo_or_classif or "").strip()
    if not key:
        return None
    for c in _load_raw().get("contas") or []:
        if str(c.get("codigo")) == key or str(c.get("classificacao")) == key:
            return c
    return None


def meta():
    data = _load_raw()
    return {
        "fonte": data.get("fonte") or "",
        "importado_em": data.get("importado_em"),
        "total": len(data.get("contas") or []),
        "arquivo_xls": next((p for p in XLS_CANDIDATES if os.path.exists(p)), None),
    }


def _col_to_idx(col):
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch.upper()) - 64)
    return n - 1


def _excel_serial_to_date(serial):
    try:
        n = int(float(serial))
    except (TypeError, ValueError):
        return None
    return (datetime(1899, 12, 30) + timedelta(days=n)).date().isoformat()


def _cell_val(c, strings):
    t = c.get("t")
    v = c.find("m:v", NS)
    if v is None or v.text is None:
        return None
    if t == "s":
        return strings[int(v.text)]
    return v.text


def import_from_xls(path=None):
    """Lê Plano Referencial.xls (Office Open XML) e grava dados/planocontas.json."""
    src = path
    if not src:
        src = next((p for p in XLS_CANDIDATES if os.path.exists(p)), None)
    if not src or not os.path.exists(src):
        raise FileNotFoundError(
            "Plano Referencial.xls não encontrado na raiz do projeto (arquivo local, não versionado)"
        )

    with zipfile.ZipFile(src) as z:
        strings = []
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si", NS):
            texts = [
                t.text or ""
                for t in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
            ]
            strings.append("".join(texts))
        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))

    rows = {}
    max_col = 0
    for row in sheet.findall("m:sheetData/m:row", NS):
        ridx = int(row.get("r"))
        vals = {}
        for c in row.findall("m:c", NS):
            ref = c.get("r") or ""
            m = re.match(r"([A-Z]+)(\d+)", ref)
            if not m:
                continue
            ci = _col_to_idx(m.group(1))
            max_col = max(max_col, ci)
            vals[ci] = _cell_val(c, strings)
        rows[ridx] = vals

    contas = []
    for ridx in sorted(k for k in rows if k > 1):
        v = rows[ridx]
        codigo = str(v.get(0) or "").strip()
        desc = str(v.get(1) or "").strip()
        d_ini = v.get(2)
        d_fim = v.get(3)
        sa = str(v.get(4) or "").strip()
        classif = str(v.get(5) or "").strip()
        if not codigo and not classif:
            continue
        nome = desc
        if classif and desc.startswith(classif):
            nome = desc[len(classif) :].strip()
        elif "    " in desc:
            nome = desc.split("    ", 1)[-1].strip()
        hierarquia = [p for p in classif.split(".") if p] if classif else [codigo]
        tipo = "S" if sa in ("1", "S", "s") else "A" if sa in ("2", "A", "a") else (sa or "")
        contas.append(
            {
                "codigo": codigo,
                "descricao": desc,
                "nome": nome,
                "classificacao": classif or codigo,
                "nivel": len(hierarquia),
                "hierarquia": hierarquia,
                "tipo": tipo,
                "valido_de": _excel_serial_to_date(d_ini),
                "valido_ate": _excel_serial_to_date(d_fim),
                "origem": os.path.basename(src),
            }
        )

    if not contas:
        raise ValueError("nenhuma conta lida da planilha")

    data = {
        "fonte": os.path.basename(src),
        "importado_em": _now(),
        "total": len(contas),
        "contas": contas,
    }
    _save(data)
    return meta()
