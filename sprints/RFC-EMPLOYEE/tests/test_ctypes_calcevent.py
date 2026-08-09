#!/usr/bin/env python3
"""Teste Fase 3 — regras de calculo de evento do CALCEVENT via ctypes.

Valida o modulo CALCEVENT (calcevent.so) chamado via ctypes com o contrato
estendido na Fase 3 (calcevent-io.cpy):
  (LK-EV-CODIGO, LK-EV-TIPO, LK-EV-REFERENCIA, LK-EV-BASE,
   LK-EV-CARGA-HORARIA) -> (LK-EV-VALOR, LK-EV-INCIDE-INSS,
                             LK-EV-INCIDE-IRRF, LK-EV-INCIDE-FGTS)

Regras implementadas (RFC-004, catalogo inicial da secao 3):
  * 001 Salario Base   -> valor = base (cadastro RFC-002)
  * 002 Horas Extras 50%  -> (base / carga) x horas x 1,5
  * 003 Horas Extras 100% -> (base / carga) x horas x 2,0
  * 007 Comissao/Vendas  -> valor = base (comissao APURADA no PDV -
                           RFC-COMISSION/RFC-001 §5 regra 4)
  * 008 DSR sobre comissao -> (base / ref.) x ref-2 -
                           RFC-COMISSION/RFC-001 §7.1
  * 022 Vale-Transporte   -> 6% da base, LIMITADO ao custo real (ref.)
  * 025 Faltas / Atrasos  -> (base / 30) x dias
Incidencias: 001/002/003/007/008 -> S/S/S; 022/025 -> N/N/N.

Estrategia:
  * Casos dourados fixos (ex.: EXEMPLO-competencia.md: salario 4.500,00,
    carga 220h, 10h HE 50% -> 306,82; 2 faltas -> 300,00).
  * Bateria contra implementacao de referencia em Decimal.

Regra critica do PLAN_ERP.md secao 4.1: libcob inicializada UMA vez no
startup; .so carregado durante toda a vida do processo.

Mapeamento PIC -> ctypes (DISPLAY ASCII):
  * PIC 9(3)      ->  3 bytes (codigo)
  * PIC X(1)      ->  1 byte  (tipo / incidencias)
  * PIC 9(6)V99   ->  8 bytes (referencia)
  * PIC 9(10)V99  -> 12 bytes (base / valor)
  * PIC 9(4)V99   ->  6 bytes (carga horaria mensal)
"""
import ctypes
import ctypes.util
import os
import unittest
from decimal import Decimal, ROUND_HALF_UP

# --------------------------------------------------------------------------
# Startup: carrega libcob UMA vez (regra PLAN_ERP 4.1) e o calcevent.so
# --------------------------------------------------------------------------
_libcob_path = ctypes.util.find_library("cob") or "libcob.so.4"
_libcob = ctypes.CDLL(_libcob_path)
_libcob.cob_init.argtypes = [ctypes.c_int, ctypes.c_void_p]
_libcob.cob_init.restype = None
_libcob.cob_init(0, None)          # UMA vez, no startup do processo

_SO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "cobol")
_SO_PATH = os.path.join(_SO_DIR, "calcevent.so")
if not os.path.exists(_SO_PATH):
    raise RuntimeError(
        f"calcevent.so nao encontrado em {_SO_PATH}. "
        "Compile antes: cd cobol && cobc -m -o calcevent.so calcevent.cbl"
    )
_cal = ctypes.CDLL(_SO_PATH)
_CALCEVENT = _cal.CALCEVENT
_CALCEVENT.argtypes = [ctypes.c_char_p] * 10  # 6 entradas + 4 saidas
_CALCEVENT.restype = None


# --------------------------------------------------------------------------
# Conversores PIC -> Python
# --------------------------------------------------------------------------
def codigo_to_pic(n: int) -> bytes:
    """1 -> b'001' (PIC 9(3))."""
    return f"{n:03d}".encode("ascii")


def tipo_to_pic(t: str) -> bytes:
    """'P' -> b'P' (PIC X(1))."""
    return t.encode("ascii")


def ref_to_pic(value: Decimal) -> bytes:
    """240.00 -> b'00024000' (PIC 9(6)V99, 8 bytes)."""
    cents = int((value * 100).quantize(Decimal("1"), ROUND_HALF_UP))
    return f"{cents:08d}".encode("ascii")


def base_to_pic(value: Decimal) -> bytes:
    """4500.00 -> b'000000450000' (PIC 9(10)V99, 12 bytes)."""
    cents = int((value * 100).quantize(Decimal("1"), ROUND_HALF_UP))
    return f"{cents:012d}".encode("ascii")


