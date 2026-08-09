"""
RFC-0000 — Platform Installation & Initial Configuration (MVP).

Camada nova: orquestra instalação do zero + Business Setup.
Não reescreve o legado. Reusa: users, org_store, app_registry.

Estado: data/platform_setup.json (pausável / retomável).
"""

from __future__ import annotations

import glob
import json
import os
import re
import shutil
from datetime import datetime

import app_registry
import org_store

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "platform_setup.json")
USERS_FILE = os.path.join(BASE_DIR, "data", "users.json")
WAREHOUSE_FILE = os.path.join(BASE_DIR, "data", "warehouses_setup.json")
PARAMS_FILE = os.path.join(BASE_DIR, "data", "parametros.json")
LOG_DIR = os.path.join(BASE_DIR, "data", "logs")
LOG_FILE = os.path.join(LOG_DIR, "system_log.json")
BACKUP_ROOT = os.path.join(BASE_DIR, "data", "backups")
BACKUP_INDEX = os.path.join(BACKUP_ROOT, "_index.json")

# RFC-0000 §21 — Lifecycle: arquivos cobertos por backup/restore
_BACKUP_ROOTS = (
    (os.path.join(BASE_DIR, "data"), "data", ("*.json",)),
    (os.path.join(BASE_DIR, "dados"), "dados", ("*.json",)),
)
_AUTH_DB = os.path.join(BASE_DIR, "dados", "auth.db")

# RFC-0000 §9 — default parameters registrados na inicialização
DEFAULT_PARAMETERS = {
    "version": 1,
    "system": {
        "page_size": 50,
        "session_timeout_segundos": 300,
        "idioma_padrao": "pt-BR",
    },
    "ui": {
        "date_format": "DD/MM/AAAA",
        "decimal_separator": ",",
        "thousands_separator": ".",
        "currency_position": "before",
    },
    "negocio": {
        "inventory_precision": 2,
        "price_precision": 2,
        "fiscal_regime": "",
    },
}

FACTORY_CONFIRM = "REINSTALAR"

# Business Setup (após software + admin + first login)
STEPS = [
    "localization",
    "organization",
    "company",
    "users",
    "modules",
    "validation",
    "go_live",
]

