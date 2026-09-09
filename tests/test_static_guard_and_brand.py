"""Regressão: guarda de arquivos estáticos + marca dinâmica (org/brand.js).

Cobre:
1. server._is_sensitive_static_path — data/, dados/, backups, .py, .pfx, .dat,
   travessia ".." e ".bak" bloqueados; js/, css/, pages/, assets liberados.
2. GET /api/organizacao/nome — 401 sem token; 200 com token, retornando a
   identidade (fantasia da matriz) usada pelo js/brand.js.
3. Servidor estático — /data/users.json → 404 mesmo com token válido;
   /js/brand.js → 200.
4. Páginas: todas as pages/*.html bem-formadas incluem js/brand.js
   (as 6 antigas páginas WMS truncadas foram reparadas; arquivos ainda
   truncados são ignorados com aviso).
"""

import glob
import json
import os
import sys
import threading
import unittest
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# server.py lê sys.argv[1] como porta; isolamos antes de importar
_orig_argv = sys.argv[:]
sys.argv = [sys.argv[0]]
try:
    import server  # noqa: E402
finally:
    sys.argv = _orig_argv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class StaticGuardTest(unittest.TestCase):
    """server._is_sensitive_static_path — caminhos sensíveis nunca servidos."""

    def test_bloqueia_diretorios_de_dados(self):
        for p in (
            "/data/users.json", "/data/empresas.json",
            "/data/estabelecimentos_fiscal.json", "/data/backups/x/empresas.json",
            "/dados/empresa.json", "/dados/settings.json",
            "/dados/certificados/foo.pfx", "/uploads/funcionarios/f.png",
            "/cobol/programs/gerir_parceiros.cbl",
        ):
            self.assertTrue(server._is_sensitive_static_path(p), p)

    def test_bloqueia_fontes_e_binarios(self):
        for p in (
            "/server.py", "/org_store.py", "/js/x.py.bak", "/cobol_bridge.py.bak_alterar_validacao",
            "/dados/x.dat", "/cert.pfx", "/cert.p12", "/server.log", "/Plano Referencial.xls",
            "/db.sqlite", "/db.db",
        ):
            self.assertTrue(server._is_sensitive_static_path(p), p)

    def test_bloqueia_travessia_e_dotdirs(self):
        for p in ("/../server.py", "/data/../server.py", "/js/../../etc/passwd",
                  "/.git/config", "/.git/HEAD", "/__pycache__/server.cpython-312.pyc",
                  "/.pytest_cache/v/cache/lastfailed"):
            self.assertTrue(server._is_sensitive_static_path(p), p)

    def test_libera_assets_do_frontend(self):
        for p in (
            "/index.html", "/index4.html", "/login.html",
            "/js/brand.js", "/js/services/AuthService.js", "/js/auth/page-boot.js",
            "/css/style.css", "/pages/empresas.html", "/pages/wms-armazens.html",
            "/assets/data/menu.json", "/assets/images/icons.svg", "/img/icons.svg",
            "/fiscalui/x.js", "/modules/frontend/whatever.js",
        ):
            self.assertFalse(server._is_sensitive_static_path(p), p)

    def test_aceita_lista_branca_de_arquivos_de_dados_publicos(self):
        """menu.json em assets/data é asset de build, não dado runtime."""
        self.assertFalse(server._is_sensitive_static_path("/assets/data/menu.json"))


class _ServerMixin:
    @classmethod
    def _start_server(cls):
        cls._srv = __import__("http.server", fromlist=["ThreadingHTTPServer"]).ThreadingHTTPServer(
            ("127.0.0.1", 0), server.AuthHandler
        )
        cls._port = cls._srv.server_address[1]
        cls._thread = threading.Thread(target=cls._srv.serve_forever, daemon=True)
        cls._thread.start()
        return cls._port

    @classmethod
    def _stop_server(cls):
        cls._srv.shutdown()
        cls._srv.server_close()


