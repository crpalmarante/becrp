"""jsonio — leitura/escrita de arquivos JSON com lock global e gravação atômica.

O servidor roda multithread (ThreadingHTTPServer) e vários stores gravam os
mesmos arquivos data/*.json. Sem proteção, duas requisições concorrentes
escrevendo o mesmo arquivo poderiam corromper o JSON (gravação truncada) ou
perder atualizações. Este módulo centraliza:

  - um lock GLOBAL (compartilhado por todos os módulos) serializando as escritas;
  - gravação atômica (arquivo .tmp + os.replace), de modo que leitores nunca
    enxergam um arquivo pela metade.

Limitação conhecida: o lock protege a ESCRITA (elimina corrupção/gravação
parcial). O ciclo load-modify-save completo de um store não é serializado —
duas requisições concorrentes alterando o mesmo registro podem perder uma
atualização (last-writer-wins com dado velho). Para um ERP de admin único com
arquivos pequenos é aceitável; se precisar de serialização total, envolva a
função do store inteira com um lock.

Uso (nos stores):
    import jsonio
    jsonio.save(CAMINHO, dados)
    dados = jsonio.load(CAMINHO, default={})
"""

from __future__ import annotations

import json
import os
import threading

_LOCK = threading.Lock()


def save(path, data):
    """Grava `data` em `path` de forma atômica, sob o lock global."""
    with _LOCK:
        directory = os.path.dirname(path) or "."
        os.makedirs(directory, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    return data


def load(path, default=None):
    """Lê o JSON de `path`; retorna `default` ({} por padrão) se não existir."""
    if default is None:
        default = {}
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, OSError):
        return default