def carga_to_pic(value: Decimal) -> bytes:
    """220.00 -> b'022000' (PIC 9(4)V99, 6 bytes)."""
    cents = int((value * 100).quantize(Decimal("1"), ROUND_HALF_UP))
    return f"{cents:06d}".encode("ascii")


def pic_to_cents(buf: bytes) -> int:
    """b'000000450000' -> 450000 centavos."""
    raw = buf[:12]
    int_part = int(raw[:10])
    dec_part = int(raw[10:12])
    return int_part * 100 + dec_part


def call_calcevent(codigo: int, tipo: str, referencia: Decimal,
                   base: Decimal, carga: Decimal, referencia2: Decimal = Decimal("0")):
    """Chama CALCEVENT e retorna (valor_centavos, inss, irrf, fgts)."""
    valor = ctypes.create_string_buffer(13)   # 12 bytes + nul
    inss = ctypes.create_string_buffer(2)     # 1 byte + nul
    irrf = ctypes.create_string_buffer(2)
    fgts = ctypes.create_string_buffer(2)

    _CALCEVENT(codigo_to_pic(codigo), tipo_to_pic(tipo),
               ref_to_pic(referencia), ref_to_pic(referencia2),
               base_to_pic(base), carga_to_pic(carga),
               valor, inss, irrf, fgts)

    return (pic_to_cents(valor.value),
            inss.value[:1].decode(), irrf.value[:1].decode(),
            fgts.value[:1].decode())


# --------------------------------------------------------------------------
# Referencia independente (regras do RFC-004 em Decimal)
# --------------------------------------------------------------------------
def ref_calcevent(codigo: int, referencia: Decimal, base: Decimal,
                  carga: Decimal, referencia2: Decimal = Decimal("0")):
    """Retorna (valor, inss, irrf, fgts) conforme RFC-004."""
    if codigo == 1:
        valor = base
        incid = ("S", "S", "S")
    elif codigo == 2:
        if carga <= 0:
            valor = Decimal("0")
        else:
            valor = base / carga * referencia * Decimal("1.5")
        incid = ("S", "S", "S")
    elif codigo == 3:
        if carga <= 0:
            valor = Decimal("0")
        else:
            valor = base / carga * referencia * Decimal("2.0")
        incid = ("S", "S", "S")
    elif codigo == 7:
        valor = base
        incid = ("S", "S", "S")
    elif codigo == 8:
        if referencia <= 0:
            valor = Decimal("0")
        else:
            valor = base / referencia * referencia2
        incid = ("S", "S", "S")
    elif codigo == 22:
        vt6 = base * Decimal("0.06")
        valor = min(vt6, referencia)
        incid = ("N", "N", "N")
    elif codigo == 25:
        valor = base / 30 * referencia
        incid = ("N", "N", "N")
    else:
        valor = Decimal("0")
        incid = ("N", "N", "N")
    valor_cents = int(valor.quantize(Decimal("0.01"), ROUND_HALF_UP) * 100)
    return valor_cents, incid


