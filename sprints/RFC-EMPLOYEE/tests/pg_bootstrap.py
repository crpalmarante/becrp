#!/usr/bin/env python3
"""Infraestrutura compartilhada dos testes de integração com PostgreSQL.

Bootstrapa um cluster PostgreSQL 16 TEMPORÁRIO e descartável (initdb + pg_ctl
em diretório efêmero em /tmp, porta livre) e aplica as migrations do projeto
na ordem passada — o mesmo padrão que antes vivia dentro de
tests/test_permissions_integration.py, agora reutilizado por todos os testes
de integração (permissions, máquina de estados, runs/lines, tabelas fiscais...).

MODO CI — REUSO DE BANCO EXISTENTE:
  Se a env var ERP_TEST_DATABASE_URL apontar para uma URL libpq (ex.:
  postgresql://user:pass@host:5432/db), NENHUM cluster é criado: o TempCluster
  conecta NESTE banco e aplica as migrations nele (mesma lógica do bootstrap).
  Importante: o banco DEVE ser dedicado e descartável (criado por job de CI) —
  no modo externo TODAS as classes da suíte compartilham a MESMA URL, então
  start() RESETA o schema public (DROP SCHEMA public CASCADE; CREATE SCHEMA
  public) antes de aplicar as migrations (que não são idempotentes). Nesse modo
  stop() vira no-op: o banco compartilhado não é derrubado nem removido.

Requisitos: psycopg2 E pelo menos uma das opções de banco — (a) binários locais
do PostgreSQL (PG_BINDIR ou /usr/lib/postgresql/<v>/bin ou `pg_config --bindir`)
para o bootstrap de cluster, ou (b) ERP_TEST_DATABASE_URL (CI). A checagem de
disponibilidade (test_backend_available) e o skip ficam nos arquivos de teste
(nunca falhar por falta de ambiente).
"""
import glob
import os
import shutil
import socket
import subprocess
import tempfile
import time

try:
    import psycopg2
    HAS_PSYCOPG = True
except ImportError:
    HAS_PSYCOPG = False

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(REPO, "db")


def test_backend_available():
    """True se há como executar os testes de integração: banco externo via
    ERP_TEST_DATABASE_URL (CI) ou binários locais do PostgreSQL (bootstrap)."""
    return bool(os.environ.get("ERP_TEST_DATABASE_URL")) or bool(find_pgbindir())


def find_pgbindir():
    """Localiza o diretório com initdb/pg_ctl (PG_BINDIR > glob > pg_config)."""
    env = os.environ.get("PG_BINDIR")
    if env and os.path.exists(os.path.join(env, "initdb")):
        return env
    hits = sorted(glob.glob("/usr/lib/postgresql/*/bin"))
    if hits and os.path.exists(os.path.join(hits[-1], "initdb")):
        return hits[-1]
    try:
        bindir = subprocess.run(["pg_config", "--bindir"],
                                capture_output=True, text=True).stdout.strip()
        if bindir and os.path.exists(os.path.join(bindir, "initdb")):
            return bindir
    except OSError:
        pass
    return None


