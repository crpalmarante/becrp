"""
BECRP Apps Platform — registry + pacotes (RFC-1000 / RFC-1001 MVP).

Fase 1: base (admin/dados) — sem pacote de comércio.
Fase 2: admin aplica Loja | Atacado | Personalizado.

Fonte: data/org_apps.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "org_apps.json")

# apps do catálogo v1
APP_CATALOG = {
    "pos": {
        "id": "pos",
        "name": "POS",
        "summary": "Venda ao consumidor final (PDV / caixa)",
        "category": "operacao",
    },
    "sales": {
        "id": "sales",
        "name": "Vendas",
        "summary": "B2B — CNPJ→CNPJ, pedidos, licitação",
        "category": "operacao",
    },
    "inventory": {
        "id": "inventory",
        "name": "Estoque",
        "summary": "Saldo e movimentos básicos",
        "category": "operacao",
    },
    "fiscal": {
        "id": "fiscal",
        "name": "Fiscal",
        "summary": "NFC-e / NF-e e motor fiscal",
        "category": "conformidade",
    },
    "purchases": {
        "id": "purchases",
        "name": "Compras",
        "summary": "Pedidos a fornecedor / recebimento",
        "category": "operacao",
    },
    "wms": {
        "id": "wms",
        "name": "WMS",
        "summary": "Armazém avançado",
        "category": "operacao",
    },
    "delivery": {
        "id": "delivery",
        "name": "Entregas",
        "summary": "Pedidos de entrega e operação de campo",
        "category": "operacao",
    },
    "accounting": {
        "id": "accounting",
        "name": "Contabilidade",
        "summary": "Plano, diários, períodos",
        "category": "conformidade",
    },
    "hr_payroll": {
        "id": "hr_payroll",
        "name": "Folha",
        "summary": "Funcionários e folha de pagamento",
        "category": "conformidade",
    },
}

# RFC-0000 §17 — dependências entre apps (resolvidas automaticamente)
_DEPENDS_ON = {
    "pos": ["inventory"],
    "sales": ["inventory"],
    "purchases": ["inventory"],
    "wms": ["inventory"],
    "delivery": ["inventory"],
}
for _aid, _deps in _DEPENDS_ON.items():
    APP_CATALOG.setdefault(_aid, {})["depends_on"] = list(_deps)

PACKAGES = {
    "retail": {
        "id": "retail",
        "name": "Loja",
        "summary": "PDV + estoque + fiscal — consumidor final",
        "recommended": True,
        "apps": ["pos", "inventory", "fiscal"],
    },
    "wholesale": {
        "id": "wholesale",
        "name": "Atacado / B2B",
        "summary": "Vendas CNPJ + estoque + fiscal",
        "recommended": False,
        "apps": ["sales", "inventory", "fiscal"],
    },
    "custom": {
        "id": "custom",
        "name": "Personalizado",
        "summary": "Escolha os apps um a um",
        "recommended": False,
        "apps": [],  # preenchido na hora
    },
}

# menu módulo id → app id (ausente = base, sempre visível)
MENU_MODULE_APP = {
    "ponto_vendas": "pos",
    "vendas": "sales",
    "compras": "purchases",
    "inventario": "inventory",
    "wms": "wms",
    "delivery": "delivery",
    "fiscal": "fiscal",
    "faturamento": "fiscal",
    "funcionarios": "hr_payroll",
}

# itens dentro de Configurações que pertencem a accounting
ACCOUNTING_MENU_APP_IDS = {
    "plano-contas", "diarios", "lancamentos", "razao",
    "periodos", "relatorios-contabeis", "analytics-contabil",
}

BASE_MENU_IDS = {"dashboard", "cadastros", "configuracoes", "apps"}

# Setup por app (RFC-0000 §18 / Rule 5) — cada módulo se autodescreve.
# Ausente no SETUP_DESCRIPTORS = app não exige setup.
SETUP_FILE = os.path.join(BASE_DIR, "data", "module_setup.json")
SETUP_DESCRIPTORS = {
    "inventory": {"url": "pages/estoque.html", "label": "Estoque / Depósito", "required": True},
    "fiscal": {"url": "pages/empresas.html", "label": "Dados fiscais da empresa", "required": True},
    "pos": {"url": "pages/pos.html", "label": "Caixa / Terminal", "required": False},
    "sales": {"url": "pages/listas-preco.html", "label": "Lista de preços", "required": False},
    "purchases": {"url": "pages/recebimento.html", "label": "Recebimento / Fornecedores", "required": False},
    "wms": {"url": "pages/wms-armazens.html", "label": "Armazéns", "required": False},
    "delivery": {"url": "pages/entregas.html", "label": "Zonas / Motoristas", "required": False},
    "accounting": {"url": "pages/plano-contas.html", "label": "Plano de contas", "required": False},
    "hr_payroll": {"url": "pages/funcionarios.html", "label": "Funcionários", "required": False},
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _empty_apps(installed=False):
    return {
        aid: {"installed": bool(installed), "version": "1.0.0"}
        for aid in APP_CATALOG
    }


def _legacy_all_installed():
    """Compat: instalação já existente não perde o menu."""
    return {
        "version": 1,
        "onboarding_complete": True,
        "compat_legacy": True,
        "package_id": "",
        "apps": _empty_apps(True),
        "atualizado_em": _now(),
    }


def _base_state():
    """Após Fase 1: registry limpo, admin escolhe pacote."""
    return {
        "version": 1,
        "onboarding_complete": False,
        "compat_legacy": False,
        "package_id": "",
        "apps": _empty_apps(False),
        "atualizado_em": _now(),
    }


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_state():
    if not os.path.exists(DATA_FILE):
        # legado: não quebrar demo atual
        data = _legacy_all_installed()
        _save(data)
        return data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        data = _legacy_all_installed()
        _save(data)
        return data
    data.setdefault("apps", {})
    for aid in APP_CATALOG:
        data["apps"].setdefault(aid, {"installed": False, "version": "1.0.0"})
    data.setdefault("onboarding_complete", False)
    data.setdefault("package_id", "")
    return data


def init_base():
    """Chamado no fim da Fase 1 (criação do admin)."""
    data = _base_state()
    _save(data)
    reset_setup()
    return data


def is_installed(app_id, state=None):
    state = state or load_state()
    row = (state.get("apps") or {}).get(str(app_id) or "")
    if not isinstance(row, dict):
        return False
    return bool(row.get("installed"))


def installed_apps(state=None):
    state = state or load_state()
    return sorted(
        aid for aid in APP_CATALOG
        if is_installed(aid, state)
    )


def resolve_dependencies(ids, state=None):
    """Closure transitiva das dependências (RFC-0000 §17)."""
    state = state or load_state()
    result = set()
    stack = [str(a).strip().lower() for a in (ids or [])]
    while stack:
        aid = stack.pop()
        if aid not in APP_CATALOG or aid in result:
            continue
        result.add(aid)
        for dep in (APP_CATALOG.get(aid) or {}).get("depends_on") or []:
            if dep not in result:
                stack.append(dep)
    return sorted(result)


def missing_dependencies(state=None):
    """Apps instalados com dependência ausente."""
    st = state or load_state()
    out = {}
    for aid in APP_CATALOG:
        if not is_installed(aid, st):
            continue
        deps = (APP_CATALOG.get(aid) or {}).get("depends_on") or []
        missing = [d for d in deps if not is_installed(d, st)]
        if missing:
            out[aid] = missing
    return out


def catalog():
    state = load_state()
    setup_state = load_setup_state()
    apps = []
    for aid, meta in APP_CATALOG.items():
        row = dict(meta)
        row["installed"] = is_installed(aid, state)
        desc = SETUP_DESCRIPTORS.get(aid)
        row["setup"] = {
            "url": (desc or {}).get("url", ""),
            "label": (desc or {}).get("label", ""),
            "required": bool((desc or {}).get("required")),
            "done": setup_done(aid, setup_state),
        }
        apps.append(row)
    packages = []
    for pid, meta in PACKAGES.items():
        packages.append(dict(meta))
    return {
        "apps": apps,
        "packages": packages,
        "installed": installed_apps(state),
        "setup_pending": [p for p in setup_pending(state=state, setup_state=setup_state) if not p["done"]],
        "setup_all_done": all(p["done"] for p in setup_pending(state=state, setup_state=setup_state)),
        "missing_dependencies": missing_dependencies(state),
        "onboarding_complete": bool(state.get("onboarding_complete")),
        "package_id": state.get("package_id") or "",
        "compat_legacy": bool(state.get("compat_legacy")),
        "atualizado_em": state.get("atualizado_em"),
        "nota": "Fase 1 = base. Fase 2 = admin aplica pacote/apps (RFC-1001).",
    }


def apply_package(package_id, app_ids=None, usuario=""):
    """Aplica preset Loja / Atacado / Personalizado."""
    pid = str(package_id or "").strip().lower()
    if pid not in PACKAGES:
        raise ValueError("pacote inválido")

    if pid == "custom":
        raw = app_ids or []
        if isinstance(raw, str):
            raw = [x.strip() for x in raw.split(",") if x.strip()]
        for a in raw:
            a = str(a).strip().lower()
            if a not in APP_CATALOG:
                raise ValueError(f"app inválido: {a}")
        if not raw:
            raise ValueError("marque ao menos um app")
        ids = resolve_dependencies(raw)
    else:
        ids = resolve_dependencies(PACKAGES[pid]["apps"])

    state = load_state()
    before = set(installed_apps(state))
    idset = set(ids)
    # pacote = footprint exato (Loja / Atacado / Personalizado)
    for aid in APP_CATALOG:
        on = aid in idset
        state["apps"][aid] = {
            "installed": on,
            "version": "1.0.0",
            "installed_at": _now() if on else "",
            "by": str(usuario or "").strip(),
        }
    state["package_id"] = pid
    state["onboarding_complete"] = True
    state["compat_legacy"] = False
    _save(state)
    # RFC-0000 §18: só apps recém-instalados (ou removidos) exigem setup de novo
    for aid in sorted(idset - before):
        reset_setup(aid)
    for aid in sorted(before - idset):
        reset_setup(aid)
    return catalog()


def set_app(app_id, installed, usuario=""):
    aid = str(app_id or "").strip().lower()
    if aid not in APP_CATALOG:
        raise ValueError("app inválido")
    state = load_state()
    if bool(installed):
        # RFC-0000 §17 — instala dependências automaticamente
        for dep in resolve_dependencies([aid], state):
            state["apps"][dep] = {
                "installed": True,
                "version": "1.0.0",
                "installed_at": _now(),
                "by": str(usuario or "").strip(),
            }
            reset_setup(dep)
        if not state.get("onboarding_complete"):
            state["onboarding_complete"] = True
    else:
        state["apps"][aid] = {
            "installed": False,
            "version": "1.0.0",
            "updated_at": _now(),
            "by": str(usuario or "").strip(),
        }
        reset_setup(aid)
    state["compat_legacy"] = False
    _save(state)
    return catalog()


def menu_module_allowed(module_id, state=None):
    mid = str(module_id or "").strip()
    if mid in BASE_MENU_IDS or mid == "apps":
        return True
    app_id = MENU_MODULE_APP.get(mid)
    if not app_id:
        return True  # desconhecido → não esconder
    return is_installed(app_id, state)


def menu_entry_allowed(entry_id, parent_module_id=None, state=None):
    """Filtra itens; accounting sob configuracoes."""
    eid = str(entry_id or "").strip()
    if eid in ACCOUNTING_MENU_APP_IDS:
        return is_installed("accounting", state)
    if parent_module_id:
        return menu_module_allowed(parent_module_id, state)
    return True


def filter_menu_tree(menu_items):
    """Filtra menu.json (lista de módulos)."""
    state = load_state()
    out = []
    for mod in menu_items or []:
        if not isinstance(mod, dict):
            continue
        mid = mod.get("id")
        if not menu_module_allowed(mid, state):
            continue
        row = dict(mod)
        apps = []
        for a in mod.get("apps") or []:
            if not isinstance(a, dict):
                continue
            if a.get("section"):
                apps.append(a)
                continue
            aid = a.get("id")
            if mid == "configuracoes" and aid in ACCOUNTING_MENU_APP_IDS:
                if not is_installed("accounting", state):
                    continue
            apps.append(a)
        row["apps"] = apps
        out.append(row)
    return out


# --- Setup por app (RFC-0000 §18 / Rule 5) --------------------------------


def _empty_setup_state():
    return {
        "version": 1,
        "apps": {
            aid: {"done": False, "done_at": "", "by": ""}
            for aid in APP_CATALOG
        },
        "atualizado_em": _now(),
    }


def _legacy_setup_done():
    """Compat: instância já operacional — setups considerados concluídos."""
    return {
        "version": 1,
        "compat_legacy": True,
        "apps": {
            aid: {"done": True, "done_at": "", "by": ""}
            for aid in APP_CATALOG
        },
        "atualizado_em": _now(),
    }


def _save_setup(data):
    os.makedirs(os.path.dirname(SETUP_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    with open(SETUP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_setup_state():
    if not os.path.exists(SETUP_FILE):
        st = load_state()
        if st.get("compat_legacy") or st.get("onboarding_complete"):
            data = _legacy_setup_done()
        else:
            data = _empty_setup_state()
        _save_setup(data)
        return data
    with open(SETUP_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        data = _empty_setup_state()
        _save_setup(data)
        return data
    data.setdefault("apps", {})
    for aid in APP_CATALOG:
        data["apps"].setdefault(aid, {"done": False, "done_at": "", "by": ""})
    return data


def setup_descriptor(app_id):
    return SETUP_DESCRIPTORS.get(str(app_id or "").strip().lower())


def setup_done(app_id, setup_state=None):
    row = ((setup_state or load_setup_state()).get("apps", {})
           .get(str(app_id or "").strip().lower()) or {})
    return bool(row.get("done"))


def setup_pending(state=None, setup_state=None):
    """Apps instalados com setup registrado e ainda não configurados."""
    st = state or load_state()
    ss = setup_state or load_setup_state()
    out = []
    for aid in SETUP_DESCRIPTORS:
        if not is_installed(aid, st):
            continue
        desc = SETUP_DESCRIPTORS[aid]
        out.append({
            "app_id": aid,
            "name": (APP_CATALOG.get(aid) or {}).get("name", aid),
            "label": desc.get("label") or "",
            "url": desc.get("url") or "",
            "required": bool(desc.get("required")),
            "done": setup_done(aid, ss),
        })
    return out


def mark_setup_done(app_id, usuario=""):
    aid = str(app_id or "").strip().lower()
    if aid not in SETUP_DESCRIPTORS:
        raise ValueError("app sem setup registrado")
    data = load_setup_state()
    row = data["apps"].setdefault(aid, {})
    row["done"] = True
    row["done_at"] = row.get("done_at") or _now()
    row["by"] = str(usuario or "").strip()
    _save_setup(data)
    return {"app_id": aid, **row}


def reset_setup(app_id=None, usuario=""):
    """Limpa done de um app ou de todos (factory reset / nova instalação)."""
    data = load_setup_state()
    if app_id:
        aid = str(app_id).strip().lower()
        row = data["apps"].setdefault(aid, {})
        row["done"] = False
        row["done_at"] = ""
        row["by"] = ""
    else:
        data = _empty_setup_state()
        data["reset_em"] = _now()
        data["reset_by"] = str(usuario or "").strip()
    _save_setup(data)
    return data