# --------------------------------------------------------------------------
# Testes
# --------------------------------------------------------------------------
class TestCalceventCtypes(unittest.TestCase):
    def test_salario_base(self):
        """001: valor = base, incide S/S/S."""
        valor, inss, irrf, fgts = call_calcevent(
            1, "P", Decimal("0"), Decimal("4500.00"), Decimal("220.00"))
        self.assertEqual(valor, 450000)
        self.assertEqual((inss, irrf, fgts), ("S", "S", "S"))

    def test_he_50_exemplo_documentado(self):
        """002: caso do EXEMPLO-competencia.md -> 306,82 (S/S/S)."""
        valor, inss, irrf, fgts = call_calcevent(
            2, "P", Decimal("10"), Decimal("4500.00"), Decimal("220.00"))
        self.assertEqual(valor, 30682)  # R$ 306,82
        self.assertEqual((inss, irrf, fgts), ("S", "S", "S"))

    def test_he_100(self):
        """003: (4500/220) x 5 x 2,0 = 204,55."""
        valor, *_ = call_calcevent(
            3, "P", Decimal("5"), Decimal("4500.00"), Decimal("220.00"))
        self.assertEqual(valor, 20455)

    def test_comissao_evento7(self):
        """007: valor = comissao apurada (base), incide S/S/S (RFC-COMISSION §6)."""
        valor, inss, irrf, fgts = call_calcevent(
            7, "P", Decimal("0"), Decimal("116.50"), Decimal("220.00"))
        self.assertEqual(valor, 11650)  # R$ 116,50 (exemplo RFC-005 §6)
        self.assertEqual((inss, irrf, fgts), ("S", "S", "S"))

    def test_dsr_sobre_comissao(self):
        """008: (2.000/26) x 4 = 307,69 (exemplo RFC-001 §4.1), S/S/S."""
        valor, inss, irrf, fgts = call_calcevent(
            8, "P", Decimal("26"), Decimal("2000.00"), Decimal("220.00"),
            Decimal("4"))
        self.assertEqual(valor, 30769)  # R$ 307,69
        self.assertEqual((inss, irrf, fgts), ("S", "S", "S"))

    def test_dsr_divisor_zero(self):
        """008 com dias uteis 0 -> valor 0 (protecao contra divisao por zero)."""
        valor, *_ = call_calcevent(
            8, "P", Decimal("0"), Decimal("2000.00"), Decimal("220.00"),
            Decimal("4"))
        self.assertEqual(valor, 0)

    def test_vt_limitado(self):
        """022: 6% = 270,00; teto 240,00 -> valor 240,00 (N/N/N)."""
        valor, inss, irrf, fgts = call_calcevent(
            22, "D", Decimal("240.00"), Decimal("4500.00"), Decimal("220.00"))
        self.assertEqual(valor, 24000)
        self.assertEqual((inss, irrf, fgts), ("N", "N", "N"))

    def test_vt_sem_atingir_teto(self):
        """022: 6% = 270,00; teto 300,00 -> valor 270,00 (nao limita)."""
        valor, *_ = call_calcevent(
            22, "D", Decimal("300.00"), Decimal("4500.00"), Decimal("220.00"))
        self.assertEqual(valor, 27000)

    def test_faltas_exemplo_documentado(self):
        """025: (4500/30) x 2 = 300,00 (N/N/N) - caso do EXEMPLO."""
        valor, inss, irrf, fgts = call_calcevent(
            25, "D", Decimal("2"), Decimal("4500.00"), Decimal("220.00"))
        self.assertEqual(valor, 30000)
        self.assertEqual((inss, irrf, fgts), ("N", "N", "N"))

    def test_carga_horaria_zero_nao_divide(self):
        """002 com carga 0 -> valor 0 (protecao contra divisao por zero)."""
        valor, *_ = call_calcevent(
            2, "P", Decimal("10"), Decimal("4500.00"), Decimal("0"))
        self.assertEqual(valor, 0)

    def test_evento_desconhecido(self):
        """999: valor 0, N/N/N."""
        valor, inss, irrf, fgts = call_calcevent(
            999, "P", Decimal("0"), Decimal("4500.00"), Decimal("220.00"))
        self.assertEqual(valor, 0)
        self.assertEqual((inss, irrf, fgts), ("N", "N", "N"))

    def test_bateria_contra_referencia(self):
        """Varredura ampla: COBOL deve bater com a referencia Decimal."""
        casos = []
        for base in (Decimal("1500.00"), Decimal("3000.00"),
                     Decimal("4500.00"), Decimal("9999.99")):
            casos.append((7, Decimal("0"), base, Decimal("220.00")))
            casos.append((8, Decimal("26"), base, Decimal("220.00"),
                          Decimal("4")))
            casos.append((8, Decimal("25"), base, Decimal("220.00"),
                          Decimal("5")))
            for carga in (Decimal("180.00"), Decimal("220.00"),
                          Decimal("240.00")):
                for horas in (Decimal("1"), Decimal("8"), Decimal("44.5")):
                    casos.append((2, horas, base, carga))
                    casos.append((3, horas, base, carga))
                for dias in (Decimal("1"), Decimal("2"), Decimal("15")):
                    casos.append((25, dias, base, carga))
                for custo in (Decimal("100.00"), Decimal("270.00"),
                              Decimal("600.00")):
                    casos.append((22, custo, base, carga))

        for codigo, ref, base, carga, *resto in casos:
            ref2 = resto[0] if resto else Decimal("0")
            with self.subTest(codigo=codigo, ref=ref, base=base, carga=carga):
                valor, inss, irrf, fgts = call_calcevent(
                    codigo, "P" if codigo < 20 else "D", ref, base, carga,
                    ref2)
                v_esp, (i_esp, r_esp, f_esp) = ref_calcevent(
                    codigo, ref, base, carga, ref2)
                self.assertEqual(valor, v_esp, f"valor evento {codigo}")
                self.assertEqual((inss, irrf, fgts), (i_esp, r_esp, f_esp),
                                 f"incidencias evento {codigo}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
