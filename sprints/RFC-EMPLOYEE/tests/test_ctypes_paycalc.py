#!/usr/bin/env python3
"""Teste Fase 3 — PAYCALC orquestrador da folha completa via struct ctypes.

Valida o modulo PAYCALC (paycalc.so) chamado via ctypes com a estrutura
unica ENTRADA + RESULTADO do PAYCALC-IO:
  (SALARIO, CARGA-HORARIA, DEPEND, HE50, HE100, FALTAS, VT-CUSTO,
   COMISSAO, COMPETENCIA) -> (PROVENTOS, DESCONTOS, BASES, LIQUIDO)

Cadeia orquestrada pelo PAYCALC (RFC-006 §3.2):
  * CALCEVENT por evento: 001 salario, 002/003 HE, 007 comissao apurada
    (RFC-COMISSION), 022 VT, 025 faltas.
  * Base INSS = soma dos proventos com incidencia INSS.
  * TAXCALC(base INSS, competencia, depend) -> INSS e IRRF.
  * Total descontos = INSS + IRRF + VT + faltas.
  * Liquido = total proventos - total descontos.

Regra critica do PLAN_ERP.md secao 4.1: libcob inicializada UMA vez no
startup; .so carregado durante toda a vida do processo.

Nota: o PAYCALC chama CALCEVENT e TAXCALC como subprogramas — o runtime
do GnuCOBOL resolve os modulos via COB_LIBRARY_PATH (aponta p/ cobol/).

Mapeamento PIC -> ctypes (DISPLAY ASCII, um campo por byte):
  * PIC 9(10)V99 -> 12 bytes   | PIC 9(6)V99 -> 8 bytes
  * PIC 9(4)V99  ->  6 bytes   | PIC 9(6)    -> 6 bytes
  * PIC 9(2)     ->  2 bytes   | PIC 9(12)V99 -> 14 bytes
"""
import ctypes
import ctypes.util
import os
import unittest
from decimal import Decimal, ROUND_HALF_UP

# --------------------------------------------------------------------------
# Startup: libcob UMA vez + COB_LIBRARY_PATH para os subprogramas
# --------------------------------------------------------------------------
_SO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "cobol")
os.environ["COB_LIBRARY_PATH"] = _SO_DIR

_libcob_path = ctypes.util.find_library("cob") or "libcob.so.4"
_libcob = ctypes.CDLL(_libcob_path)
_libcob.cob_init.argtypes = [ctypes.c_int, ctypes.c_void_p]
_libcob.cob_init.restype = None
_libcob.cob_init(0, None)          # UMA vez, no startup do processo

_SO_PATH = os.path.join(_SO_DIR, "paycalc.so")
if not os.path.exists(_SO_PATH):
    raise RuntimeError(
        f"paycalc.so nao encontrado em {_SO_PATH}. "
        "Compile antes: cd cobol && cobc -m -o paycalc.so paycalc.cbl"
    )

# PAYCALC chama CALCEVENT e TAXCALC como subprogramas via CALL. No runtime
# do GnuCOBOL o CALL resolve para o programa REGISTRADO — e o registro so
# acontece quando o entry point do modulo e invocado (nao basta dlopen).
# Aqui carregamos e invocamos uma vez cada subprograma (mesmo efeito de
# roda-los antes na mesma vida do processo - PLAN_ERP 4.1).
_calcevent_path = os.path.join(_SO_DIR, "calcevent.so")
_taxcalc_path = os.path.join(_SO_DIR, "taxcalc.so")
if not (os.path.exists(_calcevent_path) and os.path.exists(_taxcalc_path)):
    raise RuntimeError(
        "calcevent.so / taxcalc.so nao encontrados em cobol/. Compile antes: "
        "cd cobol && cobc -m -o calcevent.so calcevent.cbl && cobc -m -o taxcalc.so taxcalc.cbl"
    )

