"""
NF-e XML Monitor (RFC-4003) — ciclo de vida do arquivo XML.

Não interpreta fiscal completo, não cria regra de negócio de estoque.
Recebe → armazena → identifica → processa via nfe_inbound → receiving draft.

MVP: só NF-e modelo 55. Sem scheduler (processamento sob demanda / scan pasta).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import datetime

import nfe_inbound

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
INBOX_DIR = os.path.join(DATA_DIR, "nfe_inbox")
PROCESSED_DIR = os.path.join(INBOX_DIR, "processed")
ERROR_DIR = os.path.join(INBOX_DIR, "error")
REGISTRY_FILE = os.path.join(DATA_DIR, "nfe_monitor.json")

STATUSES = ("new", "processing", "done", "error", "duplicate")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _digits(val):
    return "".join(ch for ch in str(val or "") if ch.isdigit())


def _ensure_dirs():
    for d in (INBOX_DIR, PROCESSED_DIR, ERROR_DIR):
        os.makedirs(d, exist_ok=True)


def _load():
    if not os.path.exists(REGISTRY_FILE):
        return {"next_id": 1, "documents": []}
    with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"next_id": 1, "documents": []}
    if not isinstance(data.get("documents"), list):
        data["documents"] = []
    if not isinstance(data.get("next_id"), int):
        data["next_id"] = 1
    return data


def _save(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _get(data, doc_id):
    for d in data.get("documents") or []:
        if str(d.get("id")) == str(doc_id):
            return d
    return None


def list_documents(status=None, limit=100):
    rows = list(_load().get("documents") or [])
    st = str(status or "").strip().lower()
    if st:
        rows = [d for d in rows if str(d.get("status")) == st]
    rows.sort(key=lambda d: d.get("id") or 0, reverse=True)
    return rows[: max(1, int(limit or 100))]


def get_document(doc_id):
    return _get(_load(), doc_id)


def find_by_chave(chave):
    chave = _digits(chave)
    if not chave:
        return None
    for d in _load().get("documents") or []:
        if _digits(d.get("chave")) == chave:
            return d
    return None


def _identify(raw: bytes):
    """Identificação leve: chave, modelo, emit/dest — via parse já existente."""
    try:
        parsed = nfe_inbound.parse_nfe_xml(raw)
    except ValueError as e:
        return {
            "ok": False,
            "error": str(e),
            "chave": "",
            "modelo": "",
            "tipo": "unknown",
        }
    modelo = str(parsed.get("modelo") or "")
    tipo = "nfe" if modelo == "55" else ("nfce" if modelo == "65" else f"mod{modelo}")
    return {
        "ok": True,
        "error": "",
        "chave": parsed.get("chave") or "",
        "modelo": modelo,
        "tipo": tipo,
        "numero": parsed.get("numero"),
        "serie": parsed.get("serie"),
        "fornecedor_cnpj": parsed.get("fornecedor_cnpj"),
        "fornecedor_nome": parsed.get("fornecedor_nome"),
        "destinatario_cnpj": parsed.get("destinatario_cnpj"),
        "valor_total": parsed.get("valor_total"),
        "xml_sha256": parsed.get("xml_sha256"),
    }


def ingest_xml(xml_text_or_bytes, *, filename=None, source="upload", user_id=None):
    """
    Recebe XML, armazena na inbox, registra status=new (ou error na ID).
    Não cria receiving ainda.
    """
    _ensure_dirs()
    if isinstance(xml_text_or_bytes, str):
        raw = xml_text_or_bytes.encode("utf-8", errors="replace")
    else:
        raw = bytes(xml_text_or_bytes or b"")
    if not raw.strip():
        raise ValueError("XML vazio")

    sha = hashlib.sha256(raw).hexdigest()
    ident = _identify(raw)
    chave = _digits(ident.get("chave"))

    data = _load()
    for d in data.get("documents") or []:
        if chave and _digits(d.get("chave")) == chave and d.get("status") in ("new", "processing", "done"):
            return {
                "document": d,
                "duplicate": True,
                "message": f"XML já no monitor #{d.get('id')} (status={d.get('status')})",
            }
        if d.get("xml_sha256") == sha and d.get("status") in ("new", "processing", "done"):
            return {
                "document": d,
                "duplicate": True,
                "message": f"mesmo arquivo já no monitor #{d.get('id')}",
            }

    doc_id = int(data.get("next_id") or 1)
    safe_name = (filename or f"{chave or sha[:16]}.xml").replace("/", "_").replace("\\", "_")
    if not safe_name.lower().endswith(".xml"):
        safe_name += ".xml"
    stored_name = f"{doc_id:05d}_{safe_name}"
    path = os.path.join(INBOX_DIR, stored_name)
    with open(path, "wb") as f:
        f.write(raw)

    status = "new"
    error = ""
    if not ident.get("ok"):
        status = "error"
        error = ident.get("error") or "XML ilegível"
        err_path = os.path.join(ERROR_DIR, stored_name)
        shutil.move(path, err_path)
        path = err_path
    elif ident.get("modelo") == "65":
        status = "error"
        error = "NFC-e (65) ignorada no monitor de entrada — use NF-e 55"
    elif ident.get("modelo") and ident.get("modelo") not in ("55", ""):
        status = "error"
        error = f"modelo {ident.get('modelo')} não suportado no MVP"

    doc = {
        "id": doc_id,
        "status": status,
        "tipo": ident.get("tipo") or "unknown",
        "modelo": ident.get("modelo") or "",
        "chave": chave,
        "numero": ident.get("numero"),
        "serie": ident.get("serie"),
        "fornecedor_cnpj": ident.get("fornecedor_cnpj") or "",
        "fornecedor_nome": ident.get("fornecedor_nome") or "",
        "destinatario_cnpj": ident.get("destinatario_cnpj") or "",
        "valor_total": ident.get("valor_total"),
        "xml_sha256": sha,
        "filename": safe_name,
        "path": path,
        "source": source,
        "error": error,
        "receiving_id": None,
        "attempts": 0,
        "created_at": _now(),
        "created_by": user_id,
        "processed_at": None,
        "events": [
            {"at": _now(), "tipo": "received", "by": user_id, "source": source},
        ],
    }
    if status == "error":
        doc["events"].append({"at": _now(), "tipo": "error", "detail": error})

    data["documents"].append(doc)
    data["next_id"] = doc_id + 1
    _save(data)
    if status in ("error",):
        try:
            import receiving_pending
            receiving_pending.sync_from_monitor_doc(doc, user_id=user_id)
        except Exception:
            pass
    return {"document": doc, "duplicate": False, "message": "ok"}


def scan_inbox(user_id=None):
    """Varre data/nfe_inbox/*.xml soltos e registra no monitor."""
    _ensure_dirs()
    created = []
    skipped = []
    for name in sorted(os.listdir(INBOX_DIR)):
        if not name.lower().endswith(".xml"):
            continue
        path = os.path.join(INBOX_DIR, name)
        if not os.path.isfile(path):
            continue
        if len(name) > 6 and name[:5].isdigit() and name[5] == "_":
            continue
        with open(path, "rb") as f:
            raw = f.read()
        result = ingest_xml(raw, filename=name, source="inbox_scan", user_id=user_id)
        if result.get("duplicate"):
            skipped.append({"filename": name, "message": result.get("message")})
        else:
            created.append(result["document"])
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass
    return {"created": created, "skipped": skipped, "total_created": len(created)}


def process_document(doc_id, *, estabelecimento_id=None, user_id=None):
    """
    Processa documento new → nfe_inbound → receiving draft.
    Status final: done | duplicate | error.
    """
    data = _load()
    doc = _get(data, doc_id)
    if not doc:
        raise ValueError("documento não encontrado no monitor")
    if doc.get("status") == "done":
        return doc
    if doc.get("status") == "processing":
        raise ValueError("documento já em processamento")
    if doc.get("status") == "duplicate":
        return doc

    path = doc.get("path") or ""
    if not path or not os.path.exists(path):
        doc["status"] = "error"
        doc["error"] = "arquivo XML ausente"
        doc.setdefault("events", []).append({"at": _now(), "tipo": "error", "detail": doc["error"]})
        _save(data)
        raise ValueError(doc["error"])

    doc["status"] = "processing"
    doc["attempts"] = int(doc.get("attempts") or 0) + 1
    doc.setdefault("events", []).append({"at": _now(), "tipo": "processing", "by": user_id})
    _save(data)

    try:
        with open(path, "rb") as f:
            raw = f.read()
        rec = nfe_inbound.create_receiving_from_nfe(
            raw,
            estabelecimento_id=estabelecimento_id,
            user_id=user_id,
        )
    except ValueError as e:
        msg = str(e)
        data = _load()
        doc = _get(data, doc_id)
        if "já importada" in msg.lower():
            doc["status"] = "duplicate"
            doc["error"] = msg
            m = re.search(r"#(\d+)", msg)
            if m:
                doc["receiving_id"] = int(m.group(1))
        else:
            doc["status"] = "error"
            doc["error"] = msg
            try:
                if os.path.dirname(path) == INBOX_DIR:
                    dest = os.path.join(ERROR_DIR, os.path.basename(path))
                    shutil.move(path, dest)
                    doc["path"] = dest
            except OSError:
                pass
        doc["processed_at"] = _now()
        doc.setdefault("events", []).append({
            "at": _now(), "tipo": doc["status"], "by": user_id, "detail": msg,
        })
        _save(data)
        try:
            import receiving_pending
            receiving_pending.sync_from_monitor_doc(doc, user_id=user_id)
        except Exception:
            pass
        if doc["status"] == "duplicate":
            return doc
        raise ValueError(msg) from e
    except Exception as e:
        data = _load()
        doc = _get(data, doc_id)
        doc["status"] = "error"
        doc["error"] = f"falha: {e}"
        doc["processed_at"] = _now()
        doc.setdefault("events", []).append({
            "at": _now(), "tipo": "error", "by": user_id, "detail": str(e),
        })
        _save(data)
        try:
            import receiving_pending
            receiving_pending.sync_from_monitor_doc(doc, user_id=user_id)
        except Exception:
            pass
        raise

    data = _load()
    doc = _get(data, doc_id)
    doc["status"] = "done"
    doc["error"] = ""
    doc["receiving_id"] = rec.get("id")
    doc["processed_at"] = _now()
    doc.setdefault("events", []).append({
        "at": _now(), "tipo": "done", "by": user_id, "receiving_id": rec.get("id"),
    })
    try:
        if os.path.exists(path) and os.path.dirname(path) == INBOX_DIR:
            dest = os.path.join(PROCESSED_DIR, os.path.basename(path))
            shutil.move(path, dest)
            doc["path"] = dest
    except OSError:
        pass
    _save(data)
    try:
        import receiving_pending
        receiving_pending.sync_from_monitor_doc(doc, user_id=user_id)
    except Exception:
        pass
    doc["_receiving"] = rec
    return doc


def process_pending(*, estabelecimento_id=None, user_id=None, limit=20):
    """Processa documentos status=new (NF-e 55)."""
    rows = [d for d in list_documents(status="new", limit=500) if d.get("modelo") in ("55", "")]
    out = {"ok": [], "errors": []}
    for d in rows[: max(1, int(limit or 20))]:
        try:
            doc = process_document(d["id"], estabelecimento_id=estabelecimento_id, user_id=user_id)
            out["ok"].append({
                "id": doc["id"],
                "receiving_id": doc.get("receiving_id"),
                "status": doc.get("status"),
            })
        except ValueError as e:
            out["errors"].append({"id": d["id"], "message": str(e)})
    return out


def retry_document(doc_id, *, estabelecimento_id=None, user_id=None):
    """Reprocessa documento em error (volta para new logic via process direto)."""
    data = _load()
    doc = _get(data, doc_id)
    if not doc:
        raise ValueError("documento não encontrado")
    if doc.get("status") not in ("error", "new"):
        raise ValueError(f"não reprocessa status={doc.get('status')}")
    if doc.get("status") == "error":
        doc["status"] = "new"
        doc["error"] = ""
        # se estava em error/, move de volta à inbox
        path = doc.get("path") or ""
        if path and os.path.exists(path) and os.path.dirname(path) == ERROR_DIR:
            dest = os.path.join(INBOX_DIR, os.path.basename(path))
            try:
                shutil.move(path, dest)
                doc["path"] = dest
            except OSError:
                pass
        doc.setdefault("events", []).append({"at": _now(), "tipo": "retry", "by": user_id})
        _save(data)
    return process_document(doc_id, estabelecimento_id=estabelecimento_id, user_id=user_id)