def _request(url, token=""):
    req = urllib.request.Request(url)
    if token:
        req.add_header("X-Auth-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


class OrganizacaoNomeEndpointTest(_ServerMixin, unittest.TestCase):
    """GET /api/organizacao/nome — fonte da marca dinâmica do brand.js."""

    @classmethod
    def setUpClass(cls):
        cls.port = cls._start_server()
        os.chdir(BASE_DIR)
        # backup do users.json p/ restaurar após a classe (em clone fresco o
        # arquivo não existe e o teste cria um admin temporário)
        cls._users_path = os.path.join(BASE_DIR, "data", "users.json")
        cls._users_backup = (
            open(cls._users_path, "rb").read()
            if os.path.exists(cls._users_path) else None
        )

    @classmethod
    def tearDownClass(cls):
        cls._stop_server()
        if cls._users_backup is not None:
            with open(cls._users_path, "wb") as f:
                f.write(cls._users_backup)
        elif os.path.exists(cls._users_path):
            os.remove(cls._users_path)

    def _token_admin(self):
        users = server.load_users()
        if isinstance(users, dict):
            for u in users.values():
                if isinstance(u, dict) and u.get("role") == "admin" and u.get("ativo", True):
                    if not u.get("token"):
                        u["token"] = server.make_token()
                        server.save_users(users)
                    return u["token"]
        # clone fresco: sem users.json — cria admin temporário para o teste
        users = users if isinstance(users, dict) else {}
        tok = server.make_token()
        users["__test_admin"] = {
            "usuario": "test_admin", "nome": "Teste Admin",
            "email": "test_admin@test.local", "senha": "x",
            "role": "admin", "empresas": {}, "ativo": True, "token": tok,
        }
        server.save_users(users)
        return tok

    def test_401_sem_token(self):
        code, body = _request(f"http://127.0.0.1:{self.port}/api/organizacao/nome")
        self.assertEqual(code, 401)
        self.assertEqual(json.loads(body).get("status"), "error")

    def test_401_token_invalido(self):
        code, _ = _request(f"http://127.0.0.1:{self.port}/api/organizacao/nome", token="invalido")
        self.assertEqual(code, 401)

    def test_200_com_token_retorna_identidade(self):
        tok = self._token_admin()
        code, body = _request(f"http://127.0.0.1:{self.port}/api/organizacao/nome", token=tok)
        self.assertEqual(code, 200)
        data = json.loads(body)
        self.assertEqual(data.get("status"), "ok")
        # identidade não pode ser vazia nem o placeholder BECRP
        nome = data.get("empresa") or data.get("organizacao")
        self.assertTrue(nome, "identidade vazia")
        self.assertNotEqual(nome, "BECRP")

    def test_guard_estatico_bloqueia_users_json_mesmo_com_token(self):
        tok = self._token_admin()
        code, _ = _request(f"http://127.0.0.1:{self.port}/data/users.json", token=tok)
        self.assertEqual(code, 404)
        code, _ = _request(f"http://127.0.0.1:{self.port}/dados/empresa.json", token=tok)
        self.assertEqual(code, 404)

    def test_brand_js_servido(self):
        code, body = _request(f"http://127.0.0.1:{self.port}/js/brand.js")
        self.assertEqual(code, 200)
        self.assertIn("api/organizacao/nome", body)


class BrandCoverageTest(unittest.TestCase):
    """Todas as páginas HTML bem-formadas incluem js/brand.js."""

    def test_paginas_completas_tem_brand_js(self):
        faltando = []
        truncadas = []
        for f in sorted(glob.glob(os.path.join(BASE_DIR, "pages", "*.html"))):
            src = open(f, encoding="utf-8").read()
            if "</body>" not in src:
                # página WIP/truncada não roda JS — apenas reporta
                truncadas.append(os.path.basename(f))
                continue
            if "js/brand.js" not in src:
                faltando.append(os.path.basename(f))
        self.assertEqual(faltando, [], f"páginas sem brand.js: {faltando}")
        if truncadas:
            print(f"\n[aviso] páginas truncadas (sem </body>): {truncadas}")

    def test_brand_js_aplica_marca_e_preserva_fallback(self):
        path = os.path.join(BASE_DIR, "js", "brand.js")
        src = open(path, encoding="utf-8").read()
        # chama o endpoint correto
        self.assertIn("/api/organizacao/nome", src)
        # envia o token
        self.assertIn("X-Auth-Token", src)
        # degradação segura: se a API falhar, mantém o texto existente
        self.assertIn("BECRP", src)

    def test_index4_tem_marca_dinamica(self):
        src = open(os.path.join(BASE_DIR, "index4.html"), encoding="utf-8").read()
        self.assertIn("/api/organizacao/nome", src)


if __name__ == "__main__":
    unittest.main()