_cal = ctypes.CDLL(_calcevent_path)
_CALCEVENT = _cal.CALCEVENT
_CALCEVENT.argtypes = [ctypes.c_char_p] * 10  # codigo, tipo, ref, ref-2, base, carga, valor, inss, irrf, fgts
_CALCEVENT.restype = None
# Invocacao unica p/ registrar CALCEVENT no runtime (valores descartaveis).
# IMPORTANTE: buffers dimensionados p/ o maior campo dos copybooks dos
# subprogramas (9(10)V99 = 12 bytes; 16 bytes como margem); usar buffers
# pequenos causaria overflow de heap quando o COBOL grava LK-EV-VALOR
# (12 bytes) e as incidencias.
_calcevent_args = [ctypes.create_string_buffer(16) for _ in range(10)]
_CALCEVENT(*(_calcevent_args))

_tax = ctypes.CDLL(_taxcalc_path)
_TAXCALC = _tax.TAXCALC
_TAXCALC.argtypes = [ctypes.c_char_p] * 5    # base, competencia, depend, inss, irrf
_TAXCALC.restype = None
# Invocacao unica p/ registrar TAXCALC no runtime (buffers de 16 bytes,
# seguros p/ os campos 9(10)V99 de saida = 12 bytes).
_taxcalc_args = [ctypes.create_string_buffer(16) for _ in range(5)]
_TAXCALC(*(_taxcalc_args))

_pay = ctypes.CDLL(_SO_PATH)


# --------------------------------------------------------------------------
# Struct ctypes espelhando o PAYCALC-IO (ordem exata do copybook)
# --------------------------------------------------------------------------
class Payroll(ctypes.Structure):
    _fields_ = [
        # ---- ENTRADA ----
        ("salario", ctypes.c_char * 12),        # LK-SALARIO 9(10)V99
        ("carga_horaria", ctypes.c_char * 6),   # LK-CARGA-HORARIA 9(4)V99
        ("depend", ctypes.c_char * 2),          # LK-DEPEND 9(2)
        ("he50", ctypes.c_char * 8),            # LK-HE50 9(6)V99
        ("he100", ctypes.c_char * 8),           # LK-HE100 9(6)V99
        ("faltas", ctypes.c_char * 8),          # LK-FALTAS 9(6)V99
        ("vt_custo", ctypes.c_char * 12),       # LK-VT-CUSTO 9(10)V99
        ("comissao", ctypes.c_char * 12),       # LK-COMISSAO 9(10)V99 (evento 007)
        ("dsr_dias_uteis", ctypes.c_char * 8),  # LK-DSR-DIAS-UTEIS 9(6)V99 (evento 008)
        ("dsr_dom_fer", ctypes.c_char * 8),     # LK-DSR-DOM-FER 9(6)V99 (evento 008)
        ("competencia", ctypes.c_char * 6),     # LK-COMPETENCIA 9(6)
        # ---- RESULTADO: PROVENTOS ----
        ("prov_salario", ctypes.c_char * 12),   # LK-PROV-SALARIO 9(10)V99
        ("prov_he50", ctypes.c_char * 12),      # LK-PROV-HE50
        ("prov_he100", ctypes.c_char * 12),     # LK-PROV-HE100
        ("prov_comissao", ctypes.c_char * 12),  # LK-PROV-COMISSAO (evento 007)
        ("prov_dsr", ctypes.c_char * 12),       # LK-PROV-DSR (evento 008)
        ("prov_total", ctypes.c_char * 14),     # LK-PROV-TOTAL 9(12)V99
        # ---- RESULTADO: DESCONTOS ----
        ("desc_inss", ctypes.c_char * 12),      # LK-DESC-INSS 9(10)V99
        ("desc_irrf", ctypes.c_char * 12),      # LK-DESC-IRRF
        ("desc_vt", ctypes.c_char * 12),        # LK-DESC-VT
        ("desc_faltas", ctypes.c_char * 12),    # LK-DESC-FALTAS
        ("desc_total", ctypes.c_char * 14),     # LK-DESC-TOTAL 9(12)V99
        # ---- RESULTADO: BASES ----
        ("base_inss", ctypes.c_char * 14),      # LK-BASE-INSS 9(12)V99
        ("base_irrf", ctypes.c_char * 14),      # LK-BASE-IRRF
        ("base_fgts", ctypes.c_char * 14),      # LK-BASE-FGTS
        # ---- RESULTADO: LIQUIDO ----
        ("liquido", ctypes.c_char * 14),        # LK-LIQUIDO 9(12)V99
    ]


