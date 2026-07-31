#!/usr/bin/env python3
"""FiscalBrasil ERP — Servidor de Desenvolvimento com autenticação real e mult-empresa"""

import http.server
import json
import os
import sys
import urllib.parse
import hashlib
import uuid
from datetime import datetime
import cobol_bridge
import inventory_mvp
import receiving_mvp
from modules.certificate import cert_service
from modules.sefaz import sefaz_service
from modules.sefaz import nfce_xml
from modules.sefaz import nfe_xml
from modules.sefaz import nfse_service
from modules.sefaz import nfse_xml
from modules.sefaz import tributos
from modules.sped import sped_fiscal
from modules.sped import sped_pis_cofins
from modules.sefaz import danfe
from modules.lookup import ncm_cest_service

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
HOST = "0.0.0.0"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
EMPRESAS_FILE = os.path.join(DATA_DIR, "empresas.json")
CATEGORIAS_FILE = os.path.join(DATA_DIR, "categorias.json")
MARCAS_FILE = os.path.join(DATA_DIR, "marcas.json")
FABRICANTES_FILE = os.path.join(DATA_DIR, "fabricantes.json")
CONTATOS_FILE = os.path.join(DATA_DIR, "contatos.json")
PARTNERS_FILE = os.path.join(DATA_DIR, "partners.json")
POS_FILA_FILE = os.path.join(DATA_DIR, "pos_fila.json")
POS_TERMINAIS_FILE = os.path.join(DATA_DIR, "pos_terminais.json")

os.makedirs(DATA_DIR, exist_ok=True)

EMPRESA_JSON = os.path.join(BASE_DIR, "dados", "empresa.json")
ESTAB_FISCAL_FILE = os.path.join(DATA_DIR, "estabelecimentos_fiscal.json")

def load_empresa_fiscal():
    if not os.path.exists(EMPRESA_JSON):
        return {}
    with open(EMPRESA_JSON, "r") as f:
        return json.load(f)

def load_estab_fiscal_store():
    data = load_json(ESTAB_FISCAL_FILE)
    return data if isinstance(data, dict) else {}

def save_estab_fiscal_store(data):
    save_json(ESTAB_FISCAL_FILE, data if isinstance(data, dict) else {})

def _digits(val):
    return "".join(ch for ch in str(val or "") if ch.isdigit())

def resolve_empresa_fiscal(estabelecimento_id=None):
    """
    Emitente NFC-e = estabelecimento do terminal.
    Camadas: dados/empresa.json (legado) ← dados estruturais da filial ← overlay fiscal.
    """
    base = dict(load_empresa_fiscal() or {})
    eid = str(estabelecimento_id or "").strip()
    if not eid:
        base["estabelecimento_id"] = None
        return base

    empresas = load_empresas()
    estab = dict(empresas.get(eid, {}) or {})
    overlay = dict(load_estab_fiscal_store().get(eid, {}) or {})

    if estab.get("nome"):
        base["nome_fantasia"] = estab["nome"]
        if not overlay.get("nome"):
            base["nome"] = estab["nome"]
    cnpj = overlay.get("cnpj") or estab.get("cnpj")
    if cnpj:
        base["cnpj"] = _digits(cnpj) or base.get("cnpj")
    ie = overlay.get("inscricao_est") or overlay.get("ie") or estab.get("ie")
    if ie:
        base["inscricao_est"] = ie
    if estab.get("cidade") and not overlay.get("municipio"):
        base["municipio"] = estab["cidade"]
    uf_estab = overlay.get("uf") if overlay.get("uf") is not None else estab.get("uf")
    if uf_estab is not None and uf_estab != "":
        base["uf"] = uf_estab

    for k, v in overlay.items():
        if v is None or v == "":
            continue
        if k in ("cnpj",):
            base[k] = _digits(v) or base.get(k)
        else:
            base[k] = v

    base["estabelecimento_id"] = eid
    return base

def _terminal_do_usuario(uid):
    if not uid:
        return None
    for t in load_pos_terminais().get("terminais", []):
        if t.get("ativo", True) and t.get("usuario_id") == uid:
            return t
    return None

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

def load_empresas():
    if not os.path.exists(EMPRESAS_FILE):
        return {}
    with open(EMPRESAS_FILE, "r") as f:
        return json.load(f)

def save_empresas(empresas):
    with open(EMPRESAS_FILE, "w") as f:
        json.dump(empresas, f, indent=2, ensure_ascii=False)

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_pos_terminais():
    data = load_json(POS_TERMINAIS_FILE)
    if not isinstance(data, dict) or "terminais" not in data:
        return {"terminais": []}
    if not isinstance(data.get("terminais"), list):
        data["terminais"] = []
    return data

def save_pos_terminais(data):
    if not isinstance(data, dict):
        data = {"terminais": []}
    if not isinstance(data.get("terminais"), list):
        data["terminais"] = []
    save_json(POS_TERMINAIS_FILE, data)

def _pdv_user_conflict(terminais, usuario_id, exclude_id=None):
    """Vendedor ↔ PDV 1:1 — retorna terminal conflitante ou None."""
    if not usuario_id:
        return None
    for t in terminais:
        if t.get("tipo") != "pdv":
            continue
        if not t.get("ativo", True):
            continue
        if t.get("usuario_id") == usuario_id and t.get("id") != exclude_id:
            return t
    return None

def promise_produto(estabelecimento_id, produto_id, empresas=None):
    """Promise Engine (POS) — lê ledger/cache do Inventário MVP."""
    return inventory_mvp.inventory_promise(
        estabelecimento_id,
        produto_id,
        empresas=empresas if empresas is not None else load_empresas(),
    )

def enriquecer_produtos_com_promise(produtos, estabelecimento_id):
    return inventory_mvp.enriquecer_produtos_com_promise(
        produtos, estabelecimento_id, empresas=load_empresas()
    )

def baixar_estoque_local(estabelecimento_id, linhas, venda_id=None):
    """Compat: delega para inventory_apply_sale (movimento sale)."""
    return inventory_mvp.inventory_apply_sale(estabelecimento_id, linhas, venda_id=venda_id)

def load_pos_fila():
    data = load_json(POS_FILA_FILE)
    if not isinstance(data, dict) or "pedidos" not in data:
        return {"next_num": 1000, "pedidos": []}
    if not isinstance(data.get("pedidos"), list):
        data["pedidos"] = []
    if not isinstance(data.get("next_num"), int):
        data["next_num"] = 1000
    return data

def save_pos_fila(data):
    save_json(POS_FILA_FILE, data)

def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return float(default)

def _digits(val):
    return "".join(c for c in str(val or "") if c.isdigit())

def _resolve_cert_id(empresa, preferred_id=""):
    preferred_id = str(preferred_id or "").strip()
    if preferred_id and cert_service.obter(preferred_id):
        return preferred_id
    certs = cert_service.listar()
    if not certs:
        return ""
    arq = (empresa or {}).get("certificado") or ""
    cnpj = _digits((empresa or {}).get("cnpj"))
    for c in certs:
        if arq and c.get("arquivo") == arq:
            return c.get("id") or ""
    for c in certs:
        nome = (c.get("nome") or "").upper()
        if cnpj and cnpj in nome:
            return c.get("id") or ""
        if "FABIELI" in nome:
            return c.get("id") or ""
    for c in certs:
        if c.get("valido") and c.get("ativo", True):
            return c.get("id") or ""
    return certs[0].get("id") or ""

def _pedido_para_venda(pedido, forma_pg="Dinheiro"):
    """Converte pedido da fila POS no formato esperado por nfce_xml / vendas.json."""
    agora = datetime.now()
    client = pedido.get("client") or {}
    itens = []
    catalog = {}
    try:
        for p in cobol_bridge.produtos_listar() or []:
            catalog[str(p.get("id"))] = p
    except Exception:
        catalog = {}
    for line in pedido.get("lines") or []:
        pid = line.get("id")
        prod = catalog.get(str(pid), {})
        qtd = _safe_float(line.get("qtd"), 1)
        preco = _safe_float(line.get("preco"), 0)
        subtotal = round(qtd * preco, 2)
        itens.append({
            "prod_id": pid,
            "produto": line.get("nome") or prod.get("nome") or f"Produto {pid}",
            "qtd": qtd,
            "preco": preco,
            "subtotal": subtotal,
            "unidade": "KG" if line.get("peso") else (prod.get("unidade") or "UN"),
            "ncm": prod.get("ncm") or "00000000",
            "ean": prod.get("codigo_barras") or line.get("ean") or "",
            "cfop": prod.get("cfop") or "5102",
            "cst": prod.get("cst") or "400",
            "filial_id": 0,
        })
    return {
        "id": pedido.get("orderNum") or pedido.get("id"),
        "data": agora.strftime("%Y-%m-%d"),
        "hora": agora.strftime("%H:%M:%S"),
        "cliente": client.get("nome") or "Consumidor Final",
        "cliente_id": client.get("id") or "cf",
        "cliente_cpf": client.get("cpf") or "",
        "total": _safe_float(pedido.get("total"), 0),
        "forma_pg": forma_pg or "Dinheiro",
        "filial_id": 0,
        "pos_pedido_id": pedido.get("id"),
        "itens": itens,
    }

def _avancar_numero_nfce(estabelecimento_id=None):
    eid = str(estabelecimento_id or "").strip()
    if eid:
        store = load_estab_fiscal_store()
        entry = dict(store.get(eid) or {})
        n = int(entry.get("numero_nfce") or 0) + 1
        entry["numero_nfce"] = n
        if "serie_nfce" not in entry:
            entry["serie_nfce"] = 1
        store[eid] = entry
        save_estab_fiscal_store(store)
        return n
    cobol_bridge._compile_if_needed("gerir_numeracao")
    out, _ = cobol_bridge._run("gerir_numeracao", {"ACAO": "avancar-nfce"})
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    return 0

