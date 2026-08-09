#!/usr/bin/env python3
"""Smoke do jsonio — lock global + gravação atômica das escritas JSON.

Cobre:
  - round-trip save/load com o shape esperado
  - concorrência: 8 writers + 2 readers no MESMO arquivo (nenhum JSON corrupto)
  - atomicidade: nenhum .tmp fica para trás; leitura nunca vê arquivo pela metade
  - carga real: settings_store._save -> jsonio.save (com backup/restore do
    dados/settings.json)

Uso:
    python3 scripts/smoke_jsonio.py
"""

from __future__ import annotations

import json
import os
import random
import shutil
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import jsonio  # noqa: E402

PASS = 0
FAIL = 0


def check(label, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label} {extra}")


def main():
    print("1. Round-trip básico")
    path = "/tmp/smoke_jsonio_rt.json"
    if os.path.exists(path):
        os.remove(path)
    payload = {"modulos": {"geral": {"empresa_nome": "BECRP"}}, "lista": [1, 2, 3]}
    jsonio.save(path, payload)
    got = jsonio.load(path)
    check("save/load preserva os dados", got == payload, got)
    check("arquivo é JSON válido",
          isinstance(json.load(open(path, encoding="utf-8")), dict))
    os.remove(path)

    print("\n2. Concorrência (8 writers + 2 readers no mesmo arquivo)")
    path = "/tmp/smoke_jsonio_conc.json"
    if os.path.exists(path):
        os.remove(path)
    errors = []

    def writer(n):
        try:
            for i in range(30):
                jsonio.save(path, {"writer": n, "iter": i,
                                   "blob": "x" * random.randint(1, 800)})
        except Exception as e:  # pragma: no cover
            errors.append(f"writer{n}: {e}")

    def reader():
        try:
            for _ in range(150):
                d = jsonio.load(path)
                assert isinstance(d, dict)
        except Exception as e:  # pragma: no cover
            errors.append(f"reader: {e}")

    ths = [threading.Thread(target=writer, args=(n,)) for n in range(8)]
    ths += [threading.Thread(target=reader) for _ in range(2)]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    check("nenhum erro nas threads", not errors, errors[:3] if errors else "")
    try:
        final = json.load(open(path, encoding="utf-8"))
        ok_final = isinstance(final, dict) and "writer" in final
    except Exception as e:
        ok_final = False
        errors.append(str(e))
    check("JSON final íntegro após 240 escritas paralelas", ok_final)
    check("nenhum .tmp sobrando",
          not os.path.exists(path + ".tmp"), "leftover .tmp")
    os.remove(path)

    print("\n3. Store real (settings_store) via jsonio")
    import settings_store  # noqa: E402
    real = settings_store.SETTINGS_FILE
    orig = jsonio.load(real)
    try:
        settings_store._save({"modulos": {"geral": {"empresa_nome": "SMOKE_JSONIO"}}})
        d = settings_store.listar()
        check("settings_store._save -> jsonio.save grava de verdade",
              d["modulos"]["geral"]["empresa_nome"] == "SMOKE_JSONIO", d)
        disco = jsonio.load(real)
        check("arquivo em disco confere",
              disco["modulos"]["geral"]["empresa_nome"] == "SMOKE_JSONIO"
              and "atualizado_em" in disco, disco)
    finally:
        jsonio.save(real, orig)
    check("arquivo real restaurado após o teste", jsonio.load(real) == orig)

    print(f"\n{'=' * 52}")
    print(f"Resultado: {PASS} ✅  {FAIL} ❌")
    print(f"{'=' * 52}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
