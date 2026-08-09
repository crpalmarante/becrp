#!/usr/bin/env python3
"""Teste Fase 3 — regras progressivas de INSS/IRRF do TAXCALC via ctypes.

Valida o modulo TAXCALC (taxcalc.so) chamado via ctypes com o contrato
inalterado (taxcalc-io.cpy):
  (LK-BASE, LK-COMPETENCIA, LK-DEPEND) -> (LK-INSS, LK-IRRF)

Regras implementadas (RFC-005, tabelas ilustrativas):
  * INSS progressivo por faixa (7,5% / 9% / 12% / 14%).
  * Base IRRF = base INSS - INSS - deducao por dependente (189,59).
  * IRRF progressivo com deducao da faixa (10%-100 / 15%-300 / 22,5%-700).

Estrategia:
  * Uma implementacao de referencia em Decimal (regra por regra do RFC-005)
    compara o resultado do COBOL para uma bateria de bases de calculo.
  * Casos dourados fixos (ex.: o exemplo documentado em
    docs-tecnicos/EXEMPLO-competencia.md: base 4.806,82 + 1 dependente
    -> INSS 464,32 / IRRF 322,94).

Regra critica do PLAN_ERP.md secao 4.1: libcob inicializada UMA vez no
startup; .so carregado durante toda a vida do processo.

Mapeamento PIC -> ctypes (DISPLAY ASCII):
  * PIC 9(10)V99  -> 12 bytes (10 digitos inteiros + 2 decimais)
  * PIC 9(6)      ->  6 bytes (competencia AAAAMM)
  * PIC 9(2)      ->  2 bytes (dependentes)
"""
import ctypes
import ctypes.util
import os
import unittest
from decimal import Decimal, ROUND_HALF_UP

# --------------------------------------------------------------------------
# Startup: carrega libcob UMA vez (regra PLAN_ERP 4.1) e o taxcalc.so
# --------------------------------------------------------------------------
_libcob_path = ctypes.util.find_library("cob") or "libcob.so.4"
_libcob = ctypes.CDLL(_libcob_path)
_libcob.cob_init.argtypes = [ctypes.c_int, ctypes.c_void_p]
_libcob.cob_init.restype = None
_libcob.cob_init(0, None)          # UMA vez, no startup do processo

_SO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "cobol")
_SO_PATH = os.path.join(_SO_DIR, "taxcalc.so")
if not os.path.exists(_SO_PATH):
    raise RuntimeError(
        f"taxcalc.so nao encontrado em {_SO_PATH}. "
        "Compile antes: cd cobol && cobc -m -o taxcalc.so taxcalc.cbl"
    )
_tax = ctypes.CDLL(_SO_PATH)
_TAXCALC = _tax.TAXCALC
_TAXCALC.argtypes = [ctypes.c_char_p] * 5  # base, competencia, depend, inss, irrf
_TAXCALC.restype = None


# --------------------------------------------------------------------------
# Conversores PIC -> Python (mesmo padrao do test_ctypes_paycalc.py)
# --------------------------------------------------------------------------
def money_to_pic(value: Decimal) -> bytes:
    """1234.56 -> b'000000123456' (PIC 9(10)V99, 12 bytes)."""
    cents = int((value * 100).quantize(Decimal("1"), ROUND_HALF_UP))
    return f"{cents:012d}".encode("ascii")


def pic_to_cents(buf: bytes) -> int:
    """b'000000123456' -> 123456 centavos (comparacao exata em inteiros)."""
    raw = buf[:12]
    int_part = int(raw[:10])
    dec_part = int(raw[10:12])
    return int_part * 100 + dec_part


def competencia_to_pic(ano_mes: str) -> bytes:
    """'202608' -> b'202608' (PIC 9(6))."""
    return ano_mes.encode("ascii")


def depend_to_pic(n: int) -> bytes:
    """2 -> b'02' (PIC 9(2))."""
    return f"{n:02d}".encode("ascii")


def call_taxcalc(base: Decimal, competencia: str, depend: int):
    """Chama TAXCALC e retorna (inss_centavos, irrf_centavos)."""
    base_b = money_to_pic(base)
    comp_b = competencia_to_pic(competencia)
    dep_b = depend_to_pic(depend)
    inss = ctypes.create_string_buffer(13)  # 12 bytes + nul
    irrf = ctypes.create_string_buffer(13)

    _TAXCALC(base_b, comp_b, dep_b, inss, irrf)

    return pic_to_cents(inss.value), pic_to_cents(irrf.value)


# --------------------------------------------------------------------------
# Referencia independente (regras do RFC-005 em Decimal)
# --------------------------------------------------------------------------
INSS_FAIXAS = [
    (Decimal("1500.00"), Decimal("0.075")),
    (Decimal("3000.00"), Decimal("0.09")),
    (Decimal("5000.00"), Decimal("0.12")),
    (None, Decimal("0.14")),  # acima de 5.000,00 (sem teto na tabela ilustrativa)
]
IRRF_FAIXAS = [
    (Decimal("2000.00"), Decimal("0.00"), Decimal("0.00")),   # isento
    (Decimal("4000.00"), Decimal("0.10"), Decimal("100.00")),
    (Decimal("6000.00"), Decimal("0.15"), Decimal("300.00")),
    (None, Decimal("0.225"), Decimal("700.00")),
]
DEP_DEDUCAO = Decimal("189.59")