_PAYCALC = _pay.PAYCALC
_PAYCALC.argtypes = [ctypes.POINTER(Payroll)]
_PAYCALC.restype = None


# --------------------------------------------------------------------------
# Conversores PIC -> Python
# --------------------------------------------------------------------------
def money_to_pic(value: Decimal, int_digits: int) -> bytes:
    """Decimal -> PIC 9(n)V99 (DISPLAY, int_digits + 2 bytes)."""
    cents = int((value * 100).quantize(Decimal("1"), ROUND_HALF_UP))
    return f"{cents:0{int_digits + 2}d}".encode("ascii")


def pic_to_cents(buf: bytes, int_digits: int) -> int:
    """PIC 9(n)V99 -> centavos (comparacao exata em inteiros)."""
    raw = buf[: int_digits + 2]
    int_part = int(raw[:int_digits])
    dec_part = int(raw[int_digits:])
    return int_part * 100 + dec_part


def call_payroll(salario, carga, depend, he50, he100, faltas, vt_custo,
                 comissao=0.0, dsr_dias_uteis=0.0, dsr_dom_fer=0.0,
                 competencia="202608") -> Payroll:
    """Monta a struct, chama PAYCALC e devolve a struct preenchida."""
    p = Payroll()
    p.salario = money_to_pic(Decimal(str(salario)), 10)
    p.carga_horaria = money_to_pic(Decimal(str(carga)), 4)
    p.depend = f"{depend:02d}".encode("ascii")
    p.he50 = money_to_pic(Decimal(str(he50)), 6)
    p.he100 = money_to_pic(Decimal(str(he100)), 6)
    p.faltas = money_to_pic(Decimal(str(faltas)), 6)
    p.vt_custo = money_to_pic(Decimal(str(vt_custo)), 10)
    p.comissao = money_to_pic(Decimal(str(comissao)), 10)
    p.dsr_dias_uteis = money_to_pic(Decimal(str(dsr_dias_uteis)), 6)
    p.dsr_dom_fer = money_to_pic(Decimal(str(dsr_dom_fer)), 6)
    p.competencia = competencia.encode("ascii")
    _PAYCALC(ctypes.byref(p))
    return p


# --------------------------------------------------------------------------
# Referencia independente (regras dos RFCs em Decimal)
# --------------------------------------------------------------------------
INSS_FAIXAS = [
    (Decimal("1500.00"), Decimal("0.075")),
    (Decimal("3000.00"), Decimal("0.09")),
    (Decimal("5000.00"), Decimal("0.12")),
    (None, Decimal("0.14")),
]
IRRF_FAIXAS = [
    (Decimal("2000.00"), Decimal("0.00"), Decimal("0.00")),
    (Decimal("4000.00"), Decimal("0.10"), Decimal("100.00")),
    (Decimal("6000.00"), Decimal("0.15"), Decimal("300.00")),
    (None, Decimal("0.225"), Decimal("700.00")),
]
DEP_DEDUCAO = Decimal("189.59")


def r2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), ROUND_HALF_UP)


def ref_inss(base: Decimal) -> Decimal:
    total = Decimal("0")
    restante = base
    anterior = Decimal("0")
    for limite, aliquota in INSS_FAIXAS:
        if restante <= 0:
            break
        if limite is None:
            total += restante * aliquota
            restante = Decimal("0")
        else:
            largura = limite - anterior
            parcela = min(restante, largura)
            total += parcela * aliquota
            restante -= parcela
            anterior = limite
    return total


