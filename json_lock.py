"""Locks simples de arquivo para proteger leitura/escrita de JSON."""

from __future__ import annotations

import fcntl
import os
import threading
from contextlib import contextmanager

# Lock por instância de processo (thread-local) para evitar deadlock
# quando o mesmo thread locka duas vezes; flock já permite isso no Unix,
# mas mantemos uma camada extra de segurança.
_thread_locks = {}
_thread_locks_lock = threading.Lock()


def _lock_file_name(path: str) -> str:
    directory = os.path.dirname(os.path.abspath(path)) or "."
    basename = os.path.basename(path) or "data.lock"
    return os.path.join(directory, f".{basename}.lock")


@contextmanager
def acquire(path: str, timeout: float = 10.0, shared: bool = False):
    """
    Adquire lock de arquivo exclusivo (ou compartilhado se shared=True) para path.
    Cria um arquivo .<nome>.lock ao lado do arquivo de dados.
    """
    lock_path = _lock_file_name(path)
    os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
    try:
        with _thread_locks_lock:
            tid = threading.current_thread().ident
            key = (lock_path, tid)
            count = _thread_locks.get(key, 0)
            _thread_locks[key] = count + 1

        # flock é recursivo no mesmo processo/thread no Linux; ok não fazer nada se count>0
        if shared:
            fcntl.flock(lock_fd, fcntl.LOCK_SH)
        else:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
        yield
    finally:
        with _thread_locks_lock:
            tid = threading.current_thread().ident
            key = (lock_path, tid)
            count = _thread_locks.get(key, 1)
            if count <= 1:
                _thread_locks.pop(key, None)
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            else:
                _thread_locks[key] = count - 1
        try:
            os.close(lock_fd)
        except OSError:
            pass


def read(path: str, read_fn, *args, **kwargs):
    with acquire(path, shared=True):
        return read_fn(*args, **kwargs)


def write(path: str, write_fn, *args, **kwargs):
    with acquire(path, shared=False):
        return write_fn(*args, **kwargs)