def ref_inss(base: Decimal) -> Decimal:
    """INSS progressivo por faixa, sem arredondamento intermediario."""
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
    """IRRF = (base IRRF x aliquota) - deducao da faixa."""
    base_irrf = base_inss - inss - DEP_DEDUCAO * Decimal(depend)
    if base_irrf <= 0:
        return Decimal("0")
    for limite, aliquota, deducao in IRRF_FAIXAS:
        if limite is None or base_irrf <= limite:
            return max(Decimal("0"), base_irrf * aliquota - deducao)
    return Decimal("0")


def ref_cents(base: Decimal, depend: int) -> tuple:
    """Valores esperados em centavos (arredondamento so no final)."""
    inss_full = ref_inss(base)
    inss_cents = int(inss_full.quantize(Decimal("0.01"), ROUND_HALF_UP) * 100)
    irrf_full = ref_irrf(base, inss_full, depend)
    irrf_cents = int(irrf_full.quantize(Decimal("0.01"), ROUND_HALF_UP) * 100)
    return inss_cents, irrf_cents


# --------------------------------------------------------------------------
# Testes
# --------------------------------------------------------------------------
class TestTaxcalcCtypes(unittest.TestCase):
    def test_exemplo_documentado_4806_82_1_dep(self):
        """Caso dourado do EXEMPLO-competencia.md: 4.806,82 + 1 dep."""
        inss, irrf = call_taxcalc(Decimal("4806.82"), "202608", 1)
        self.assertEqual(inss, 46432)  # R$ 464,32
        self.assertEqual(irrf, 32294)  # R$ 322,94

    def test_faixas_inss(self):
        """INSS progressivo: verifica cada faixa com valores validados."""
        casos = [
            # base, dep, inss esperado (centavos), irrf esperado (centavos)
            (Decimal("500.00"), 0, 3750, 0),       # so faixa 1: 500 x 7,5%
            (Decimal("1500.00"), 0, 11250, 0),     # topo faixa 1: 1.500 x 7,5%
            (Decimal("1500.01"), 0, 11250, 0),     # 0,01 na faixa 2 (9% de 0,01 = 0)
            (Decimal("2500.00"), 0, 20250, 12975), # 112,50 + 1.000 x 9% = 202,50
            (Decimal("4000.00"), 0, 36750, 26325), # + 1.000 x 12% = 367,50; IRRF 10%
            (Decimal("6000.00"), 0, 62750, 50588), # + 1.000 x 14% = 627,50; IRRF 15%
        ]
        for base, dep, inss_esp, irrf_esp in casos:
            with self.subTest(base=base):
                inss, irrf = call_taxcalc(base, "202608", dep)
                self.assertEqual(inss, inss_esp, f"INSS p/ base {base}")
                self.assertEqual(irrf, irrf_esp, f"IRRF p/ base {base}")

    def test_faixas_irrf(self):
        """IRRF: isento, faixas 10%, 15% e 22,5% com deducao da faixa."""
        casos = [
            (Decimal("2000.00"), 0, 0),      # base IRRF <= 2.000 -> isento
            (Decimal("2200.00"), 0, 10245),  # base IRRF 2.024,50 -> 10% - 100
            (Decimal("3000.00"), 0, 17525),  # base IRRF 2.752,50 -> 10% - 100
            (Decimal("4300.00"), 0, 28965),  # base IRRF 3.896,50 -> 10% - 100
            (Decimal("7000.00"), 0, 70231),  # base IRRF 6.232,50 -> 22,5% - 700
        ]
        for base, dep, irrf_esp in casos:
            with self.subTest(base=base):
                _inss, irrf = call_taxcalc(base, "202608", dep)
                self.assertEqual(irrf, irrf_esp, f"IRRF p/ base {base}")

    def test_dependentes_reduzem_irrf(self):
        """Dependente reduz a base IRRF em 189,59 por dependente."""
        inss0, irrf0 = call_taxcalc(Decimal("4806.82"), "202608", 0)
        inss1, irrf1 = call_taxcalc(Decimal("4806.82"), "202608", 1)
        inss2, irrf2 = call_taxcalc(Decimal("4806.82"), "202608", 2)

        # INSS nao depende de dependentes
        self.assertEqual(inss0, inss1)
        self.assertEqual(inss1, inss2)

        # IRRF diminui com mais dependentes
        self.assertGreater(irrf0, irrf1)
        self.assertGreater(irrf1, irrf2)

    def test_competencia_aceita_qualquer_valor(self):
        """A competencia e aceita (tabela unica ilustrativa na Fase 3)."""
        inss_a, irrf_a = call_taxcalc(Decimal("4806.82"), "202501", 1)
        inss_b, irrf_b = call_taxcalc(Decimal("4806.82"), "202608", 1)
        self.assertEqual((inss_a, irrf_a), (inss_b, irrf_b))

    def test_bateria_contra_referencia(self):
        """Varredura ampla: COBOL deve bater com a referencia Decimal."""
        bases = [
            Decimal("0.01"), Decimal("1499.99"), Decimal("1500.00"),
            Decimal("1500.01"), Decimal("2999.99"), Decimal("3000.00"),
            Decimal("3000.01"), Decimal("4999.99"), Decimal("5000.00"),
            Decimal("5000.01"), Decimal("7500.00"), Decimal("9999.99"),
            Decimal("12345.67"), Decimal("4806.82"),
        ]
        for dep in (0, 1, 3):
            for base in bases:
                with self.subTest(base=base, dep=dep):
                    inss, irrf = call_taxcalc(base, "202608", dep)
                    inss_esp, irrf_esp = ref_cents(base, dep)
                    self.assertEqual(inss, inss_esp, f"INSS p/ base {base} dep {dep}")
                    self.assertEqual(irrf, irrf_esp, f"IRRF p/ base {base} dep {dep}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