def free_port():
    """Porta TCP livre (para o cluster temporário não conflitar)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TempCluster:
    """Cluster PostgreSQL efêmero — ou banco externo do CI — com start()/stop().

    Modo padrão — bootstrap de cluster (sem ERP_TEST_DATABASE_URL):
      start()   — initdb + pg_ctl, aguarda o servidor, cria o banco e aplica as
                  migrations na ordem informada (ex.: ['002_...', '009_...']).
      stop()    — derruba o cluster e remove o diretório (seguro repetir).

    Modo CI — banco externo (env ERP_TEST_DATABASE_URL definida):
      start()   — NÃO cria cluster: conecta no banco da URL, RESETA o schema
                  public (DROP/CREATE) e aplica as migrations nele. Todas as
                  classes da suíte compartilham a MESMA URL (db_name é
                  ignorado) — por isso o reset a cada start() (banco deve ser
                  dedicado/descartável; migrations não idempotentes).
      stop()    — no-op: o banco compartilhado não é derrubado nem removido.

    Em ambos: connect() — nova conexão psycopg2 (GUC de sessão sempre limpo;
    UTF-8 obrigatório: as migrations contêm —, §, ✅, →).
    """

    def __init__(self, db_name, migrations):
        self.db_name = db_name
        self.migrations = migrations
        self.external_url = os.environ.get("ERP_TEST_DATABASE_URL")
        self.pgbindir = None if self.external_url else find_pgbindir()
        self.pgdata = None
        self.port = None
        self._base = None
        self._started = False

    # ------------------------------------------------------------------
    def start(self):
        if self._started:
            return self

        # --- Modo CI: reusa o banco existente (nenhum cluster é criado) ---
        if self.external_url:
            # O banco é DEDICADO/DESCARTÁVEL (contrato da env): reset do schema
            # public garante que a suíte INTEIRA — que no modo externo tem
            # todas as classes de teste compartilhando a MESMA URL (db_name é
            # ignorado) — seja re-executável, já que as migrations NÃO são
            # idempotentes. Se a URL estiver errada ou sem privilégio de
            # CREATE, falha de forma ruidosa com dica de diagnóstico; o
            # addClassCleanup dos testes chama stop(), que neste modo é no-op.
            try:
                conn = self.connect()
                with conn.cursor() as cur:
                    # IF EXISTS: se um start() anterior falhou entre o DROP e o
                    # CREATE (autocommit), o banco pode estar sem o schema —
                    # não pode travar a próxima execução.
                    cur.execute("DROP SCHEMA IF EXISTS public CASCADE")
                    cur.execute("CREATE SCHEMA public")
                self._apply_migrations(conn)
            except psycopg2.Error as exc:
                raise RuntimeError(
                    "ERP_TEST_DATABASE_URL deve apontar para um banco DEDICADO e "
                    "descartável (as migrations não são idempotentes e o schema "
                    "é resetado a cada start()). Erro: " + str(exc)) from exc
            self._started = True
            return self

        if not self.pgbindir:
            raise RuntimeError(
                "binários do PostgreSQL (initdb/pg_ctl) não encontrados: "
                "defina PG_BINDIR ou instale o servidor")

        self.pgdata = tempfile.mkdtemp(prefix="erp_pg_test_")
        self.port = free_port()

        initdb = subprocess.run(
            [os.path.join(self.pgbindir, "initdb"), "-D", self.pgdata,
             "-A", "trust", "-U", "postgres", "--no-locale"],
            capture_output=True, text=True)
        if initdb.returncode != 0:
            self._cleanup()
            raise RuntimeError(f"initdb falhou: {initdb.stderr}")

        log = os.path.join(self.pgdata, "pg.log")
        started = subprocess.run(
            [os.path.join(self.pgbindir, "pg_ctl"), "-D", self.pgdata,
             "-o", f"-p {self.port} -k /tmp -c listen_addresses=''",
             "-l", log, "start"],
            capture_output=True, text=True)
        if started.returncode != 0:
            self._cleanup()
            raise RuntimeError(f"pg_ctl start falhou: {started.stderr}")

        # aguarda o servidor aceitar conexões (até ~10s)
        for _ in range(50):
            try:
                self._base = self.connect(dbname="postgres")
                break
            except Exception:
                time.sleep(0.2)
        if self._base is None:
            self._cleanup()
            raise RuntimeError("cluster não iniciou")

        with self._base.cursor() as cur:
            cur.execute(f"CREATE DATABASE {self.db_name}")

        self._apply_migrations(self.connect())
        self._started = True
        return self

    def _apply_migrations(self, conn):
        """Aplica as migrations na ordem do projeto (arquivos com BEGIN/COMMIT)."""
        try:
            for mig in self.migrations:
                path = os.path.join(DB_DIR, mig)
                with open(path, encoding="utf-8") as f:
                    sql = f.read()
                with conn.cursor() as cur:
                    cur.execute(sql)
        finally:
            conn.close()

    def connect(self, dbname=None):
        """Nova conexão psycopg2 (autocommit pós-conexão + client UTF-8).

        Modo externo (ERP_TEST_DATABASE_URL): a URL define o banco; o argumento
        `dbname` é ignorado nesse modo.
        """
        if self.external_url:
            conn = psycopg2.connect(self.external_url, client_encoding="UTF8")
            conn.autocommit = True
            return conn
        conn = psycopg2.connect(
            host="/tmp", port=self.port, user="postgres",
            dbname=dbname or self.db_name, client_encoding="UTF8")
        conn.autocommit = True
        return conn

    def _cleanup(self):
        if self._base is not None:
            try:
                self._base.close()
            except Exception:
                pass
            self._base = None
        if self.pgdata and self.pgbindir:
            subprocess.run(
                [os.path.join(self.pgbindir, "pg_ctl"), "-D", self.pgdata,
                 "stop", "-m", "immediate"],
                capture_output=True, text=True)
            shutil.rmtree(self.pgdata, ignore_errors=True)
            self.pgdata = None

    def stop(self):
        if self.external_url:
            # no-op: o banco do CI é compartilhado — não derrubar nem remover
            self._started = False
            return
        self._cleanup()
        self._started = False