STEP_LABELS = {
    "localization": "Localização",
    "organization": "Organização",
    "company": "Empresa / Estrutura",
    "users": "Usuários",
    "modules": "Módulos / Pacotes",
    "validation": "Validação",
    "go_live": "Produção",
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _slug(name):
    s = str(name or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return (s[:48] or "instance")


def _load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _save_users(users):
    os.makedirs(os.path.dirname(USERS_FILE) or ".", exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users if isinstance(users, dict) else {}, f, indent=2, ensure_ascii=False)


def _has_admin():
    return any(u.get("role") == "admin" for u in _load_users().values())


def _org_configured():
    org = org_store.load_organizacao()
    nome = (org.get("nome") or "").strip()
    # default legado "Organização" não conta como configurado
    if not nome or nome.lower() in ("organização", "organizacao", "organization"):
        return False
    return True


def _legacy_configured():
    """Instância já operacional (legado) — não forçar wizard."""
    if not _has_admin():
        return False
    if not _org_configured():
        return False
    if not org_store.load_empresas():
        return False
    return True


def _load_warehouses():
    if not os.path.exists(WAREHOUSE_FILE):
        return {"warehouses": []}
    with open(WAREHOUSE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"warehouses": []}
    data.setdefault("warehouses", [])
    return data


def _save_warehouses(data):
    os.makedirs(os.path.dirname(WAREHOUSE_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    with open(WAREHOUSE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _fresh():
    return {
        "version": 1,
        "phase": "empty",  # empty | initialized | business_setup | operational
        "instance": {
            "name": "",
            "identifier": "",
            "description": "",
        },
        "localization": {
            "country": "BR",
            "language": "pt-BR",
            "timezone": "America/Sao_Paulo",
            "currency": "BRL",
        },
        "structure": {
            "branch_name": "",
            "warehouse_name": "",
            "warehouse_postponed": True,
        },
        "init_progress": [],
        "steps_done": {},
        "current_step": "localization",
        "go_live": False,
        "compat_legacy": False,
        "maintenance": False,
        "archived": False,
        "atualizado_em": _now(),
    }


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_state():
    if not os.path.exists(DATA_FILE):
        if _legacy_configured():
            data = _fresh()
            data["compat_legacy"] = True
            data["go_live"] = True
            data["phase"] = "operational"
            data["current_step"] = "go_live"
            for s in STEPS:
                data["steps_done"][s] = True
            org = org_store.load_organizacao()
            data["instance"]["name"] = org.get("nome") or "Business Instance"
            data["instance"]["identifier"] = _slug(org.get("id") or org.get("nome") or "org")
            _save(data)
            return data
        data = _fresh()
        _save(data)
        return data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        data = _fresh()
        _save(data)
    data.setdefault("steps_done", {})
    data.setdefault("localization", _fresh()["localization"])
    data.setdefault("instance", _fresh()["instance"])
    data.setdefault("structure", _fresh()["structure"])
    data.setdefault("init_progress", [])
    data.setdefault("phase", "empty")
    data.setdefault("go_live", False)
    data.setdefault("current_step", "localization")
    # passo antigo removido → ajusta
    if data.get("current_step") not in STEPS:
        data["current_step"] = "localization"
    return data


def register_default_parameters(overwrite=False):
    """RFC-0000 §9 — registra parâmetros default da Business Instance."""
    if os.path.exists(PARAMS_FILE) and not overwrite:
        with open(PARAMS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    data = json.loads(json.dumps(DEFAULT_PARAMETERS))
    data["atualizado_em"] = _now()
    os.makedirs(os.path.dirname(PARAMS_FILE) or ".", exist_ok=True)
    with open(PARAMS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


def load_parameters():
    if not os.path.exists(PARAMS_FILE):
        return register_default_parameters()
    with open(PARAMS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return register_default_parameters(overwrite=True)
    return data


def init_logging():
    """RFC-0000 §9 — inicializa o Logging Services da Business Instance."""
    os.makedirs(LOG_DIR, exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump({"events": [], "atualizado_em": _now()}, f, indent=2, ensure_ascii=False)
    return True


def load_log(limit=100):
    """Últimos eventos do System Log (RFC-0000 §9)."""
    init_logging()
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            log = json.load(f)
    except Exception:
        return {"events": []}
    events = (log.get("events") or []) if isinstance(log, dict) else []
    try:
        n = int(limit)
    except (TypeError, ValueError):
        n = 100
    return {"events": events[-max(0, n):]}


def log_event(dominio, acao, usuario="", detalhe="", data=None):
    """Registrar evento no System Log (append-only, com teto de tamanho)."""
    init_logging()
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            log = json.load(f)
    except Exception:
        log = {"events": []}
    if not isinstance(log, dict):
        log = {"events": []}
    log.setdefault("events", [])
    log["events"].append({
        "em": _now(),
        "dominio": str(dominio or "").strip(),
        "acao": str(acao or "").strip(),
        "usuario": str(usuario or "").strip(),
        "detalhe": str(detalhe or "").strip(),
        "data": data if isinstance(data, dict) else {},
    })
    log["events"] = log["events"][-5000:]  # teto para arquivo não crescer sem limite
    log["atualizado_em"] = _now()
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    return True


# --- RFC-0000 §21 — Business Instance Lifecycle ----------------------------

_LIFECYCLE_ALLOWED = (
    "/api/system/",
    "/api/auth/login", "/api/auth/me", "/api/auth/logout", "/api/auth/minhas-empresas",
    "/api/platform/setup",
)


def lifecycle_guard(path):
    """RFC-0000 §21 — bloqueia escritas fora de manutenção/arquivamento."""
    p = str(path or "").rstrip("/") or "/"
    if p.startswith(_LIFECYCLE_ALLOWED):
        return ""
    state = load_state()
    if state.get("archived"):
        return "Instância arquivada — operações bloqueadas"
    if state.get("maintenance"):
        return "Plataforma em manutenção — operações temporariamente bloqueadas"
    return ""


def enter_maintenance(usuario=""):
    state = load_state()
    if not state.get("go_live"):
        raise ValueError("instância ainda não está em produção")
    state["maintenance"] = True
    state["maintenance_em"] = _now()
    state["maintenance_by"] = str(usuario or "").strip()
    _save(state)
    log_event("platform", "maintenance", usuario=usuario, detalhe="entrou em manutenção")
    return status()


def exit_maintenance(usuario=""):
    state = load_state()
    state["maintenance"] = False
    state["maintenance_exit_em"] = _now()
    state["maintenance_exit_by"] = str(usuario or "").strip()
    _save(state)
    log_event("platform", "maintenance", usuario=usuario, detalhe="saiu da manutenção")
    return status()


def archive_instance(usuario=""):
    state = load_state()
    state["archived"] = True
    state["archived_em"] = _now()
    state["archived_by"] = str(usuario or "").strip()
    _save(state)
    log_event("platform", "archive", usuario=usuario, detalhe="instância arquivada")
    return status()


def unarchive_instance(usuario=""):
    state = load_state()
    state["archived"] = False
    state["unarchived_em"] = _now()
    state["unarchived_by"] = str(usuario or "").strip()
    _save(state)
    log_event("platform", "archive", usuario=usuario, detalhe="instância reativada")
    return status()


def _backup_files():
    files = []
    for root_dir, label, pats in _BACKUP_ROOTS:
        for pat in pats:
            for fn in glob.glob(os.path.join(root_dir, pat)):
                files.append((root_dir, label, os.path.basename(fn)))
    if os.path.exists(_AUTH_DB):
        files.append((os.path.dirname(_AUTH_DB), "dados", os.path.basename(_AUTH_DB)))
    return files


def _load_backup_index():
    if not os.path.exists(BACKUP_INDEX):
        return {"version": 1, "backups": []}
    try:
        with open(BACKUP_INDEX, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"version": 1, "backups": []}
    if not isinstance(data, dict):
        data = {"version": 1, "backups": []}
    data.setdefault("backups", [])
    return data


def _save_backup_index(data):
    os.makedirs(BACKUP_ROOT, exist_ok=True)
    data["atualizado_em"] = _now()
    with open(BACKUP_INDEX, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def list_backups():
    idx = _load_backup_index()
    return sorted(idx["backups"], key=lambda b: b.get("criado_em", ""), reverse=True)


def create_backup(usuario=""):
    bid = "backup_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(BACKUP_ROOT, bid)
    os.makedirs(dest, exist_ok=True)
    copied = 0
    total = 0
    for root, label, fn in _backup_files():
        src = os.path.join(root, fn)
        d = os.path.join(dest, label)
        os.makedirs(d, exist_ok=True)
        shutil.copy2(src, os.path.join(d, fn))
        copied += 1
        total += os.path.getsize(src)
    idx = _load_backup_index()
    idx["backups"].append({
        "id": bid,
        "criado_em": _now(),
        "by": str(usuario or "").strip(),
        "files": copied,
        "size": total,
    })
    _save_backup_index(idx)
    log_event("platform", "backup", usuario=usuario, detalhe=f"{bid} · {copied} arquivos")
    return {"backup_id": bid, "files": copied, "size": total}


def restore_backup(backup_id, usuario=""):
    bid = str(backup_id or "").strip()
    src = os.path.join(BACKUP_ROOT, bid)
    if not os.path.isdir(src):
        raise ValueError("backup não encontrado")
    restored = 0
    for root, label, fn in _backup_files():
        b = os.path.join(src, label, fn)
        if os.path.exists(b):
            shutil.copy2(b, os.path.join(root, fn))
            restored += 1
    log_event("platform", "restore", usuario=usuario, detalhe=f"{bid} · {restored} arquivos")
    return {"backup_id": bid, "files": restored}


def run_initialization(state=None):
    """
    RFC-0000 §9 — inicializa repositórios da Business Instance.
    Retorna lista de progresso para a UI.
    """
    state = state if isinstance(state, dict) else load_state()
    progress = []

    def tick(item_id, label, ok=True, detail=""):
        progress.append({
            "id": item_id,
            "label": label,
            "ok": bool(ok),
            "detail": detail,
            "em": _now(),
        })

    # Repository
    try:
        os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
        os.makedirs(os.path.join(BASE_DIR, "dados"), exist_ok=True)
        tick("repository", "Repositório", True)
    except Exception as e:
        tick("repository", "Repositório", False, str(e))

    # Configuration
    try:
        _save(state)
        tick("configuration", "Configuração", True)
    except Exception as e:
        tick("configuration", "Configuração", False, str(e))

    # Administrator
    tick("administrator", "Administrador", _has_admin())

    # Localization
    loc = state.get("localization") or {}
    tick(
        "localization",
        "Localização",
        bool(loc.get("country") and loc.get("currency")),
        f"{loc.get('country')}/{loc.get('currency')}",
    )

    # Services / module registry
    try:
        app_registry.init_base()
        tick("services", "Serviços / Registry", True)
    except Exception as e:
        tick("services", "Serviços / Registry", False, str(e))

    # Analytics placeholder
    analytics = os.path.join(BASE_DIR, "data", "analytics_store.json")
    try:
        if not os.path.exists(analytics):
            with open(analytics, "w", encoding="utf-8") as f:
                json.dump({"initialized": True, "em": _now()}, f)
        tick("analytics", "Analytics", True)
    except Exception as e:
        tick("analytics", "Analytics", False, str(e))

    # Documents
    docs = os.path.join(BASE_DIR, "data", "documents")
    try:
        os.makedirs(docs, exist_ok=True)
        tick("documents", "Documentos", True)
    except Exception as e:
        tick("documents", "Documentos", False, str(e))

    # Default parameters
    try:
        register_default_parameters()
        tick("parameters", "Parâmetros default", True)
    except Exception as e:
        tick("parameters", "Parâmetros default", False, str(e))

    # Logging Services
    try:
        init_logging()
        log_event("platform", "initialization", usuario="", detalhe="Plataforma inicializada")
        tick("logging", "Logging", True)
    except Exception as e:
        tick("logging", "Logging", False, str(e))

    state["init_progress"] = progress
    state["phase"] = "initialized"
    state["initialized_em"] = _now()
    _save(state)
    return progress


def init_after_admin(instance_name="", instance_description="", localization=None, usuario=""):
    """
    Fim da instalação (admin criado).
    Business Setup só após o primeiro login (RFC-0000 §10–11).
    """
    data = _fresh()
    name = str(instance_name or "Minha Empresa").strip() or "Minha Empresa"
    data["instance"]["name"] = name
    data["instance"]["identifier"] = _slug(name)
    data["instance"]["description"] = str(instance_description or "").strip()
    if isinstance(localization, dict):
        loc = data.setdefault("localization", {})
        for k in ("country", "language", "timezone", "currency"):
            if localization.get(k) is not None:
                loc[k] = str(localization.get(k) or "").strip()
        data.setdefault("steps_done", {})["localization"] = True
        data["current_step"] = "organization"
    else:
        data["current_step"] = "localization"
        data["steps_done"] = {}
    data["compat_legacy"] = False
    data["go_live"] = False
    progress = run_initialization(data)
    data = load_state()
    data["init_progress"] = progress
    _save(data)
    return {"state": data, "init_progress": progress}


def needs_wizard():
    if not _has_admin():
        return False
    state = load_state()
    if state.get("go_live"):
        return False
    return True


def is_installed():
    """Software + admin existem (check-setup)."""
    return _has_admin()


def status():
    state = load_state()
    org = org_store.load_organizacao()
    empresas = org_store.load_empresas()
    apps = app_registry.catalog()
    eid = org_store.estabelecimento_padrao_id()
    empresa = (empresas.get(eid) or {}) if eid else {}
    wh = _load_warehouses().get("warehouses") or []
    users = _load_users()
    ops_users = [
        u for u in users.values()
        if u.get("role") != "admin" and u.get("ativo", True)
    ]
    structure = state.get("structure") or {}
    setup_pending = [p for p in app_registry.setup_pending() if not p["done"]]

    checklist = [
        {"id": "instance", "label": "Business Instance", "ok": bool((state.get("instance") or {}).get("name"))},
        {"id": "admin", "label": "Administrador", "ok": _has_admin()},
        {"id": "localization", "label": "Localização", "ok": bool(state.get("steps_done", {}).get("localization"))},
        {"id": "organization", "label": "Organização", "ok": bool(state.get("steps_done", {}).get("organization")) or _org_configured()},
        {"id": "company", "label": "Empresa", "ok": bool(state.get("steps_done", {}).get("company")) or bool(empresas)},
        {"id": "users", "label": "Usuários operacionais", "ok": bool(ops_users) or bool(state.get("steps_done", {}).get("users")), "warn": not bool(ops_users)},
        {"id": "modules", "label": "Módulos", "ok": bool(state.get("steps_done", {}).get("modules")) or bool(apps.get("onboarding_complete"))},
        {
            "id": "module_setup",
            "label": "Setup dos módulos",
            "ok": not setup_pending,
            "warn": bool(setup_pending),
        },
        {
            "id": "warehouse",
            "label": "Depósito / Warehouse",
            "ok": bool(wh),
            "warn": not bool(wh),  # adiar é permitido
        },
        {"id": "go_live", "label": "Produção", "ok": bool(state.get("go_live"))},
    ]
    if not empresa.get("cnpj") and empresas:
        checklist.append({"id": "cnpj", "label": "CNPJ da empresa", "ok": False, "warn": True})

    current = state.get("current_step") or "localization"
    if state.get("go_live"):
        current = "go_live"

    steps = []
    for sid in STEPS:
        steps.append({
            "id": sid,
            "label": STEP_LABELS.get(sid, sid),
            "done": bool(state.get("steps_done", {}).get(sid)) or (
                sid == "go_live" and state.get("go_live")
            ),
            "current": sid == current and not state.get("go_live"),
        })

    return {
        "needs_wizard": needs_wizard(),
        "go_live": bool(state.get("go_live")),
        "compat_legacy": bool(state.get("compat_legacy")),
        "phase": state.get("phase") or "empty",
        "current_step": current,
        "steps": steps,
        "instance": state.get("instance") or {},
        "localization": state.get("localization") or {},
        "structure": structure,
        "init_progress": state.get("init_progress") or [],
        "organization": {
            "id": org.get("id"),
            "nome": org.get("nome") or "",
            "razao": org.get("razao") or org.get("legal_name") or "",
            "cnpj": org.get("cnpj") or "",
            "endereco": org.get("endereco") or "",
        },
        "company": {
            "id": eid,
            "nome": empresa.get("nome") or empresa.get("nome_fantasia") or "",
            "nome_razao": empresa.get("nome_razao") or "",
            "cnpj": empresa.get("cnpj") or "",
            "ie": empresa.get("ie") or empresa.get("inscricao_est") or "",
            "cidade": empresa.get("cidade") or empresa.get("municipio") or "",
            "uf": empresa.get("uf") or "",
            "endereco": empresa.get("endereco") or "",
        },
        "warehouses": wh,
        "users_count": len(users),
        "ops_users_count": len(ops_users),
        "setup_pending": setup_pending,
        "modules": {
            "onboarding_complete": apps.get("onboarding_complete"),
            "package_id": apps.get("package_id"),
            "installed": apps.get("installed") or [],
            "packages": apps.get("packages") or [],
        },
        "checklist": checklist,
        "has_admin": _has_admin(),
        "lifecycle": {
            "phase": state.get("phase") or "empty",
            "maintenance": bool(state.get("maintenance")),
            "archived": bool(state.get("archived")),
            "backups_count": len(list_backups()),
        },
        "atualizado_em": state.get("atualizado_em"),
        "nota": "RFC-0000 — instalação do zero → login → Business Setup → Go Live.",
    }


def _next_step(current):
    try:
        i = STEPS.index(current)
    except ValueError:
        return "localization"
    if i + 1 < len(STEPS):
        return STEPS[i + 1]
    return current


def save_step(step_id, payload=None, usuario=""):
    sid = str(step_id or "").strip().lower()
    if sid not in STEPS:
        raise ValueError("passo inválido")
    body = payload if isinstance(payload, dict) else {}
    state = load_state()
    in_production = bool(state.get("go_live"))

    # RFC-0000 §8: pós-produção só aceita ajustes in place (localização)
    if in_production and sid != "localization":
        raise ValueError("instância já em produção — use Apps/Configurações")

    if sid == "localization":
        loc = state.setdefault("localization", {})
        for k in ("country", "language", "timezone", "currency"):
            if body.get(k) is not None:
                loc[k] = str(body.get(k) or "").strip()
        if body.get("instance_name"):
            name = str(body.get("instance_name")).strip()
            state.setdefault("instance", {})["name"] = name
            state["instance"]["identifier"] = _slug(name)
        if body.get("instance_description") is not None:
            state.setdefault("instance", {})["description"] = str(body.get("instance_description") or "").strip()

    elif sid == "organization":
        nome = str(body.get("nome") or "").strip()
        if not nome:
            raise ValueError("nome da organização obrigatório")
        org = org_store.load_organizacao()
        org["nome"] = nome
        if body.get("razao") is not None:
            org["razao"] = str(body.get("razao") or "").strip()
        if body.get("cnpj") is not None:
            org["cnpj"] = org_store.digits(body.get("cnpj")) or str(body.get("cnpj") or "").strip()
        if body.get("endereco") is not None:
            org["endereco"] = str(body.get("endereco") or "").strip()
        org.setdefault("id", "org")
        org_store.save_organizacao(org)
        state.setdefault("instance", {})["name"] = nome
        state["instance"]["identifier"] = _slug(nome)

    elif sid == "company":
        nome = str(body.get("nome") or body.get("nome_fantasia") or "").strip()
        if not nome:
            raise ValueError("nome da empresa obrigatório")
        eid = str(body.get("id") or org_store.estabelecimento_padrao_id() or "matriz").strip() or "matriz"
        updates = {
            "nome": nome,
            "nome_fantasia": str(body.get("nome_fantasia") or nome).strip(),
            "nome_razao": str(body.get("nome_razao") or body.get("razao") or nome).strip(),
            "cnpj": body.get("cnpj") or "",
            "ie": body.get("ie") or "",
            "cidade": body.get("cidade") or body.get("municipio") or "",
            "uf": str(body.get("uf") or "").strip().upper()[:2],
            "endereco": body.get("endereco") or "",
            "ativo": True,
            "tipo": "matriz" if eid == "matriz" else "filial",
        }
        org_store.update_estabelecimento(eid, updates, also_fiscal=True)
        # filial opcional
        branch = str(body.get("branch_name") or body.get("filial") or "").strip()
        structure = state.setdefault("structure", {})
        structure["branch_name"] = branch
        if branch:
            fid = "filial-1"
            org_store.update_estabelecimento(fid, {
                "nome": branch,
                "nome_fantasia": branch,
                "nome_razao": updates["nome_razao"],
                "cnpj": updates["cnpj"],
                "cidade": updates["cidade"],
                "uf": updates["uf"],
                "ativo": True,
                "tipo": "filial",
            }, also_fiscal=True)
        # warehouse opcional
        wh_name = str(body.get("warehouse_name") or body.get("deposito") or "").strip()
        postpone = body.get("warehouse_postpone")
        if postpone is None:
            postpone = not bool(wh_name)
        structure["warehouse_name"] = wh_name
        structure["warehouse_postponed"] = bool(postpone) and not wh_name
        if wh_name:
            wh = _load_warehouses()
            if not any(w.get("nome") == wh_name for w in wh.get("warehouses") or []):
                wh.setdefault("warehouses", []).append({
                    "id": "WH-01",
                    "nome": wh_name,
                    "estabelecimento_id": eid,
                    "criado_em": _now(),
                })
                _save_warehouses(wh)
            structure["warehouse_postponed"] = False
        org = org_store.load_organizacao()
        org["estabelecimento_padrao"] = eid
        org_store.save_organizacao(org)
        try:
            org_store.sync_legacy_empresa_json(eid)
        except Exception:
            pass

    elif sid == "users":
        # opcional: cria um usuário operacional; ou skip
        skip = bool(body.get("skip"))
        if not skip:
            nome = str(body.get("nome") or "").strip()
            usuario = str(body.get("usuario") or "").strip()
            senha = str(body.get("senha") or "").strip()
            role = str(body.get("role") or "operador").strip().lower() or "operador"
            if role not in ("operador", "supervisor", "gerente", "manager", "operator"):
                role = "operador"
            if role == "manager":
                role = "gerente"
            if role == "operator":
                role = "operador"
            if not (nome and usuario and senha):
                raise ValueError("informe nome, usuário e senha — ou marque pular")
            users = _load_users()
            if any(str(u.get("usuario") or "").lower() == usuario.lower() for u in users.values()):
                raise ValueError("usuário já existe")
            import hashlib
            import uuid

            uid = str(uuid.uuid4())[:8]
            users[uid] = {
                "usuario": usuario,
                "nome": nome,
                "senha": hashlib.sha256(senha.encode()).hexdigest(),
                "email": str(body.get("email") or "").strip(),
                "role": role,
                "empresas": {},
                "ativo": True,
                "token": "",
            }
            _save_users(users)

    elif sid == "modules":
        pkg = str(body.get("package_id") or body.get("package") or "").strip().lower()
        if pkg:
            app_registry.apply_package(
                pkg,
                app_ids=body.get("apps") or body.get("app_ids"),
                usuario=usuario,
            )
        elif not app_registry.load_state().get("onboarding_complete"):
            raise ValueError("escolha um pacote (Loja, Atacado ou Personalizado)")
        pending = [p for p in app_registry.setup_pending() if not p["done"]]
        if any(p["required"] for p in pending):
            # RFC-0000 §18: encadeia os wizards — permanece no passo
            # até os setups obrigatórios serem concluídos
            state.setdefault("steps_done", {})["modules"] = False
            state["current_step"] = "modules"
            state["compat_legacy"] = False
            if state.get("phase") in ("empty", "initialized"):
                state["phase"] = "business_setup"
            _save(state)
            return status()

    elif sid == "validation":
        pass

    elif sid == "go_live":
        return go_live(usuario=usuario)

    state.setdefault("steps_done", {})[sid] = True
    if sid == "users":
        # §16: usuários são opcionais — só marca feito se houver usuário criado
        has_ops = any(
            u.get("role") != "admin" and u.get("ativo", True)
            for u in _load_users().values()
        )
        state["steps_done"]["users"] = has_ops
    if in_production:
        # ajuste pós-produção: não avança o wizard
        _save(state)
        return status()
    nxt = _next_step(sid)
    state["current_step"] = nxt
    state["compat_legacy"] = False
    if state.get("phase") in ("empty", "initialized"):
        state["phase"] = "business_setup"
    _save(state)
    return status()


def go_live(usuario=""):
    state = load_state()
    if not _has_admin():
        raise ValueError("administrador obrigatório")
    if not _org_configured():
        raise ValueError("organização obrigatória")
    if not org_store.load_empresas():
        raise ValueError("empresa obrigatória")
    if not app_registry.load_state().get("onboarding_complete"):
        raise ValueError("instale ao menos um pacote/módulo")
    if not state.get("steps_done", {}).get("localization"):
        # localization from install counts
        if (state.get("localization") or {}).get("country"):
            state.setdefault("steps_done", {})["localization"] = True
        else:
            raise ValueError("localização obrigatória")

    state["steps_done"]["validation"] = True
    state["steps_done"]["go_live"] = True
    # §16: usuários são opcionais — registra a realidade, não "feito" cego
    has_ops = any(
        u.get("role") != "admin" and u.get("ativo", True)
        for u in _load_users().values()
    )
    state["steps_done"]["users"] = has_ops
    state["go_live"] = True
    state["phase"] = "operational"
    state["current_step"] = "go_live"
    state["go_live_em"] = _now()
    state["go_live_by"] = str(usuario or "").strip()
    _save(state)
    return status()


def set_step(step_id):
    sid = str(step_id or "").strip().lower()
    if sid not in STEPS:
        raise ValueError("passo inválido")
    state = load_state()
    if state.get("go_live") and sid != "go_live":
        raise ValueError("instância já em produção — use Apps/Configurações")
    state["current_step"] = sid
    _save(state)
    return status()


def reopen_business_setup(usuario=""):
    state = load_state()
    state["go_live"] = False
    state["compat_legacy"] = False
    state["phase"] = "business_setup"
    done = {"localization": True} if (state.get("localization") or {}).get("country") else {}
    state["steps_done"] = done
    state["current_step"] = "organization" if done.get("localization") else "localization"
    state["reopened_em"] = _now()
    state["reopened_by"] = str(usuario or "").strip()
    _save(state)
    try:
        app_registry.init_base()
    except Exception:
        pass
    return status()


def factory_reset(confirm="", usuario=""):
    """
    Volta a plataforma ao estado vazio (RFC-0000 do zero).
    Apaga admin, setup, apps, org/empresas de setup.
    Não apaga dados operacionais de módulos (delivery, estoque…).
    """
    if str(confirm or "").strip().upper() != FACTORY_CONFIRM:
        raise ValueError(f'Digite "{FACTORY_CONFIRM}" para confirmar a reinstalação')

    _save_users({})
    try:
        app_registry.init_base()
    except Exception:
        pass
    org_store.save_organizacao({
        "id": "org",
        "nome": "",
        "razao": "",
        "cnpj": "",
        "endereco": "",
        "estabelecimento_padrao": "matriz",
    })
    org_store.save_empresas({})
    try:
        org_store.save_fiscal_store({})
    except Exception:
        pass
    _save_warehouses({"warehouses": []})
    register_default_parameters(overwrite=True)

    data = _fresh()
    data["phase"] = "empty"
    data["reset_em"] = _now()
    data["reset_by"] = str(usuario or "").strip()
    _save(data)

    return {
        "reset": True,
        "confirm": FACTORY_CONFIRM,
        "next": "install",
        "message": "Plataforma limpa. Acesse /install.html para instalar do zero.",
        **status(),
    }
