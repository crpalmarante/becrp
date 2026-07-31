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

os.makedirs(DATA_DIR, exist_ok=True)

EMPRESA_JSON = os.path.join(BASE_DIR, "dados", "empresa.json")

def load_empresa_fiscal():
    if not os.path.exists(EMPRESA_JSON):
        return {}
    with open(EMPRESA_JSON, "r") as f:
        return json.load(f)

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

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def make_token():
    return hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:32]

ROLES = {
    "admin": {"label": "Administrador", "permissoes": "*"},
    "supervisor": {"label": "Supervisor", "permissoes": ["dashboard", "nfe", "nfce", "nfse", "clientes", "produtos", "relatorios", "folha", "contabilidade"]},
    "operador": {"label": "Operador", "permissoes": ["dashboard", "nfe", "nfce"]},
    "fiscal": {"label": "Fiscal", "permissoes": ["dashboard", "nfe", "nfce", "nfse", "certificados", "sped"]}
}

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
                item = {"id": uid, "usuario": u["usuario"], "nome": u.get("nome", ""),
                        "role": u.get("role", "operador"), "ativo": u.get("ativo", True),
                        "email": u.get("email", ""), "empresas": u.get("empresas", {})}
                lista.append(item)
            return self._json({"status": "ok", "users": lista})

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

        # ── POS: leitura (qualquer usuário autenticado) ──
        if parsed.path == "/api/pos/produtos":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            produtos = cobol_bridge.produtos_listar()
            return self._json({"status": "ok", "source": "api", "produtos": produtos})

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
            role = body.get("role", "operador")
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
                if body.get("role"): users[uid]["role"] = body["role"]
                if body.get("senha"): users[uid]["senha"] = hash_password(body["senha"])
                if "empresas" in body:
                    users[uid]["empresas"] = body["empresas"]
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