def _autorizar_nfce_de_venda(venda, empresa, cert_id, cert_senha, ambiente=2, serie=1, numero=0):
    uf = empresa.get("uf", "RS")
    if isinstance(uf, int) or (isinstance(uf, str) and uf.isdigit()):
        uf_codes = {
            11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
            21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL",
            28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ", 35: "SP", 41: "PR",
            42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF",
        }
        uf = uf_codes.get(int(uf), "RS")
    elif isinstance(uf, str) and len(uf) == 2:
        uf = uf.upper()
    eid = empresa.get("estabelecimento_id")
    if not numero:
        numero = _avancar_numero_nfce(eid)
    if not numero:
        raise ValueError("Erro ao obter numeração NFC-e")
    xml_envi = nfce_xml.montar_envi_nfe(venda, empresa, ambiente, serie, numero)
    resultado = sefaz_service.autorizar_nfce(
        xml_envi, uf, ambiente, cert_id, cert_senha, empresa=empresa
    )
    nfce_path = os.path.join(BASE_DIR, "dados", "nfce.json")
    nfce_data = load_json(nfce_path)
    if not isinstance(nfce_data, dict):
        nfce_data = {"nfce": []}
    notas = nfce_data.get("nfce") or []
    notas.append({
        "venda_id": venda.get("id"),
        "pos_pedido_id": venda.get("pos_pedido_id"),
        "estabelecimento_id": eid,
        "numero": numero,
        "serie": serie,
        "chave": resultado.get("chave", ""),
        "ambiente": ambiente,
        "status": resultado.get("status", "ERRO"),
        "protocolo": resultado.get("nProt", resultado.get("protocolo", "")),
        "cStat": resultado.get("cStat", ""),
        "xMotivo": resultado.get("xMotivo", ""),
        "xml": xml_envi,
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    nfce_data["nfce"] = notas
    save_json(nfce_path, nfce_data)
    return {"resultado": resultado, "numero": numero, "serie": serie, "chave": resultado.get("chave", "")}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def make_token():
    return hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:32]

ROLES = {
    # Administração / sistema
    "admin": {
        "label": "Administrador",
        "grupo": "sistema",
        "permissoes": "*",
        "pos": "hub",
        "descricao": "Configurações, usuários, terminais e todos os módulos",
    },
    # Operação POS (plano RFC)
    "vendedor": {
        "label": "Vendedor",
        "grupo": "pos",
        "permissoes": ["dashboard", "pos", "produtos"],
        "pos": "pdv",
        "descricao": "Opera um PDV (vínculo 1:1). Não acessa Caixa nem Configurações.",
    },
    "caixa": {
        "label": "Caixa",
        "grupo": "pos",
        "permissoes": ["dashboard", "pos", "nfce"],
        "pos": "caixa",
        "descricao": "Terminal Caixa: fila, pagamento e NFC-e. Vê PDVs da loja.",
    },
    "gerente": {
        "label": "Gerente",
        "grupo": "pos",
        "permissoes": ["dashboard", "pos", "nfce", "produtos", "relatorios"],
        "pos": "ambos",
        "descricao": "Supervisão da loja: PDVs e Caixas do estabelecimento.",
    },
    # Legado (mantidos)
    "supervisor": {
        "label": "Supervisor",
        "grupo": "legado",
        "permissoes": ["dashboard", "nfe", "nfce", "nfse", "clientes", "produtos", "relatorios", "folha", "contabilidade"],
        "pos": "ambos",
        "descricao": "Perfil legado — preferir Gerente no POS.",
    },
    "operador": {
        "label": "Operador",
        "grupo": "legado",
        "permissoes": ["dashboard", "nfe", "nfce", "pos"],
        "pos": "pdv",
        "descricao": "Perfil legado — preferir Vendedor no POS.",
    },
    "fiscal": {
        "label": "Fiscal",
        "grupo": "legado",
        "permissoes": ["dashboard", "nfe", "nfce", "nfse", "certificados", "sped"],
        "pos": None,
        "descricao": "Documentos fiscais (não é perfil de loja POS).",
    },
}

ROLE_IDS = set(ROLES.keys())

def role_label(role):
    return (ROLES.get(role) or {}).get("label") or role or "—"

def user_empresas(user):
    if user.get("role") == "admin":
        return list(load_empresas().keys())
    return list(user.get("empresas", {}).keys())

class AuthHandler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/auth/me":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            for uid, u in users.items():
                if u.get("token") == token:
                    data = dict(u)
                    data.pop("senha", None)
                    data.pop("token", None)
                    data["id"] = uid
                    data["empresas"] = user_empresas(u)
                    return self._json({"status": "ok", "conta": data})
            return self._json({"status": "error", "message": "Token inválido"}, 401)

        if parsed.path == "/api/auth/check-setup":
            users = load_users()
            has_admin = any(u.get("role") == "admin" for u in users.values())
            return self._json({"status": "ok", "setup": not has_admin})

        if parsed.path == "/api/auth/logout":
            return self._json({"status": "ok"})

        if parsed.path == "/api/auth/minhas-empresas":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            empresas = load_empresas()
            lista = []
            for eid in user_empresas(current):
                if eid in empresas:
                    e = dict(empresas[eid])
                    e["id"] = eid
                    e["role"] = current.get("empresas", {}).get(eid, current["role"])
                    lista.append(e)
            return self._json({"status": "ok", "empresas": lista})

        if parsed.path == "/api/admin/users":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            lista = []
            for uid, u in users.items():
                role = u.get("role", "operador")
                item = {"id": uid, "usuario": u["usuario"], "nome": u.get("nome", ""),
                        "role": role, "role_label": role_label(role),
                        "ativo": u.get("ativo", True),
                        "email": u.get("email", ""), "empresas": u.get("empresas", {})}
                lista.append(item)
            return self._json({"status": "ok", "users": lista, "roles": ROLES})

        if parsed.path == "/api/admin/empresas":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            empresas = load_empresas()
            lista = []
            for eid, e in empresas.items():
                item = dict(e)
                item["id"] = eid
                lista.append(item)
            return self._json({"status": "ok", "empresas": lista})

        if parsed.path == "/api/admin/permissions":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            return self._json({"status": "ok", "roles": ROLES})

        if parsed.path == "/api/admin/pos/terminais":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            data = load_pos_terminais()
            return self._json({"status": "ok", "terminais": data.get("terminais", [])})

        if parsed.path == "/api/admin/fiscal/estabelecimentos":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            empresas = load_empresas()
            store = load_estab_fiscal_store()
            lista = []
            for eid, e in empresas.items():
                merged = resolve_empresa_fiscal(eid)
                item = {
                    "id": eid,
                    "nome": e.get("nome"),
                    "cnpj_cadastro": e.get("cnpj"),
                    "ativo": e.get("ativo", True),
                    "fiscal": {
                        "csc_id": merged.get("csc_id", "1"),
                        "csc": merged.get("csc", ""),
                        "serie_nfce": int(merged.get("serie_nfce") or 1),
                        "numero_nfce": int(merged.get("numero_nfce") or 0),
                        "ambiente": int(merged.get("ambiente") or 2),
                        "certificado": merged.get("certificado", ""),
                        "cert_senha_set": bool(merged.get("cert_senha")),
                        "crt": merged.get("crt", 1),
                        "uf": merged.get("uf"),
                        "inscricao_est": merged.get("inscricao_est", ""),
                        "cod_municipio": merged.get("cod_municipio", ""),
                        "municipio": merged.get("municipio", ""),
                        "has_overlay": eid in store,
                    },
                }
                lista.append(item)
            return self._json({"status": "ok", "estabelecimentos": lista})

        if parsed.path.startswith("/api/admin/fiscal/estabelecimentos/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            eid = parsed.path.rstrip("/").split("/")[-1]
            if eid not in load_empresas():
                return self._json({"status": "error", "message": "Estabelecimento não encontrado"}, 404)
            return self._json({
                "status": "ok",
                "id": eid,
                "empresa": resolve_empresa_fiscal(eid),
                "overlay": load_estab_fiscal_store().get(eid, {}),
            })

        if parsed.path.startswith("/api/admin/pos/terminais/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            tid = parsed.path.rstrip("/").split("/")[-1]
            data = load_pos_terminais()
            for t in data.get("terminais", []):
                if t.get("id") == tid:
                    return self._json({"status": "ok", "terminal": t})
            return self._json({"status": "error", "message": "Terminal não encontrado"}, 404)

        if parsed.path == "/api/pos/contexto":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            uid = None
            for k, u in users.items():
                if u.get("token") == token:
                    uid = k
                    break
            role = (current.get("role") or "operador").lower()
            empresas = load_empresas()
            data = load_pos_terminais()
            terminais = [
                t for t in data.get("terminais", [])
                if t.get("ativo", True) and t.get("usuario_id") == uid
            ]
            # Gerente/caixa/admin no mesmo estabelecimento: listar todos os terminais da loja
            loja_ids = {t.get("estabelecimento_id") for t in terminais if t.get("estabelecimento_id")}
            visao_ampla = []
            if role in ("caixa", "gerente", "admin") and loja_ids:
                visao_ampla = [
                    t for t in data.get("terminais", [])
                    if t.get("ativo", True) and t.get("estabelecimento_id") in loja_ids
                ]
            elif role == "admin" and not terminais:
                # Admin sem terminal: contexto da matriz (demo / supervisão)
                visao_ampla = [t for t in data.get("terminais", []) if t.get("ativo", True)]

            primary = terminais[0] if terminais else None
            if not primary and role == "admin":
                # fallback estabelecimento matriz
                mid = "matriz" if "matriz" in empresas else (next(iter(empresas), None))
                estab = dict(empresas.get(mid or "", {}) or {})
                if mid:
                    estab["id"] = mid
                return self._json({
                    "status": "ok",
                    "role": role,
                    "usuario_id": uid,
                    "terminal": None,
                    "estabelecimento": estab or None,
                    "terminais": visao_ampla,
                    "modo_sugerido": "pdv",
                    "pode_trocar_modo": True,
                    "aviso": "Admin sem terminal vinculado — modo supervisão/demo",
                })

            if not primary:
                return self._json({
                    "status": "ok",
                    "role": role,
                    "usuario_id": uid,
                    "terminal": None,
                    "estabelecimento": None,
                    "terminais": [],
                    "modo_sugerido": "pdv",
                    "pode_trocar_modo": False,
                    "aviso": "Nenhum terminal ativo vinculado a este usuário. Peça ao Admin em Configurações → POS.",
                })

            eid = primary.get("estabelecimento_id")
            estab = dict(empresas.get(eid, {}) or {})
            estab["id"] = eid
            tipo = (primary.get("tipo") or "pdv").lower()
            pode_trocar = role in ("admin", "gerente") or (
                any(t.get("tipo") == "pdv" for t in terminais)
                and any(t.get("tipo") == "caixa" for t in terminais)
            )
            return self._json({
                "status": "ok",
                "role": role,
                "usuario_id": uid,
                "terminal": primary,
                "estabelecimento": estab,
                "terminais": visao_ampla if visao_ampla else terminais,
                "modo_sugerido": "caixa" if tipo == "caixa" else "pdv",
                "pode_trocar_modo": pode_trocar,
                "aviso": None,
            })

        # ── POS: leitura (qualquer usuário autenticado) ──
        if parsed.path == "/api/pos/produtos":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            estab = (qs.get("estabelecimento_id") or [""])[0].strip()
            if not estab:
                # Inferir do terminal do usuário
                users = load_users()
                current = self._find_user(token, users)
                uid = None
                for k, u in users.items():
                    if u.get("token") == token:
                        uid = k
                        break
                if uid:
                    for t in load_pos_terminais().get("terminais", []):
                        if t.get("ativo", True) and t.get("usuario_id") == uid:
                            estab = (t.get("estabelecimento_id") or "").strip()
                            break
            produtos = cobol_bridge.produtos_para_pos(estab or None)
            produtos = enriquecer_produtos_com_promise(produtos, estab or None)
            return self._json({
                "status": "ok",
                "source": "api",
                "estabelecimento_id": estab or None,
                "promise": True,
                "produtos": produtos,
            })

        if parsed.path == "/api/pos/promise":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            estab = (qs.get("estabelecimento_id") or [""])[0].strip()
            pid = (qs.get("produto_id") or [""])[0].strip()
            if not pid:
                return self._json({"status": "error", "message": "produto_id obrigatório"}, 400)
            if not estab:
                users = load_users()
                uid = next((k for k, u in users.items() if u.get("token") == token), None)
                term = _terminal_do_usuario(uid)
                if term:
                    estab = (term.get("estabelecimento_id") or "").strip()
            prom = promise_produto(estab, pid)
            return self._json({
                "status": "ok",
                "estabelecimento_id": estab or None,
                "produto_id": pid,
                **prom,
            })

        if parsed.path == "/api/inventory/balance":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            estab = (qs.get("estabelecimento_id") or [""])[0].strip()
            pid = (qs.get("produto_id") or [""])[0].strip()
            balances = inventory_mvp.load_balances()
            if not estab:
                return self._json({
                    "status": "ok",
                    "por_estabelecimento": balances.get("por_estabelecimento") or {},
                    "atualizado_em": balances.get("atualizado_em"),
                })
            if pid:
                return self._json({
                    "status": "ok",
                    "estabelecimento_id": estab,
                    "produto_id": pid,
                    "balance": inventory_mvp.inventory_balance(estab, pid, balances=balances),
                })
            loja = (balances.get("por_estabelecimento") or {}).get(estab) or {}
            return self._json({
                "status": "ok",
                "estabelecimento_id": estab,
                "balances": loja,
            })

        if parsed.path == "/api/inventory/movements":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                limit = int((qs.get("limit") or ["50"])[0])
            except (TypeError, ValueError):
                limit = 50
            estab = (qs.get("estabelecimento_id") or [""])[0].strip() or None
            pid = (qs.get("produto_id") or [""])[0].strip() or None
            rows = inventory_mvp.list_recent_movements(limit=limit, estabelecimento_id=estab, produto_id=pid)
            return self._json({"status": "ok", "movements": rows, "total": len(rows)})

        if parsed.path == "/api/inventory/transit":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            itens = [
                t for t in (inventory_mvp.load_transit().get("itens") or [])
                if t.get("status") == "open"
            ]
            return self._json({"status": "ok", "itens": itens})

        if parsed.path == "/api/receiving":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            estab = (qs.get("estabelecimento_id") or [""])[0].strip() or None
            status = (qs.get("status") or [""])[0].strip() or None
            rows = receiving_mvp.list_receivings(estabelecimento_id=estab, status=status)
            return self._json({"status": "ok", "receivings": rows, "total": len(rows)})

        if parsed.path.startswith("/api/receiving/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            rid = parsed.path.rstrip("/").split("/")[-1]
            if rid in ("verify", "complete", "cancel"):
                return self._json({"status": "error", "message": "id obrigatório"}, 400)
            rec = receiving_mvp.get_receiving(rid)
            if not rec:
                return self._json({"status": "error", "message": "Recebimento não encontrado"}, 404)
            return self._json({"status": "ok", "receiving": rec})

        if parsed.path == "/api/pos/parceiros":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            data = load_json(PARTNERS_FILE)
            role_filter = self._get_query_param(parsed.query, "role", "CUSTOMER").upper().strip()
            lista = []
            for eid, e in data.items():
                item = dict(e)
                item["id"] = eid
                if item.get("ativo") is False or str(item.get("status", "")).upper() == "INACTIVE":
                    continue
                roles = [str(r).upper() for r in (item.get("roles") or [])]
                if role_filter and role_filter not in roles:
                    continue
                lista.append(item)
            return self._json({"status": "ok", "source": "api", "parceiros": lista})

        # ── POS: fila PDV → Caixa ──
        if parsed.path == "/api/pos/fila":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            fila = load_pos_fila()
            pid = self._get_query_param(parsed.query, "id", "").strip()
            if pid:
                hit = next((p for p in fila["pedidos"] if str(p.get("id")) == pid), None)
                if not hit:
                    return self._json({"status": "error", "message": "Pedido não encontrado"}, 404)
                return self._json({"status": "ok", "pedido": hit})
            states_raw = self._get_query_param(parsed.query, "state", "aguardando,pagamento")
            states = {s.strip().lower() for s in states_raw.split(",") if s.strip()}
            pedidos = [p for p in fila["pedidos"] if str(p.get("state", "")).lower() in states]
            pedidos.sort(key=lambda p: p.get("createdAt") or "", reverse=True)
            return self._json({"status": "ok", "pedidos": pedidos, "next_num": fila.get("next_num")})

        # ── COBOL: Produtos ──
        if parsed.path == "/api/admin/produtos":
            token = self.headers.get("X-Auth-Token", "")
            if not self._is_admin(token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            return self._json({"status": "ok", "produtos": cobol_bridge.produtos_listar()})

        if parsed.path == "/api/admin/produtos/sync":
            token = self.headers.get("X-Auth-Token", "")
            if not self._is_admin(token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            return self._json({"status": "ok", **cobol_bridge.sync_json()})

        # ── COBOL: Fornecedores ──
        if parsed.path == "/api/admin/fornecedores":
            token = self.headers.get("X-Auth-Token", "")
            if not self._is_admin(token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            return self._json({"status": "ok", "fornecedores": cobol_bridge.fornecedores_listar()})

        # ── Certificados ──
        if parsed.path == "/api/admin/certificados":
            token = self.headers.get("X-Auth-Token", "")
            if not self._is_admin(token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            return self._json({"status": "ok", "certificados": cert_service.listar()})

        if parsed.path.startswith("/api/admin/certificados/") and parsed.path.count("/") == 4:
            token = self.headers.get("X-Auth-Token", "")
            if not self._is_admin(token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            cid = parsed.path.split("/")[-1]
            action = body.get("action", "") if self.command == "POST" else ""
            if parsed.path.endswith("/info"):
                cid = parsed.path.split("/")[-2]
                info = cert_service.info_detalhada(cid)
                if not info:
                    return self._json({"status": "error", "message": "Certificado não encontrado"}, 404)
                return self._json({"status": "ok", "certificado": info})
            # GET single cert
            cert = cert_service.obter(cid)
            if not cert:
                return self._json({"status": "error", "message": "Certificado não encontrado"}, 404)
            return self._json({"status": "ok", "certificado": cert})

        # ── Fiscal: NFC-e ──
        # ── Lookup NCM / CEST (RFC 0012 + 0013) ──
        if parsed.path == "/api/lookup/ncm":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            q = self._get_query_param(parsed.query, "q", "")
            limit = int(self._get_query_param(parsed.query, "limit", "20") or "20")
            return self._json({"status": "ok", "items": ncm_cest_service.search_ncm(q, limit)})

        if parsed.path.startswith("/api/lookup/ncm/") and parsed.path.endswith("/cest"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            codigo = parsed.path.split("/")[4]
            autofill = ncm_cest_service.resolve_cest_autofill(codigo)
            return self._json({"status": "ok", "ncm": ncm_cest_service.get_ncm(codigo), **autofill})

        if parsed.path.startswith("/api/lookup/ncm/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            codigo = parsed.path.rstrip("/").split("/")[-1]
            item = ncm_cest_service.get_ncm(codigo)
            if not item:
                return self._json({"status": "error", "message": "NCM não encontrado"}, 404)
            return self._json({"status": "ok", "item": item})

        if parsed.path == "/api/lookup/cest":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            q = self._get_query_param(parsed.query, "q", "")
            ncm = self._get_query_param(parsed.query, "ncm", "") or None
            limit = int(self._get_query_param(parsed.query, "limit", "20") or "20")
            return self._json({"status": "ok", "items": ncm_cest_service.search_cest(q, limit, ncm=ncm)})

        if parsed.path == "/api/lookup/ncm-cest/validate":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            ncm = self._get_query_param(parsed.query, "ncm", "")
            cest = self._get_query_param(parsed.query, "cest", "")
            result = ncm_cest_service.validate_ncm_cest(ncm, cest)
            return self._json({"status": "ok" if result.get("ok") else "error", **result})

        # ── Vendas B2B (CNPJ → CNPJ) ──
        if parsed.path == "/api/vendas/b2b":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            pedidos = load_json(os.path.join(BASE_DIR, "dados", "pedidos_b2b.json"))
            return self._json({"status": "ok", **pedidos})

        # ── Vendas (para NFC-e) ──
        if parsed.path == "/api/vendas":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            cobol_bridge.sync_json()
            vendas = load_json(os.path.join(BASE_DIR, "dados", "vendas.json"))
            return self._json(vendas)

        if parsed.path == "/api/admin/fiscal/nfce/listar":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "nfce"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            nfce_data = load_json(os.path.join(BASE_DIR, "dados", "nfce.json"))
            return self._json({"status": "ok", "nfce": nfce_data.get("nfce", [])})

        if parsed.path == "/api/admin/fiscal/nfce/empresa":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "nfce"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            emp = load_empresa_fiscal()
            certs = cert_service.listar()
            return self._json({"status": "ok", "empresa": emp, "certificados": certs})

        # ── Fiscal: NF-e (modelo 55) ──
        if parsed.path == "/api/admin/fiscal/nfe/listar":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(crud_token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            nfe_data = load_json(os.path.join(BASE_DIR, "dados", "nfe.json"))
            return self._json({"status": "ok", "nfe": nfe_data.get("nfe", [])})

        if parsed.path == "/api/admin/fiscal/nfe/empresa":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            emp = load_empresa_fiscal()
            certs = cert_service.listar()
            return self._json({"status": "ok", "empresa": emp, "certificados": certs})

        # ── Fiscal: NFS-e ──
        if parsed.path == "/api/admin/fiscal/nfse/listar":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "nfse"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            nfse_data = load_json(os.path.join(BASE_DIR, "dados", "nfse.json"))
            return self._json({"status": "ok", "nfse": nfse_data.get("nfse", [])})

        if parsed.path == "/api/admin/fiscal/nfse/empresa":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "nfse"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            emp = load_empresa_fiscal()
            certs = cert_service.listar()
            return self._json({"status": "ok", "empresa": emp, "certificados": certs})

        if parsed.path == "/api/admin/fiscal/nfse/cidades":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "nfse"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            return self._json({"status": "ok", "cidades": nfse_service.CIDADES_NFSE})

        # ── SPED ──
        if parsed.path == "/api/admin/fiscal/sped/fiscal":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "sped"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            empresa = load_empresa_fiscal()
            nfce = load_json(os.path.join(BASE_DIR, "dados", "nfce.json")).get("nfce", [])
            nfe = load_json(os.path.join(BASE_DIR, "dados", "nfe.json")).get("nfe", [])
            conteudo = sped_fiscal.gerar_sped_fiscal(empresa, nfce_list=nfce, nfe_list=nfe)
            return self._json({"status": "ok", "conteudo": conteudo, "filename": f"SPED_FISCAL_{empresa.get('cnpj','')}.txt"})

        if parsed.path == "/api/admin/fiscal/sped/pis":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "sped"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            empresa = load_empresa_fiscal()
            nfce = load_json(os.path.join(BASE_DIR, "dados", "nfce.json")).get("nfce", [])
            nfe = load_json(os.path.join(BASE_DIR, "dados", "nfe.json")).get("nfe", [])
            conteudo = sped_pis_cofins.gerar_sped_pis(empresa, nfce_list=nfce, nfe_list=nfe)
            return self._json({"status": "ok", "conteudo": conteudo, "filename": f"SPED_PIS_{empresa.get('cnpj','')}.txt"})

        # ── CT-e (COBOL) ──
        if parsed.path == "/api/admin/fiscal/cte":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            return self._json({"status": "ok", "cte": cobol_bridge.cte_listar()})

        # ── MDF-e (COBOL) ──
        if parsed.path == "/api/admin/fiscal/mdfe":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            return self._json({"status": "ok", "mdfe": cobol_bridge.mdfe_listar()})

        # ── Tributos ──
        if parsed.path == "/api/admin/fiscal/calcular-tributos":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            uf_origem = self._get_query_param(parsed.query, "uf_origem", "RS")
            uf_destino = self._get_query_param(parsed.query, "uf_destino", "RS")
            regime = self._get_query_param(parsed.query, "regime", "SN")
            regime_pis = self._get_query_param(parsed.query, "regime_pis", "cumulativo")
            return self._json({"status": "ok", "tabelas": {
                "icms_interno": tributos.TABELA_ICMS_INTERNO,
                "icms_interestadual": tributos.TABELA_ICMS_INTERESTADUAL,
                "pis": tributos.TABELA_PIS,
                "cofins": tributos.TABELA_COFINS,
                "ipi": tributos.TABELA_IPI,
                "iss": tributos.TABELA_ISS,
            }})

        # CRUD GET routes (JSON)
        for prefix, data_file, list_key in [
            ("/api/admin/categorias", CATEGORIAS_FILE, "categorias"),
            ("/api/admin/marcas", MARCAS_FILE, "marcas"),
            ("/api/admin/fabricantes", FABRICANTES_FILE, "fabricantes"),
            ("/api/admin/contatos", CONTATOS_FILE, "contatos"),
            ("/api/admin/partners", PARTNERS_FILE, "partners"),
        ]:
            if parsed.path == prefix:
                token = self.headers.get("X-Auth-Token", "")
                if not self._is_admin(token):
                    return self._json({"status": "error", "message": "Acesso negado"}, 403)
                data = load_json(data_file)
                lista = []
                role_filter = self._get_query_param(parsed.query, "role", "").upper().strip()
                for eid, e in data.items():
                    item = dict(e)
                    item["id"] = eid
                    if role_filter:
                        roles = [str(r).upper() for r in (item.get("roles") or [])]
                        # legado contatos: tipo=cliente
                        if list_key == "contatos" and not roles:
                            t = (item.get("tipo") or "").lower()
                            tipo_map = {
                                "cliente": "CUSTOMER",
                                "fornecedor": "SUPPLIER",
                                "transportador": "CARRIER",
                            }
                            if tipo_map.get(t):
                                roles = [tipo_map[t]]
                        if role_filter not in roles:
                            continue
                    lista.append(item)
                return self._json({"status": "ok", list_key: lista})

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode() if length else ""
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = {}

        if parsed.path == "/api/auth/setup":
            users = load_users()
            if any(u.get("role") == "admin" for u in users.values()):
                return self._json({"status": "error", "message": "Admin já configurado"}, 400)
            nome = body.get("nome", "").strip()
            usuario = body.get("usuario", "").strip()
            senha = body.get("senha", "")
            email = body.get("email", "").strip()
            if not nome or not usuario or not senha:
                return self._json({"status": "error", "message": "Preencha nome, usuário e senha"}, 400)
            uid = str(uuid.uuid4())[:8]
            token = make_token()
            users[uid] = {
                "usuario": usuario,
                "nome": nome,
                "senha": hash_password(senha),
                "email": email or "",
                "role": "admin",
                "empresas": {},
                "ativo": True,
                "token": token
            }
            save_users(users)
            return self._json({"status": "ok", "id": uid, "token": token, "nome": nome, "usuario": usuario, "role": "admin"})

        # ── Inventory MVP: transfer / adjust ──
        if parsed.path in ("/api/inventory/transfer", "/api/inventory/adjust"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            uid = next((k for k, u in users.items() if u.get("token") == token), None)
            try:
                if parsed.path == "/api/inventory/transfer":
                    result = inventory_mvp.inventory_transfer(
                        body.get("origem") or body.get("from"),
                        body.get("destino") or body.get("to"),
                        body.get("items") or body.get("linhas") or [],
                        user_id=uid,
                        nota=body.get("nota"),
                    )
                    return self._json({"status": "ok", **result})
                # adjust
                result = inventory_mvp.inventory_adjust(
                    body.get("estabelecimento_id") or body.get("warehouse_id"),
                    body.get("produto_id") or body.get("id"),
                    body.get("qty") or body.get("quantidade"),
                    direcao=body.get("direcao") or body.get("sign") or "in",
                    nota=body.get("nota"),
                    user_id=uid,
                )
                return self._json({"status": "ok", **result})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── Receiving MVP ──
        if parsed.path == "/api/receiving" or parsed.path.startswith("/api/receiving/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            uid = next((k for k, u in users.items() if u.get("token") == token), None)

            if parsed.path == "/api/receiving":
                try:
                    rec = receiving_mvp.create_receiving(body, user_id=uid)
                    return self._json({"status": "ok", "receiving": rec}, 201)
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)

            parts = parsed.path.rstrip("/").split("/")
            # /api/receiving/{id}/{action?}
            if len(parts) < 4:
                return self._json({"status": "error", "message": "Rota inválida"}, 400)
            rid = parts[3]
            action = parts[4] if len(parts) > 4 else (body.get("action") or "update")
            try:
                if action == "verify":
                    rec = receiving_mvp.verify_receiving(rid, body, user_id=uid)
                elif action == "complete":
                    auto = bool(body.get("auto_verify"))
                    rec = receiving_mvp.complete_receiving(rid, user_id=uid, auto_verify=auto)
                elif action == "cancel":
                    rec = receiving_mvp.cancel_receiving(rid, user_id=uid, motivo=body.get("motivo"))
                else:
                    return self._json({"status": "error", "message": f"ação desconhecida: {action}"}, 400)
                return self._json({"status": "ok", "receiving": rec})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── POS: criar pedido na fila ──
        if parsed.path == "/api/pos/fila":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            lines = body.get("lines") or []
            if not isinstance(lines, list) or not lines:
                return self._json({"status": "error", "message": "Pedido sem itens"}, 400)
            if body.get("training"):
                return self._json({"status": "error", "message": "Treino não grava na fila"}, 400)
            total = _safe_float(body.get("total"), 0)
            if total <= 0:
                return self._json({"status": "error", "message": "Total inválido"}, 400)
            fila = load_pos_fila()
            order_num = int(fila.get("next_num") or 1000)
            fila["next_num"] = order_num + 1
            now = datetime.now().isoformat(timespec="seconds")
            client = body.get("client") if isinstance(body.get("client"), dict) else {}
            pdv_uid = next(
                    (uid for uid, u in users.items() if u.get("token") == token),
                    "",
                )
            term = _terminal_do_usuario(pdv_uid)
            estab_id = (body.get("estabelecimento_id") or "").strip()
            term_id = (body.get("terminal_id") or "").strip()
            if term:
                if not estab_id:
                    estab_id = (term.get("estabelecimento_id") or "").strip()
                if not term_id:
                    term_id = term.get("id") or ""
            pedido = {
                "id": str(uuid.uuid4())[:12],
                "orderNum": order_num,
                "state": "aguardando",
                "training": False,
                "createdAt": now,
                "updatedAt": now,
                "pdvUser": user.get("nome") or user.get("usuario") or "",
                "pdvUserId": pdv_uid,
                "estabelecimento_id": estab_id,
                "terminal_id": term_id,
                "sessionId": body.get("sessionId") or "",
                "client": {
                    "id": client.get("id") or "cf",
                    "nome": client.get("nome") or "Consumidor final",
                    "av": client.get("av") or "CF",
                    "cpf": client.get("cpf") or "",
                    "hint": client.get("hint") or "",
                },
                "lines": lines,
                "subtotal": _safe_float(body.get("subtotal"), 0),
                "discount": _safe_float(body.get("discount"), 0),
                "surcharge": _safe_float(body.get("surcharge"), 0),
                "promo": _safe_float(body.get("promo"), 0),
                "total": round(total, 2),
                "orderDisc": body.get("orderDisc") or {"type": "val", "value": 0},
                "orderAcr": body.get("orderAcr") or {"type": "val", "value": 0},
                "orderParc": body.get("orderParc"),
            }
            fila["pedidos"].append(pedido)
            # mantém no máximo 200 pedidos no arquivo
            if len(fila["pedidos"]) > 200:
                fila["pedidos"] = fila["pedidos"][-200:]
            save_pos_fila(fila)
            return self._json({"status": "ok", "pedido": pedido})

        if parsed.path.startswith("/api/pos/fila/"):
            token = self.headers.get("X-Auth-Token", "")
            user = self._find_user(token, load_users())
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            pid = parsed.path.rstrip("/").split("/")[-1]
            fila = load_pos_fila()
            pedido = next((p for p in fila["pedidos"] if str(p.get("id")) == pid), None)
            if not pedido:
                return self._json({"status": "error", "message": "Pedido não encontrado"}, 404)
            action = (body.get("action") or "").strip().lower()

            if action == "finalizar":
                cur = str(pedido.get("state") or "aguardando").lower()
                if cur == "pago":
                    return self._json({
                        "status": "ok",
                        "pedido": pedido,
                        "nfce": pedido.get("nfce"),
                        "message": "Pedido já estava pago",
                    })
                if cur == "cancelado":
                    return self._json({"status": "error", "message": "Pedido cancelado"}, 400)

                forma_pg = (body.get("forma_pg") or pedido.get("forma_pg") or "Dinheiro").strip()
                emitir = body.get("emitir_nfce", True)
                if isinstance(emitir, str):
                    emitir = emitir.lower() not in ("0", "false", "nao", "não", "no")

                pedido["state"] = "pagamento"
                pedido["forma_pg"] = forma_pg
                pedido["caixaUser"] = user.get("nome") or user.get("usuario") or ""
                pedido["updatedAt"] = datetime.now().isoformat(timespec="seconds")

                venda = _pedido_para_venda(pedido, forma_pg)
                vendas_path = os.path.join(BASE_DIR, "dados", "vendas.json")
                vendas_data = load_json(vendas_path)
                if not isinstance(vendas_data, dict):
                    vendas_data = {"vendas": [], "total_vendas": 0}
                lista_v = vendas_data.get("vendas") or []
                # id numérico sequencial para compat com tela NFC-e
                try:
                    next_vid = max([int(v.get("id") or 0) for v in lista_v] or [0]) + 1
                except Exception:
                    next_vid = len(lista_v) + 1
                venda["id"] = next_vid
                lista_v.append(venda)
                vendas_data["vendas"] = lista_v
                vendas_data["total_vendas"] = len(lista_v)
                save_json(vendas_path, vendas_data)
                pedido["venda_id"] = next_vid

                # Inventário MVP: movimento sale (ledger)
                try:
                    baixar_estoque_local(
                        pedido.get("estabelecimento_id"),
                        pedido.get("lines") or [],
                        venda_id=next_vid,
                    )
                except Exception:
                    pass

                nfce_out = None
                aviso = ""
                if emitir:
                    estab_id = (pedido.get("estabelecimento_id") or body.get("estabelecimento_id") or "").strip()
                    if not estab_id:
                        # fallback: terminal do caixa logado
                        caixa_uid = next(
                            (uid for uid, u in load_users().items() if u.get("token") == token),
                            "",
                        )
                        term_cx = _terminal_do_usuario(caixa_uid)
                        if term_cx:
                            estab_id = (term_cx.get("estabelecimento_id") or "").strip()
                    empresa = resolve_empresa_fiscal(estab_id or None)
                    csc = str(empresa.get("csc") or "").strip()
                    if not csc or "ALTERAR" in csc.upper() or csc == "HOMOLOGACAO-CSC-ALTERAR":
                        aviso = (
                            f"CSC não configurado para o estabelecimento "
                            f"'{estab_id or 'legado'}' (Configurações → Fiscal)."
                        )
                    cert_id = _resolve_cert_id(empresa, body.get("cert_id", ""))
                    cert_senha = body.get("cert_senha") or empresa.get("cert_senha") or ""
                    ambiente = int(body.get("ambiente", empresa.get("ambiente", 2) or 2))
                    serie = int(body.get("serie", empresa.get("serie_nfce", 1) or 1))
                    if not cert_id:
                        aviso = (aviso + " " if aviso else "") + "Nenhum certificado válido no índice."
                    elif not cert_senha:
                        aviso = (aviso + " " if aviso else "") + "Senha do certificado ausente."
                    else:
                        try:
                            nfce_out = _autorizar_nfce_de_venda(
                                venda, empresa, cert_id, cert_senha, ambiente=ambiente, serie=serie
                            )
                            pedido["nfce"] = {
                                "numero": nfce_out.get("numero"),
                                "serie": nfce_out.get("serie"),
                                "chave": nfce_out.get("chave"),
                                "estabelecimento_id": estab_id,
                                "cStat": (nfce_out.get("resultado") or {}).get("cStat"),
                                "xMotivo": (nfce_out.get("resultado") or {}).get("xMotivo"),
                                "status": (nfce_out.get("resultado") or {}).get("status"),
                                "protocolo": (nfce_out.get("resultado") or {}).get(
                                    "nProt", (nfce_out.get("resultado") or {}).get("protocolo", "")
                                ),
                                "ambiente": ambiente,
                            }
                        except Exception as e:
                            aviso = (aviso + " " if aviso else "") + f"Falha NFC-e: {e}"
                            pedido["nfce"] = {"status": "ERRO", "xMotivo": str(e), "estabelecimento_id": estab_id}

                pedido["state"] = "pago"
                pedido["updatedAt"] = datetime.now().isoformat(timespec="seconds")
                save_pos_fila(fila)
                return self._json({
                    "status": "ok",
                    "pedido": pedido,
                    "venda_id": next_vid,
                    "nfce": nfce_out,
                    "aviso": aviso.strip(),
                })

            if action != "status":
                return self._json({"status": "error", "message": "Ação inválida"}, 400)
            new_state = str(body.get("state") or "").strip().lower()
            allowed = {
                "aguardando": {"pagamento", "cancelado"},
                "pagamento": {"pago", "aguardando", "cancelado"},
                "pago": set(),
                "cancelado": set(),
            }
            cur = str(pedido.get("state") or "aguardando").lower()
            if new_state not in allowed.get(cur, set()) and new_state != cur:
                return self._json(
                    {
                        "status": "error",
                        "message": f"Transição inválida: {cur} → {new_state}",
                    },
                    400,
                )
            pedido["state"] = new_state
            pedido["updatedAt"] = datetime.now().isoformat(timespec="seconds")
            pedido["caixaUser"] = user.get("nome") or user.get("usuario") or ""
            save_pos_fila(fila)
            return self._json({"status": "ok", "pedido": pedido})

        if parsed.path == "/api/auth/login":
            usuario = body.get("usuario", "").strip()
            senha = body.get("senha", "")
            users = load_users()
            for uid, u in users.items():
                if u["usuario"] == usuario and u["senha"] == hash_password(senha):
                    if not u.get("ativo", True):
                        return self._json({"status": "error", "message": "Usuário desativado"}, 403)
                    u["token"] = make_token()
                    save_users(users)
                    return self._json({
                        "status": "ok", "token": u["token"],
                        "nome": u["nome"], "usuario": u["usuario"],
                        "role": u.get("role", "operador"), "id": uid,
                        "empresas": user_empresas(u)
                    })
            return self._json({"status": "error", "message": "Usuário ou senha incorretos"}, 401)

        if parsed.path == "/api/admin/users":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            usuario = body.get("usuario", "").strip()
            nome = body.get("nome", "").strip()
            senha = body.get("senha", "")
            role = body.get("role", "vendedor")
            if role not in ROLE_IDS:
                return self._json({"status": "error", "message": f"Perfil inválido: {role}"}, 400)
            empresas = body.get("empresas", {})
            if not usuario or not nome or not senha:
                return self._json({"status": "error", "message": "Preencha todos os campos"}, 400)
            for uid, u in users.items():
                if u["usuario"] == usuario:
                    return self._json({"status": "error", "message": "Usuário já existe"}, 400)
            uid = str(uuid.uuid4())[:8]
            users[uid] = {
                "usuario": usuario,
                "nome": nome,
                "senha": hash_password(senha),
                "email": body.get("email", ""),
                "role": role,
                "empresas": empresas,
                "ativo": True,
                "token": ""
            }
            save_users(users)
            return self._json({"status": "ok", "id": uid, "message": "Usuário criado"})

        if parsed.path.startswith("/api/admin/users/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            uid = parsed.path.split("/")[-1]
            if uid not in users:
                return self._json({"status": "error", "message": "Usuário não encontrado"}, 404)
            if body.get("action") == "toggle":
                users[uid]["ativo"] = not users[uid].get("ativo", True)
                save_users(users)
                return self._json({"status": "ok", "ativo": users[uid]["ativo"]})
            if body.get("action") == "delete" and uid != list(users.keys())[0]:
                del users[uid]
                save_users(users)
                return self._json({"status": "ok", "message": "Usuário removido"})
            if body.get("action") == "update":
                if body.get("nome"): users[uid]["nome"] = body["nome"]
                if body.get("role"):
                    if body["role"] not in ROLE_IDS:
                        return self._json({"status": "error", "message": f"Perfil inválido: {body['role']}"}, 400)
                    users[uid]["role"] = body["role"]
                if body.get("senha"): users[uid]["senha"] = hash_password(body["senha"])
                if "empresas" in body:
                    users[uid]["empresas"] = body["empresas"]
                if "email" in body:
                    users[uid]["email"] = body.get("email") or ""
                save_users(users)
                return self._json({"status": "ok", "message": "Usuário atualizado"})

        if parsed.path == "/api/admin/empresas":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            nome = body.get("nome", "").strip()
            cnpj = body.get("cnpj", "").strip()
            if not nome:
                return self._json({"status": "error", "message": "Nome é obrigatório"}, 400)
            empresas = load_empresas()
            eid = str(uuid.uuid4())[:8]
            empresas[eid] = {
                "nome": nome,
                "cnpj": cnpj,
                "ie": body.get("ie", ""),
                "cidade": body.get("cidade", ""),
                "uf": body.get("uf", ""),
                "ativo": True
            }
            save_empresas(empresas)
            return self._json({"status": "ok", "id": eid, "message": "Empresa criada"})

        if parsed.path.startswith("/api/admin/empresas/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            eid = parsed.path.split("/")[-1]
            empresas = load_empresas()
            if eid not in empresas:
                return self._json({"status": "error", "message": "Empresa não encontrada"}, 404)
            if body.get("action") == "toggle":
                empresas[eid]["ativo"] = not empresas[eid].get("ativo", True)
                save_empresas(empresas)
                return self._json({"status": "ok", "ativo": empresas[eid]["ativo"]})
            if body.get("action") == "update":
                if body.get("nome"): empresas[eid]["nome"] = body["nome"]
                if body.get("cnpj") is not None: empresas[eid]["cnpj"] = body["cnpj"]
                if body.get("ie") is not None: empresas[eid]["ie"] = body["ie"]
                if body.get("cidade") is not None: empresas[eid]["cidade"] = body["cidade"]
                if body.get("uf") is not None: empresas[eid]["uf"] = body["uf"]
                save_empresas(empresas)
                return self._json({"status": "ok", "message": "Empresa atualizada"})

        if parsed.path.startswith("/api/admin/fiscal/estabelecimentos/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            eid = parsed.path.rstrip("/").split("/")[-1]
            if eid not in load_empresas():
                return self._json({"status": "error", "message": "Estabelecimento não encontrado"}, 404)
            store = load_estab_fiscal_store()
            entry = dict(store.get(eid) or {})
            fields = (
                "csc", "csc_id", "serie_nfce", "numero_nfce", "ambiente",
                "certificado", "cert_senha", "crt", "uf", "inscricao_est",
                "cod_municipio", "municipio", "nome", "nome_fantasia", "cnpj",
                "endereco", "cep", "telefone", "email", "tipo_fiscal",
            )
            for f in fields:
                if f in body:
                    entry[f] = body[f]
            if "serie_nfce" in entry:
                entry["serie_nfce"] = int(entry.get("serie_nfce") or 1)
            if "numero_nfce" in entry:
                entry["numero_nfce"] = int(entry.get("numero_nfce") or 0)
            if "ambiente" in entry:
                entry["ambiente"] = int(entry.get("ambiente") or 2)
            if entry.get("cnpj"):
                entry["cnpj"] = _digits(entry["cnpj"])
            store[eid] = entry
            save_estab_fiscal_store(store)
            return self._json({
                "status": "ok",
                "id": eid,
                "overlay": entry,
                "empresa": resolve_empresa_fiscal(eid),
                "message": "Fiscal do estabelecimento salvo",
            })

        if parsed.path == "/api/admin/pos/terminais":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            tipo = (body.get("tipo") or "").strip().lower()
            codigo = (body.get("codigo") or "").strip().upper()
            nome = (body.get("nome") or "").strip()
            estabelecimento_id = (body.get("estabelecimento_id") or "").strip()
            usuario_id = (body.get("usuario_id") or "").strip()
            if tipo not in ("pdv", "caixa"):
                return self._json({"status": "error", "message": "Tipo deve ser pdv ou caixa"}, 400)
            if not codigo or not nome or not estabelecimento_id:
                return self._json({"status": "error", "message": "Código, nome e estabelecimento são obrigatórios"}, 400)
            if not usuario_id:
                return self._json({"status": "error", "message": "Vínculo com usuário é obrigatório"}, 400)
            if usuario_id not in users:
                return self._json({"status": "error", "message": "Usuário não encontrado"}, 400)
            data = load_pos_terminais()
            terminais = data.get("terminais", [])
            if any(t.get("codigo", "").upper() == codigo for t in terminais):
                return self._json({"status": "error", "message": "Código de terminal já existe"}, 400)
            if tipo == "pdv":
                conflict = _pdv_user_conflict(terminais, usuario_id)
                if conflict:
                    return self._json({
                        "status": "error",
                        "message": f"Vendedor já vinculado ao PDV {conflict.get('codigo')} (relação 1:1)"
                    }, 400)
            tid = "t-" + str(uuid.uuid4())[:8]
            terminal = {
                "id": tid,
                "tipo": tipo,
                "codigo": codigo,
                "nome": nome,
                "estabelecimento_id": estabelecimento_id,
                "usuario_id": usuario_id,
                "usuario_nome": users[usuario_id].get("nome", ""),
                "ativo": True,
                "treino": bool(body.get("treino", True)),
                "impressora": (body.get("impressora") or "").strip(),
                "balanca": (body.get("balanca") or ("mock" if tipo == "pdv" else "nenhuma")).strip(),
                "timeout_min": int(body.get("timeout_min") or 30),
                "emite_nfce": bool(body.get("emite_nfce", tipo == "caixa")),
                "criado_em": datetime.now().isoformat(timespec="seconds"),
            }
            terminais.append(terminal)
            data["terminais"] = terminais
            save_pos_terminais(data)
            return self._json({"status": "ok", "id": tid, "terminal": terminal, "message": "Terminal criado"})

        if parsed.path.startswith("/api/admin/pos/terminais/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            tid = parsed.path.rstrip("/").split("/")[-1]
            data = load_pos_terminais()
            terminais = data.get("terminais", [])
            idx = next((i for i, t in enumerate(terminais) if t.get("id") == tid), None)
            if idx is None:
                return self._json({"status": "error", "message": "Terminal não encontrado"}, 404)
            action = body.get("action") or "update"
            if action == "delete":
                terminais.pop(idx)
                data["terminais"] = terminais
                save_pos_terminais(data)
                return self._json({"status": "ok", "message": "Terminal removido"})
            if action == "toggle":
                terminais[idx]["ativo"] = not terminais[idx].get("ativo", True)
                data["terminais"] = terminais
                save_pos_terminais(data)
                return self._json({"status": "ok", "ativo": terminais[idx]["ativo"], "terminal": terminais[idx]})
            # update / reassign
            t = terminais[idx]
            if body.get("nome") is not None:
                t["nome"] = str(body.get("nome") or "").strip() or t["nome"]
            if body.get("estabelecimento_id"):
                t["estabelecimento_id"] = str(body["estabelecimento_id"]).strip()
            if "treino" in body:
                t["treino"] = bool(body["treino"])
            if "impressora" in body:
                t["impressora"] = str(body.get("impressora") or "").strip()
            if "balanca" in body:
                t["balanca"] = str(body.get("balanca") or "").strip()
            if "timeout_min" in body:
                t["timeout_min"] = int(body.get("timeout_min") or 30)
            if "emite_nfce" in body:
                t["emite_nfce"] = bool(body["emite_nfce"])
            if "ativo" in body:
                t["ativo"] = bool(body["ativo"])
            if body.get("usuario_id"):
                uid = str(body["usuario_id"]).strip()
                if uid not in users:
                    return self._json({"status": "error", "message": "Usuário não encontrado"}, 400)
                if t.get("tipo") == "pdv":
                    conflict = _pdv_user_conflict(terminais, uid, exclude_id=tid)
                    if conflict:
                        return self._json({
                            "status": "error",
                            "message": f"Vendedor já vinculado ao PDV {conflict.get('codigo')} (relação 1:1)"
                        }, 400)
                t["usuario_id"] = uid
                t["usuario_nome"] = users[uid].get("nome", "")
            terminais[idx] = t
            data["terminais"] = terminais
            save_pos_terminais(data)
            return self._json({"status": "ok", "terminal": t, "message": "Terminal atualizado"})

        crud_token = self.headers.get("X-Auth-Token", "")

        # ── COBOL: Produtos (POST) ──
        if parsed.path == "/api/admin/produtos":
            if not self._is_admin(crud_token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                pid = cobol_bridge.produtos_incluir(body)
                return self._json({"status": "ok", "id": pid, "message": "Produto criado"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/produtos/"):
            if not self._is_admin(crud_token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            eid = parsed.path.split("/")[-1]
            if eid == "sync":
                return self._json({"status": "ok", **cobol_bridge.sync_json()})
            if eid == "migrate-extras":
                n = cobol_bridge.produtos_extra_import(body.get("extras") or {}, overwrite=False)
                return self._json({"status": "ok", "imported": n, "message": f"{n} extras importados"})
            try:
                pid = int(eid)
                if body.get("action") == "toggle":
                    cobol_bridge.produtos_alterar(pid, {"ativo": ""})
                    return self._json({"status": "ok", "message": "Toggle não suportado via COBOL"})
                if body.get("action") == "update":
                    cobol_bridge.produtos_alterar(pid, body)
                    return self._json({"status": "ok", "message": "Produto atualizado"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── COBOL: Fornecedores (POST) ──
        if parsed.path == "/api/admin/fornecedores":
            if not self._is_admin(crud_token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                fid = cobol_bridge.fornecedores_incluir(body)
                return self._json({"status": "ok", "id": fid, "message": "Fornecedor criado"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/fornecedores/"):
            if not self._is_admin(crud_token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            eid = parsed.path.split("/")[-1]
            try:
                fid = int(eid)
                if body.get("action") == "toggle":
                    cobol_bridge.fornecedores_alterar(fid, {"nome": ""})
                    return self._json({"status": "ok", "message": "Fornecedor atualizado"})
                if body.get("action") == "update":
                    cobol_bridge.fornecedores_alterar(fid, body)
                    return self._json({"status": "ok", "message": "Fornecedor atualizado"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── Certificados (POST) ──
        if parsed.path == "/api/admin/certificados/upload":
            if not self._is_admin(crud_token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                pfx_b64 = body.get("arquivo", "")
                senha = body.get("senha", "")
                nome = body.get("nome_arquivo", "certificado.pfx")
                import base64
                pfx_data = base64.b64decode(pfx_b64)
                result = cert_service.upload(pfx_data, senha, nome)
                return self._json({"status": "ok", "certificado": result, "message": "Certificado importado"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/certificados/") and parsed.path != "/api/admin/certificados/upload":
            parts = parsed.path.rstrip("/").split("/")
            # parts = ['', 'api', 'admin', 'certificados', '<id>', ...]
            action = parts[-1] if len(parts) > 5 else ""
            cid = parts[-2] if action else parts[-1]

            if action == "validate":
                if not self._is_admin(crud_token):
                    return self._json({"status": "error", "message": "Acesso negado"}, 403)
                try:
                    result = cert_service.validar(cid)
                    return self._json({"status": "ok", **result})
                except Exception as e:
                    return self._json({"status": "error", "message": str(e)}, 400)

            if action == "toggle":
                if not self._is_admin(crud_token):
                    return self._json({"status": "error", "message": "Acesso negado"}, 403)
                novo = cert_service.alternar_ativo(cid)
                if novo is None:
                    return self._json({"status": "error", "message": "Não encontrado"}, 404)
                return self._json({"status": "ok", "ativo": novo})

            if action == "empresa":
                if not self._is_admin(crud_token):
                    return self._json({"status": "error", "message": "Acesso negado"}, 403)
                empresa_id = body.get("empresa_id", "")
                ok = cert_service.definir_empresa(cid, empresa_id)
                if not ok:
                    return self._json({"status": "error", "message": "Não encontrado"}, 404)
                return self._json({"status": "ok", "message": "Certificado vinculado à empresa"})

            if body.get("action") == "delete":
                if not self._is_admin(crud_token):
                    return self._json({"status": "error", "message": "Acesso negado"}, 403)
                ok = cert_service.remover(cid)
                if not ok:
                    return self._json({"status": "error", "message": "Não encontrado"}, 404)
                return self._json({"status": "ok", "message": "Certificado removido"})

        # ── Fiscal: salvar emitente (dados/empresa.json) ──
        if parsed.path == "/api/admin/fiscal/empresa":
            if not self._is_admin(crud_token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                emp = load_empresa_fiscal()
                allowed = [
                    "nome", "nome_fantasia", "cnpj", "ie", "crt", "csc_id", "csc",
                    "cod_municipio", "municipio", "uf", "cep", "endereco", "telefone",
                    "email", "cnae_prim_codigo", "inscricao_mun", "tipo_fiscal",
                    "inscricao_est",
                ]
                for key in allowed:
                    if key in body and body[key] is not None:
                        emp[key] = body[key]
                # Mapear ie → inscricao_est (campo usado pelo XML)
                if "ie" in body and body["ie"] is not None:
                    emp["inscricao_est"] = body["ie"]
                    emp["ie"] = body["ie"]
                if "crt" in body and body["crt"] is not None:
                    try:
                        emp["crt"] = int(body["crt"])
                    except (TypeError, ValueError):
                        pass
                save_json(EMPRESA_JSON, emp)
                return self._json({"status": "ok", "empresa": emp, "message": "Emitente salvo"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        # ── Fiscal: NFC-e ──
        if parsed.path == "/api/admin/fiscal/nfce/autorizar":
            if not self._has_permission(crud_token, "nfce"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                venda_id = body.get("venda_id", "")
                cert_id = body.get("cert_id", "")
                cert_senha = body.get("cert_senha", "")
                ambiente = int(body.get("ambiente", 2))
                serie = int(body.get("serie", 1))
                numero = int(body.get("numero", 0))

                if not venda_id or not cert_id:
                    return self._json({"status": "error", "message": "venda_id e cert_id são obrigatórios"}, 400)

                vendas = load_json(os.path.join(BASE_DIR, "dados", "vendas.json"))
                venda = None
                for v in vendas.get("vendas", []):
                    if str(v.get("id")) == str(venda_id):
                        venda = v
                        break
                if not venda:
                    return self._json({"status": "error", "message": "Venda não encontrada"}, 404)

                empresa = load_empresa_fiscal()
                uf = empresa.get("uf", "RS")
                if isinstance(uf, int):
                    uf_codes = {11:"RO",12:"AC",13:"AM",14:"RR",15:"PA",16:"AP",17:"TO",21:"MA",22:"PI",23:"CE",24:"RN",25:"PB",26:"PE",27:"AL",28:"SE",29:"BA",31:"MG",32:"ES",33:"RJ",35:"SP",41:"PR",42:"SC",43:"RS",50:"MS",51:"MT",52:"GO",53:"DF"}
                    uf = uf_codes.get(int(uf), "RS")

                if not numero:
                    cobol_bridge._compile_if_needed("gerir_numeracao")
                    out, _ = cobol_bridge._run("gerir_numeracao", {"ACAO": "avancar-nfce"})
                    for line in out.splitlines():
                        line = line.strip()
                        if line.isdigit():
                            numero = int(line)
                            break
                    if not numero:
                        return self._json({"status": "error", "message": "Erro ao obter numeração"}, 500)

                xml_envi = nfce_xml.montar_envi_nfe(venda, empresa, ambiente, serie, numero)
                resultado = sefaz_service.autorizar_nfce(xml_envi, uf, ambiente, cert_id, cert_senha, empresa=empresa)

                nfce_path = os.path.join(BASE_DIR, "dados", "nfce.json")
                nfce_data = load_json(nfce_path)
                notas = nfce_data.get("nfce", [])
                notas.append({
                    "venda_id": venda_id,
                    "numero": numero,
                    "serie": serie,
                    "chave": resultado.get("chave", ""),
                    "ambiente": ambiente,
                    "status": resultado.get("status", "ERRO"),
                    "protocolo": resultado.get("nProt", resultado.get("protocolo", "")),
                    "cStat": resultado.get("cStat", ""),
                    "xMotivo": resultado.get("xMotivo", ""),
                    "xml": xml_envi,
                    "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                nfce_data["nfce"] = notas
                save_json(nfce_path, nfce_data)

                return self._json({"status": "ok", "resultado": resultado, "numero": numero, "chave": resultado.get("chave", "")})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        if parsed.path == "/api/admin/fiscal/nfce/consultar":
            if not self._has_permission(crud_token, "nfce"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                chave = body.get("chave", "")
                cert_id = body.get("cert_id", "")
                cert_senha = body.get("cert_senha", "")
                ambiente = int(body.get("ambiente", 2))
                uf = body.get("uf", "RS")
                if not chave or not cert_id:
                    return self._json({"status": "error", "message": "chave e cert_id são obrigatórios"}, 400)
                resultado = sefaz_service.consultar_nfce(chave, uf, ambiente, cert_id, cert_senha)
                return self._json({"status": "ok", "resultado": resultado})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        if parsed.path == "/api/admin/fiscal/nfce/cancelar":
            if not self._has_permission(crud_token, "nfce"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                chave = body.get("chave", "")
                protocolo = body.get("protocolo", "")
                justificativa = body.get("justificativa", "Cancelamento manual")
                cert_id = body.get("cert_id", "")
                cert_senha = body.get("cert_senha", "")
                ambiente = int(body.get("ambiente", 2))
                uf = body.get("uf", "RS")
                if not chave or not protocolo or not cert_id:
                    return self._json({"status": "error", "message": "chave, protocolo e cert_id são obrigatórios"}, 400)
                resultado = sefaz_service.cancelar_nfce(chave, protocolo, uf, ambiente, cert_id, cert_senha, justificativa)
                return self._json({"status": "ok", "resultado": resultado})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        # ── Fiscal: NF-e (modelo 55) ──
        if parsed.path == "/api/admin/fiscal/nfe/autorizar":
            if not self._has_permission(crud_token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                venda_id = body.get("venda_id", "")
                cert_id = body.get("cert_id", "")
                cert_senha = body.get("cert_senha", "")
                ambiente = int(body.get("ambiente", 2))
                serie = int(body.get("serie", 1))
                numero = int(body.get("numero", 0))
                sincrono = body.get("sincrono", False)

                if not venda_id or not cert_id:
                    return self._json({"status": "error", "message": "venda_id e cert_id são obrigatórios"}, 400)

                vendas = load_json(os.path.join(BASE_DIR, "dados", "vendas.json"))
                venda = None
                for v in vendas.get("vendas", []):
                    if str(v.get("id")) == str(venda_id):
                        venda = v
                        break
                if not venda:
                    return self._json({"status": "error", "message": "Venda não encontrada"}, 404)

                empresa = load_empresa_fiscal()
                uf = empresa.get("uf", "RS")
                if isinstance(uf, int):
                    uf_codes = {11:"RO",12:"AC",13:"AM",14:"RR",15:"PA",16:"AP",17:"TO",21:"MA",22:"PI",23:"CE",24:"RN",25:"PB",26:"PE",27:"AL",28:"SE",29:"BA",31:"MG",32:"ES",33:"RJ",35:"SP",41:"PR",42:"SC",43:"RS",50:"MS",51:"MT",52:"GO",53:"DF"}
                    uf = uf_codes.get(int(uf), "RS")

                if not numero:
                    cobol_bridge._compile_if_needed("gerir_numeracao")
                    out, _ = cobol_bridge._run("gerir_numeracao", {"ACAO": "avancar-nfe"})
                    for line in out.splitlines():
                        line = line.strip()
                        if line.isdigit():
                            numero = int(line)
                            break
                    if not numero:
                        return self._json({"status": "error", "message": "Erro ao obter numeração"}, 500)

                xml_envi = nfe_xml.montar_envi_nfe(venda, empresa, ambiente, serie, numero, sincrono=sincrono)
                resultado = sefaz_service.autorizar_nfe(xml_envi, uf, ambiente, cert_id, cert_senha)

                nfe_path = os.path.join(BASE_DIR, "dados", "nfe.json")
                nfe_data = load_json(nfe_path)
                notas = nfe_data.get("nfe", [])
                notas.append({
                    "venda_id": venda_id,
                    "numero": numero,
                    "serie": serie,
                    "chave": resultado.get("chave", ""),
                    "ambiente": ambiente,
                    "status": resultado.get("status", "ERRO"),
                    "protocolo": resultado.get("nProt", resultado.get("protocolo", "")),
                    "cStat": resultado.get("cStat", ""),
                    "xMotivo": resultado.get("xMotivo", ""),
                    "xml": xml_envi,
                    "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                nfe_data["nfe"] = notas
                save_json(nfe_path, nfe_data)

                return self._json({"status": "ok", "resultado": resultado, "numero": numero, "chave": resultado.get("chave", "")})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        if parsed.path == "/api/admin/fiscal/nfe/consultar":
            if not self._has_permission(crud_token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                chave = body.get("chave", "")
                cert_id = body.get("cert_id", "")
                cert_senha = body.get("cert_senha", "")
                ambiente = int(body.get("ambiente", 2))
                uf = body.get("uf", "RS")
                if not chave or not cert_id:
                    return self._json({"status": "error", "message": "chave e cert_id são obrigatórios"}, 400)
                resultado = sefaz_service.consultar_nfe(chave, uf, ambiente, cert_id, cert_senha)
                return self._json({"status": "ok", "resultado": resultado})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        if parsed.path == "/api/admin/fiscal/nfe/cancelar":
            if not self._has_permission(crud_token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                chave = body.get("chave", "")
                protocolo = body.get("protocolo", "")
                justificativa = body.get("justificativa", "Cancelamento manual")
                cert_id = body.get("cert_id", "")
                cert_senha = body.get("cert_senha", "")
                ambiente = int(body.get("ambiente", 2))
                uf = body.get("uf", "RS")
                if not chave or not protocolo or not cert_id:
                    return self._json({"status": "error", "message": "chave, protocolo e cert_id são obrigatórios"}, 400)
                resultado = sefaz_service.cancelar_nfe(chave, protocolo, uf, ambiente, cert_id, cert_senha, justificativa=justificativa)
                return self._json({"status": "ok", "resultado": resultado})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        if parsed.path == "/api/admin/fiscal/nfe/preview-xml":
            if not self._has_permission(crud_token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                venda_id = body.get("venda_id", "")
                ambiente = int(body.get("ambiente", 2))
                serie = int(body.get("serie", 1))
                numero = int(body.get("numero", 1))
                vendas = load_json(os.path.join(BASE_DIR, "dados", "vendas.json"))
                venda = next((v for v in vendas.get("vendas", []) if str(v.get("id")) == str(venda_id)), {})
                empresa = load_empresa_fiscal()
                xml = nfe_xml.montar_envi_nfe(venda, empresa, ambiente, serie, numero, sincrono=True)
                return self._json({"status": "ok", "xml": xml})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        if parsed.path == "/api/admin/fiscal/nfe/inutilizar":
            if not self._has_permission(crud_token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                cnpj = body.get("cnpj", "")
                serie = int(body.get("serie", 1))
                nnf_ini = int(body.get("nnf_ini", 0))
                nnf_fim = int(body.get("nnf_fim", 0))
                justificativa = body.get("justificativa", "Inutilização")
                cert_id = body.get("cert_id", "")
                cert_senha = body.get("cert_senha", "")
                ambiente = int(body.get("ambiente", 2))
                uf = body.get("uf", "RS")
                if not cnpj or not cert_id:
                    return self._json({"status": "error", "message": "cnpj e cert_id são obrigatórios"}, 400)
                resultado = sefaz_service.inutilizar_nfe(cnpj, uf, ambiente, serie, nnf_ini, nnf_fim, cert_id, cert_senha, justificativa)
                return self._json({"status": "ok", "resultado": resultado})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        # ── Fiscal: NFS-e ──
        if parsed.path == "/api/admin/fiscal/nfse/autorizar":
            if not self._has_permission(crud_token, "nfse"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                cert_id = body.get("cert_id", "")
                cert_senha = body.get("cert_senha", "")
                ambiente = int(body.get("ambiente", 2))
                numero = int(body.get("numero", 0))

                if not cert_id:
                    return self._json({"status": "error", "message": "cert_id é obrigatório"}, 400)

                empresa = load_empresa_fiscal()
                cod_mun = str(empresa.get("cod_municipio", nfse_service.DEFAULT_CIDADE))
                nota = {
                    "cliente": body.get("cliente", "Tomador"),
                    "documento": body.get("documento", ""),
                    "descricao": body.get("descricao", "Serviços prestados"),
                    "total": float(body.get("total", 0)),
                    "itens": body.get("itens", []),
                    "cod_tributacao": body.get("cod_tributacao", ""),
                    "item_lista": body.get("item_lista", "01.01"),
                }

                xml_nfse = nfse_xml.montar_nfse(nota, empresa, ambiente, 1, numero)
                resultado = nfse_service.autorizar_nfse(xml_nfse, cod_mun, ambiente, cert_id, cert_senha)

                nfse_path = os.path.join(BASE_DIR, "dados", "nfse.json")
                nfse_data = load_json(nfse_path)
                notas = nfse_data.get("nfse", [])
                notas.append({
                    "numero": numero,
                    "serie": 1,
                    "ambiente": ambiente,
                    "cliente": nota["cliente"],
                    "total": nota["total"],
                    "status": resultado.get("status", "ERRO"),
                    "xml": xml_nfse,
                    "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                nfse_data["nfse"] = notas
                save_json(nfse_path, nfse_data)

                return self._json({"status": "ok", "resultado": resultado, "numero": numero})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        # ── CT-e CRUD (COBOL) ──
        if parsed.path == "/api/admin/fiscal/cte":
            if not self._has_permission(crud_token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                action = body.get("action", "incluir")
                if action == "incluir":
                    pid = cobol_bridge.cte_incluir(body)
                    return self._json({"status": "ok", "id": pid})
                elif action == "alterar":
                    ok = cobol_bridge.cte_alterar(body.get("id"), body)
                    return self._json({"status": "ok" if ok else "error", "message": "Atualizado" if ok else "Falha"})
                elif action == "excluir":
                    ok = cobol_bridge.cte_excluir(body.get("id"))
                    return self._json({"status": "ok" if ok else "error", "message": "Excluido" if ok else "Nao encontrado"})
                return self._json({"status": "error", "message": "Acao invalida"}, 400)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        # ── MDF-e CRUD (COBOL) ──
        if parsed.path == "/api/admin/fiscal/mdfe":
            if not self._has_permission(crud_token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                action = body.get("action", "incluir")
                if action == "incluir":
                    pid = cobol_bridge.mdfe_incluir(body)
                    return self._json({"status": "ok", "id": pid})
                elif action == "alterar":
                    ok = cobol_bridge.mdfe_alterar(body.get("id"), body)
                    return self._json({"status": "ok" if ok else "error", "message": "Atualizado" if ok else "Falha"})
                elif action == "excluir":
                    ok = cobol_bridge.mdfe_excluir(body.get("id"))
                    return self._json({"status": "ok" if ok else "error", "message": "Excluido" if ok else "Nao encontrado"})
                return self._json({"status": "error", "message": "Acao invalida"}, 400)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        if parsed.path == "/api/admin/fiscal/nfse/consultar":
            if not self._has_permission(crud_token, "nfse"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                numero_rps = body.get("numero_rps", "")
                cert_id = body.get("cert_id", "")
                cert_senha = body.get("cert_senha", "")
                ambiente = int(body.get("ambiente", 2))
                empresa = load_empresa_fiscal()
                cod_mun = str(empresa.get("cod_municipio", nfse_service.DEFAULT_CIDADE))
                resultado = nfse_service.consultar_nfse(numero_rps, cod_mun, ambiente, cert_id, cert_senha)
                return self._json({"status": "ok", "resultado": resultado})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        # ── DANFE ──
        modelo = body.get("modelo", "65")

        if parsed.path == "/api/admin/fiscal/danfe":
            token = self.headers.get("X-Auth-Token", "")
            permission = "nfe" if modelo == "55" else "nfce"
            if not self._has_permission(token, permission):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            chave = body.get("chave", "")
            if not chave:
                return self._json({"status": "error", "message": "chave é obrigatória"}, 400)

            if modelo == "55":
                nf_data = load_json(os.path.join(BASE_DIR, "dados", "nfe.json"))
                nota = next((n for n in nf_data.get("nfe", []) if n.get("chave") == chave), None)
                if not nota:
                    return self._json({"status": "error", "message": "NF-e não encontrada"}, 404)
            else:
                nf_data = load_json(os.path.join(BASE_DIR, "dados", "nfce.json"))
                nota = next((n for n in nf_data.get("nfce", []) if n.get("chave") == chave), None)
                if not nota:
                    return self._json({"status": "error", "message": "NFC-e não encontrada"}, 404)

            empresa = load_empresa_fiscal()
            try:
                pdf_bytes = danfe.gerar(nota, empresa, modelo=modelo)
                nome_arq = f"DANFE-{'NFe' if modelo=='55' else 'NFCe'}-{chave}.pdf"
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Disposition", f'attachment; filename="{nome_arq}"')
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(pdf_bytes)
                return None
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        # ── CRUD Genérico: Categorias, Marcas, Fabricantes, Contatos, Partners (JSON) ──
        for cfg in [self._crud_categorias, self._crud_marcas, self._crud_fabricantes, self._crud_contatos, self._crud_partners]:
            result = cfg(parsed.path, body, crud_token)
            if result is not None:
                return result

        return self._json({"status": "error", "message": "Not found"}, 404)

    def do_PUT(self):
        self.do_POST()

    # ── CRUD Genérico ──

    def _crud_config(self, prefix, data_file, schema, list_key):
        """Retorna (GET_list, POST_create, POST_item) handlers."""
        import copy
        def get_list(token):
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            data = load_json(data_file)
            lista = []
            for eid, e in data.items():
                item = dict(e)
                item["id"] = eid
                lista.append(item)
            return self._json({"status": "ok", list_key: lista})

        def create(token, body):
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            entry = {}
            for field, default in schema.items():
                if field.startswith("_"):
                    continue
                val = body.get(field)
                if val is not None:
                    entry[field] = val if not isinstance(default, bool) else val
                else:
                    entry[field] = copy.deepcopy(default) if isinstance(default, (list, dict)) else default
            if not entry.get(schema.get("_required", "nome")):
                return self._json({"status": "error", "message": "Nome é obrigatório"}, 400)
            data = load_json(data_file)
            eid = str(uuid.uuid4())[:8]
            data[eid] = entry
            save_json(data_file, data)
            return self._json({"status": "ok", "id": eid, "message": "Criado com sucesso"})

        def item_action(token, eid, body):
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            data = load_json(data_file)
            if eid not in data:
                return self._json({"status": "error", "message": "Não encontrado"}, 404)
            if body.get("action") == "toggle":
                data[eid]["ativo"] = not data[eid].get("ativo", True)
                save_json(data_file, data)
                return self._json({"status": "ok", "ativo": data[eid]["ativo"]})
            if body.get("action") == "update":
                for field in schema:
                    if field.startswith("_"):
                        continue
                    val = body.get(field)
                    if val is not None:
                        data[eid][field] = val
                save_json(data_file, data)
                return self._json({"status": "ok", "message": "Atualizado com sucesso"})
            return self._json({"status": "error", "message": "Ação inválida"}, 400)

        return get_list, create, item_action

    def _handle_crud(self, path, body, token, prefix, data_file, schema, list_key):
        get_list, create, item_action = self._crud_config(prefix, data_file, schema, list_key)
        if path == prefix:
            if self.command == "GET":
                return get_list(token)
            return create(token, body)
        if path.startswith(prefix + "/"):
            eid = path.split("/")[-1]
            return item_action(token, eid, body)
        return None

    _CRUD_SCHEMAS = {
        "categorias": {
            "_required": "nome",
            "nome": "", "descricao": "", "ativo": True
        },
        "marcas": {
            "_required": "nome",
            "nome": "", "descricao": "", "ativo": True
        },
        "fabricantes": {
            "_required": "nome",
            "nome": "", "descricao": "", "ativo": True
        },
        "contatos": {
            "_required": "nome",
            "nome": "", "nome_fantasia": "", "tipo": "cliente", "pessoa": "PJ",
            "documento": "", "ie": "", "im": "",
            "telefone": "", "email": "",
            "cep": "", "endereco": "", "numero": "", "bairro": "",
            "cidade": "", "uf": "",
            "regime": "SN", "contribuinte_icms": "1",
            "observacao": "", "ativo": True
        },
        "partners": {
            "_required": "legal_name",
            "partner_code": "",
            "person_type": "COMPANY",
            "display_name": "",
            "legal_name": "",
            "trade_name": "",
            "status": "ACTIVE",
            "roles": [],
            "documents": [],
            "addresses": [],
            "contacts": [],
            "bank_accounts": [],
            "regime": "SN",
            "contribuinte_icms": "1",
            "observacao": "",
            "ativo": True
        }
    }

    def _crud_categorias(self, path, body, token):
        return self._handle_crud(path, body, token, "/api/admin/categorias",
            CATEGORIAS_FILE, self._CRUD_SCHEMAS["categorias"], "categorias")

    def _crud_marcas(self, path, body, token):
        return self._handle_crud(path, body, token, "/api/admin/marcas",
            MARCAS_FILE, self._CRUD_SCHEMAS["marcas"], "marcas")

    def _crud_fabricantes(self, path, body, token):
        return self._handle_crud(path, body, token, "/api/admin/fabricantes",
            FABRICANTES_FILE, self._CRUD_SCHEMAS["fabricantes"], "fabricantes")

    def _crud_contatos(self, path, body, token):
        return self._handle_crud(path, body, token, "/api/admin/contatos",
            CONTATOS_FILE, self._CRUD_SCHEMAS["contatos"], "contatos")

    def _crud_partners(self, path, body, token):
        prefix = "/api/admin/partners"
        if path == prefix and self.command == "POST":
            # gera partner_code sequencial se ausente
            if not (body.get("partner_code") or "").strip():
                data = load_json(PARTNERS_FILE)
                n = len(data) + 1
                body["partner_code"] = f"BP{n:09d}"
            if not (body.get("display_name") or "").strip():
                body["display_name"] = body.get("trade_name") or body.get("legal_name") or ""
            if body.get("ativo") is False:
                body["status"] = "INACTIVE"
            elif not body.get("status"):
                body["status"] = "ACTIVE"
            if not body.get("roles"):
                body["roles"] = ["CUSTOMER"]
        return self._handle_crud(path, body, token, prefix,
            PARTNERS_FILE, self._CRUD_SCHEMAS["partners"], "partners")

    def _find_user(self, token, users):
        if not token:
            return None
        for u in users.values():
            if u.get("token") == token:
                return u
        return None

    def _has_permission(self, token, permission):
        users = load_users()
        user = self._find_user(token, users)
        if not user:
            return False
        role = user.get("role", "")
        if role == "admin":
            return True
        perms = ROLES.get(role, {}).get("permissoes", [])
        return permission in perms

    def _is_admin(self, token):
        return self._has_permission(token, "admin")

    @staticmethod
    def _get_query_param(query_string: str, key: str, default: str = "") -> str:
        params = urllib.parse.parse_qs(query_string)
        vals = params.get(key, [])
        return vals[0] if vals else default

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Auth-Token")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Auth-Token")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.end_headers()

    def log_message(self, fmt, *args):
        try:
            print(f"[SERVER] {fmt % args}")
        except Exception:
            print(f"[SERVER] {fmt} {args}")

def seed_empresas():
    empresas = load_empresas()
    if not empresas:
        empresas["matriz"] = {"nome":"Matriz","cnpj":"00.000.000/0001-00","ie":"123.456.789.000","cidade":"São Paulo","uf":"SP","ativo":True}
        empresas["filial_sp"] = {"nome":"Filial São Paulo","cnpj":"00.000.000/0002-00","ie":"123.456.789.001","cidade":"São Paulo","uf":"SP","ativo":True}
        empresas["filial_rj"] = {"nome":"Filial Rio de Janeiro","cnpj":"00.000.000/0003-00","ie":"123.456.789.002","cidade":"Rio de Janeiro","uf":"RJ","ativo":True}
        save_empresas(empresas)
        print("   ✓ Empresas padrão criadas")

if __name__ == "__main__":
    os.chdir(BASE_DIR)
    seed_empresas()
    server = http.server.HTTPServer((HOST, PORT), AuthHandler)
    print(f"✦ BECRP Dev Server")
    print(f"   → Login:  http://localhost:{PORT}/")
    print(f"   → Menu:   http://localhost:{PORT}/index4.html")
    if not os.path.exists(USERS_FILE) or os.path.getsize(USERS_FILE) < 10:
        print(f"   ⚠ Nenhum admin. Acesse / para configurar o primeiro usuário.")
    else:
        print(f"   ✓ Admin configurado. Faça login em /")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n Server stopped.")
        server.server_close()