def ref_irrf(base_inss: Decimal, inss: Decimal, depend: int) -> Decimal:
    base_irrf = base_inss - inss - DEP_DEDUCAO * Decimal(depend)
    if base_irrf <= 0:
        return Decimal("0")
    for limite, aliquota, deducao in IRRF_FAIXAS:
        if limite is None or base_irrf <= limite:
            return max(Decimal("0"), base_irrf * aliquota - deducao)
    return Decimal("0")


def ref_payroll(salario, carga, depend, he50, he100, faltas, vt_custo,
                comissao=0.0, dsr_dias_uteis=0.0, dsr_dom_fer=0.0):
    """Mesma cadeia do PAYCALC, em Decimal (para comparacao em centavos)."""
    d_sal, d_carga = Decimal(str(salario)), Decimal(str(carga))
    d_he50, d_he100 = Decimal(str(he50)), Decimal(str(he100))
    d_faltas, d_vt = Decimal(str(faltas)), Decimal(str(vt_custo))
    d_com = Decimal(str(comissao))
    d_dias, d_dom = Decimal(str(dsr_dias_uteis)), Decimal(str(dsr_dom_fer))

    # Proventos (eventos arredondados individualmente, como no CALCEVENT)
    prov_sal = d_sal
    prov_he50 = r2((d_sal / d_carga) * d_he50 * Decimal("1.5")) if d_he50 else Decimal("0")
    prov_he100 = r2((d_sal / d_carga) * d_he100 * Decimal("2.0")) if d_he100 else Decimal("0")
    prov_comissao = d_com
    # DSR sobre comissao (RFC-COMISSION/RFC-001 §7.1): comissao / dias uteis
    # x (domingos + feriados); divisor 0 -> 0 (mesma protecao do CALCEVENT).
    prov_dsr = (r2(d_com / d_dias * d_dom) if d_dias else Decimal("0"))
    prov_total = r2(prov_sal + prov_he50 + prov_he100 + prov_comissao + prov_dsr)

    # Base INSS = soma dos proventos que incidem INSS (007/008 S/S/S)
    base_inss = prov_total

    # INSS/IRRF (TAXCALC progressivo)
    inss_full = ref_inss(base_inss)
    inss = r2(inss_full)
    irrf = r2(ref_irrf(base_inss, inss_full, depend))

    # Descontos variaveis
    desc_vt = r2(min(d_sal * Decimal("0.06"), d_vt)) if d_vt else Decimal("0")
    desc_faltas = r2((d_sal / Decimal("30")) * d_faltas) if d_faltas else Decimal("0")

    desc_total = r2(inss + irrf + desc_vt + desc_faltas)

    # Bases
    base_irrf = max(Decimal("0"), r2(base_inss - inss - DEP_DEDUCAO * Decimal(depend)))
    base_fgts = base_inss

    liquido = max(Decimal("0"), r2(prov_total - desc_total))
    return {
        "prov_salario": prov_sal, "prov_he50": prov_he50, "prov_he100": prov_he100,
        "prov_comissao": prov_comissao, "prov_dsr": prov_dsr,
        "prov_total": prov_total,
        "desc_inss": inss, "desc_irrf": irrf,
        "desc_vt": desc_vt, "desc_faltas": desc_faltas, "desc_total": desc_total,
        "base_inss": base_inss, "base_irrf": base_irrf, "base_fgts": base_fgts,
        "liquido": liquido,
    }


FIELD_WIDTHS = {
    "prov_salario": 10, "prov_he50": 10, "prov_he100": 10, "prov_comissao": 10,
    "prov_dsr": 10, "prov_total": 12, "desc_inss": 10, "desc_irrf": 10,
    "desc_vt": 10, "desc_faltas": 10, "desc_total": 12, "base_inss": 12,
    "base_irrf": 12, "base_fgts": 12, "liquido": 12,
}


def result_cents(p: Payroll) -> dict:
    out = {}
    for name, int_digits in FIELD_WIDTHS.items():
        out[name] = pic_to_cents(getattr(p, name), int_digits)
    return out


# --------------------------------------------------------------------------
# Testes
# --------------------------------------------------------------------------
class TestPaycalcCtypes(unittest.TestCase):
    def test_exemplo_documentado(self):
        """Caso dourado do EXEMPLO-competencia.md: 4.500 + 10h HE50 + 2 faltas + 1 dep."""
        p = call_payroll(4500.00, 220.00, 1, 10.00, 0.00, 2.00, 0.00,
                         competencia="202608")
        got = result_cents(p)

        esperado = {
            "prov_salario": 450000,   # R$ 4.500,00
            "prov_he50": 30682,       # R$ 306,82
            "prov_he100": 0,
            "prov_comissao": 0,       # sem comissao no caso dourado
            "prov_dsr": 0,            # sem DSR (sem comissao)
            "prov_total": 480682,     # R$ 4.806,82
            "desc_inss": 46432,       # R$ 464,32
            "desc_irrf": 32294,       # R$ 322,94
            "desc_vt": 0,
            "desc_faltas": 30000,     # R$ 300,00
            "desc_total": 108726,     # R$ 1.087,26
            "base_inss": 480682,      # R$ 4.806,82
            "base_irrf": 415291,      # R$ 4.152,91
            "base_fgts": 480682,      # R$ 4.806,82
            "liquido": 371956,        # R$ 3.719,56
        }
        self.assertEqual(got, esperado)

    def test_vt_limitado_ao_custo_real(self):
        """VT = 6% (270,00) limitado ao custo real de 240,00 -> 240,00."""
        p = call_payroll(4500.00, 220.00, 1, 10.00, 0.00, 2.00, 240.00,
                         competencia="202608")
        got = result_cents(p)
        self.assertEqual(got["desc_vt"], 24000)
        # Desconto total 1.087,26 + 240,00 = 1.327,26
        self.assertEqual(got["desc_total"], 132726)
        self.assertEqual(got["liquido"], 371956 - 24000)

    def test_vt_acima_do_teto_usa_6pc(self):
        """Custo real alto (500,00) -> VT = 6% = 270,00 (nao o custo)."""
        p = call_payroll(4500.00, 220.00, 1, 10.00, 0.00, 2.00, 500.00,
                         competencia="202608")
        got = result_cents(p)
        self.assertEqual(got["desc_vt"], 27000)

    def test_he100(self):
        """HE 100%: 5h -> (4.500/220) x 5 x 2 = 204,55."""
        p = call_payroll(4500.00, 220.00, 0, 0.00, 5.00, 0.00, 0.00,
                         competencia="202608")
        got = result_cents(p)
        self.assertEqual(got["prov_he100"], 20455)
        self.assertEqual(got["prov_total"], 470455)

    def test_comissao_evento7(self):
        """Evento 007: comissao apurada (116,50) soma aos proventos e a base INSS."""
        p = call_payroll(4500.00, 220.00, 1, 10.00, 0.00, 2.00, 0.00, 116.50)
        got = result_cents(p)
        self.assertEqual(got["prov_comissao"], 11650)
        # salario 4.500 + HE50 306,82 + comissao 116,50 = 4.923,32
        self.assertEqual(got["prov_total"], 492332)
        self.assertEqual(got["base_inss"], 492332)

    def test_comissao_compoe_inss_irrf_fgts(self):
        """Comissao incide S/S/S: sem comissao vs. com comissao mudam INSS/IRRF/base FGTS."""
        p0 = call_payroll(4500.00, 220.00, 0, 0.00, 0.00, 0.00, 0.00)
        p1 = call_payroll(4500.00, 220.00, 0, 0.00, 0.00, 0.00, 0.00, 500.00)
        g0, g1 = result_cents(p0), result_cents(p1)
        self.assertEqual(g0["prov_comissao"], 0)
        self.assertEqual(g1["prov_comissao"], 50000)
        self.assertGreater(g1["desc_inss"], g0["desc_inss"])
        self.assertGreater(g1["desc_irrf"], g0["desc_irrf"])
        self.assertEqual(g1["base_fgts"], 500000)
        self.assertEqual(g1["liquido"], 500000 - g1["desc_total"])

    def test_dsr_sobre_comissao(self):
        """008: comissao 2.000, dias uteis 26, dom/fer 4 -> DSR 307,69 (RFC-001 §4.1)."""
        p = call_payroll(4500.00, 220.00, 1, 0.00, 0.00, 0.00, 0.00,
                         comissao=2000.00, dsr_dias_uteis=26, dsr_dom_fer=4)
        got = result_cents(p)
        self.assertEqual(got["prov_comissao"], 200000)
        self.assertEqual(got["prov_dsr"], 30769)      # 2.000 / 26 x 4
        self.assertEqual(got["prov_total"], 680769)    # 4.500 + 2.000 + 307,69
        self.assertEqual(got["base_inss"], 680769)     # DSR incide S/S/S

    def test_dsr_sem_comissao_zerado(self):
        """008 com comissao 0 -> DSR 0 (nada a refletir)."""
        p = call_payroll(4500.00, 220.00, 0, 0.00, 0.00, 0.00, 0.00,
                         comissao=0.00, dsr_dias_uteis=26, dsr_dom_fer=4)
        got = result_cents(p)
        self.assertEqual(got["prov_dsr"], 0)
        self.assertEqual(got["prov_total"], 450000)

    def test_zero_entrada(self):
        """Tudo zero -> folha zerada."""
        p = call_payroll(0.00, 220.00, 0, 0.00, 0.00, 0.00, 0.00,
                         competencia="202608")
        got = result_cents(p)
        self.assertEqual(got, {k: 0 for k in got})

    def test_bateria_contra_referencia(self):
        """Varredura ampla: PAYCALC deve bater com a referencia Decimal."""
        casos = [
            (4500.00, 220.00, 1, 10.00, 0.00, 2.00, 0.00, 0.00,
             0.00, 0.00),            # exemplo
            (4500.00, 220.00, 1, 10.00, 5.00, 2.00, 240.00, 116.50,
             0.00, 0.00),            # HE100 + VT + comissao
            (4500.00, 220.00, 1, 0.00, 0.00, 0.00, 0.00, 2000.00,
             26.00, 4.00),           # comissao + DSR (RFC-001 §4.1)
            (2200.00, 200.00, 0, 8.00, 0.00, 1.00, 0.00, 0.00,
             0.00, 0.00),
            (8000.00, 220.00, 3, 20.00, 10.00, 0.00, 400.00, 1000.00,
             25.00, 5.00),           # comissao alta + DSR 25/5
            (1500.00, 180.00, 0, 0.00, 0.00, 0.00, 0.00, 0.00,
             0.00, 0.00),            # so base, isento
            (5000.00, 220.00, 2, 0.00, 4.00, 5.00, 300.00, 250.75,
             26.00, 4.00),
            (9999.99, 220.00, 0, 40.00, 20.00, 7.00, 600.00, 5000.00,
             25.00, 4.00),           # teto INSS ultrapassado + DSR
        ]
        for caso in casos:
            with self.subTest(caso=caso):
                p = call_payroll(*caso, competencia="202608")
                got = result_cents(p)
                esp = ref_payroll(*caso)
                for name, int_digits in FIELD_WIDTHS.items():
                    esperado_cents = int(
                        (esp[name] * 100).quantize(Decimal("1"), ROUND_HALF_UP)
                    )
                    self.assertEqual(got[name], esperado_cents,
                                     f"{name} divergente p/ {caso}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
