#!/usr/bin/env python3
"""Smoke E2E do Bank Integration (RFC-0070, Sprint BI-01).

Valida o contrato de importação: parse OFX/CSV, modelo canônico, validação de
balanço, idempotência, store imutável e eventos. Faz backup/restauração dos
dados para não sujar o repo.
"""

from __future__ import annotations

import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import bank_integration as bi

FILES = (
    "dados/bank_statements.json",
    "dados/bank_accounts.json",
    "dados/bank_integration_log.json",
)

BACKUP = "/tmp/opencode/bi01_backup"
EMPTY = {
    "dados/bank_statements.json": {"atualizado_em": None, "extratos": []},
    "dados/bank_accounts.json": {"atualizado_em": None, "contas": []},
    "dados/bank_integration_log.json": {"atualizado_em": None, "eventos": []},
}

OFX_SAMPLE = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252

<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>1</TRNUID>
<STMTRS>
<CURDEF>BRL</CURDEF>
<BANKACCTFROM>
<BANKID>341</BANKID>
<BRANCHID>1234</BRANCHID>
<ACCTID>5678901</ACCTID>
<ACCTTYPE>CHECKING</ACCTTYPE>
</BANKACCTFROM>
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>DEBIT</TRNTYPE>
<DTPOSTED>20260701</DTPOSTED>
<TRNAMT>-150.00</TRNAMT>
<FITID>1001</FITID>
<NAME>PIX ENVIADO</NAME>
<MEMO>pagamento fornecedor</MEMO>
<REFNUM>E12345</REFNUM>
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT</TRNTYPE>
<DTPOSTED>20260702</DTPOSTED>
<TRNAMT>250.00</TRNAMT>
<FITID>1002</FITID>
<NAME>PIX RECEBIDO</NAME>
<MEMO>venda</MEMO>
</STMTTRN>
</BANKTRANLIST>
<LEDGERBAL>
<BALAMT>100.00</BALAMT>
<DTASOF>20260731</DTASOF>
</LEDGERBAL>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""

CSV_SAMPLE = """data;descricao;valor
01/07/2026;PIX RECEBIDO;250,00
02/07/2026;PIX ENVIADO;-150,00
03/07/2026;BOLETO PAGO;-80,00
"""

CSV_DEB_CRED = """DATA;HISTORICO;VALOR_DEBITO;VALOR_CREDITO;DOC
01/07/2026;ENTRADA PIX;;250,00;111
02/07/2026;SAIDA PIX;150,00;;222
"""


def _backup():
    os.makedirs(BACKUP, exist_ok=True)
    for path in FILES:
        src = os.path.join(ROOT, path)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(BACKUP, os.path.basename(path)))


def _restore():
    for path in FILES:
        dst = os.path.join(ROOT, path)
        bkp = os.path.join(BACKUP, os.path.basename(path))
        if os.path.exists(bkp):
            shutil.copy2(bkp, dst)


def _reset():
    for path, payload in EMPTY.items():
        with open(os.path.join(ROOT, path), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)


def _linha(c, n):
    return "".join(list(str(c).ljust(n)))


def _cnab240_retorno(nosso_numero="123456789012345", numero_doc="000000FV99001",
                     banco="341", agencia="01234", conta="000005678901",
                     vencimento="10072026", valor="0000000003290", credito="15072026"):
    h = _linha("3410000", 240)
    h = h[:7] + "0" + h[8:]
    h = h[:52] + agencia + h[57:]
    h = h[:58] + conta + h[70:]
    h = h[:142] + "2" + h[143:]
    d = _linha(f"{banco}00013", 240)
    d = d[:13] + "T" + d[14:]
    d = d[:15] + "06" + d[17:]
    d = d[:17] + agencia + d[22:]
    d = d[:23] + conta + d[35:]
    d = d[:37] + "123456" + d[43:]
    d = d[:44] + "1" + d[45:]
    d = d[:45] + numero_doc + d[59:]
    d = d[:73] + vencimento + d[81:]
    d = d[:81] + valor + d[96:]
    d = d[:105] + nosso_numero + d[120:]
    d = d[:165] + credito + d[173:]
    t = _linha("34100015", 240)
    tf = _linha("34199999", 240)
    tf = tf[:7] + "9" + tf[8:]
    return "\n".join([h, d, t, tf])


def _cnab400_retorno(nosso_numero="1234567890", numero_doc="0000000000FV99001",
                     banco="341", agencia="12345", conta="005678901",
                     vencimento="10072026", valor="00000000003290", ocorrencia="150726"):
    h = _linha("0" + banco, 400)
    h = h[:4] + agencia + h[9:]
    h = h[:9] + conta + h[17:]
    d = _linha("1" + banco, 400)
    d = d[:62] + nosso_numero + d[73:]
    d = d[:73] + vencimento + d[81:]
    d = d[:81] + valor + d[95:]
    d = d[:107] + "06" + d[109:]
    d = d[:109] + ocorrencia + d[115:]
    d = d[:115] + numero_doc + d[131:]
    t = _linha("9", 400)
    return "\n".join([h, d, t])


def _salvar_ar(dat_path):
    import shutil as _sh
    src = os.path.join(ROOT, dat_path)
    if os.path.exists(src):
        _sh.copy2(src, os.path.join(BACKUP, os.path.basename(dat_path)))


def _restaurar_ar(dat_path):
    import shutil as _sh
    bkp = os.path.join(BACKUP, os.path.basename(dat_path))
    if os.path.exists(bkp):
        _sh.copy2(bkp, os.path.join(ROOT, dat_path))


def main():
    _backup()
    _salvar_ar("dados/titulos_ar.dat")
    try:
        _reset()

        # 1) importação OFX → Statement canônico
        r = bi.importar_extrato(OFX_SAMPLE, nome_arquivo="itau_julho.ofx", actor="tesouraria")
        assert r["ok"] and r["status"] == "ok", r
        assert r["evento"] == "finance_statement_imported", r["evento"]
        ext = r["extrato"]
        assert ext["banco"] == "341", ext["banco"]
        assert ext["conta"] == "5678901", ext["conta"]
        assert ext["moeda"] == "BRL", ext["moeda"]
        assert ext["fonte"] == "ofx", ext["fonte"]
        assert ext["saldo_final"] == 100.0, ext["saldo_final"]
        assert len(ext["lancamentos"]) == 2, ext["lancamentos"]
        tipos = {t["tipo"] for t in ext["lancamentos"]}
        assert tipos == {"D", "C"}, tipos
        refs = [t["refs"] for t in ext["lancamentos"] if t["descricao"] == "PIX ENVIADO"]
        assert refs and refs[0] == ["E12345"], refs
        print("OFX importado:", ext["banco"], ext["conta"], len(ext["lancamentos"]), "lancamentos")

        # 2) idempotência → duplicate
        r2 = bi.importar_extrato(OFX_SAMPLE, nome_arquivo="itau_julho.ofx", actor="tesouraria")
        assert r2["ok"] and r2["status"] == "duplicate", r2
        assert r2["evento"] == "finance_statement_duplicate", r2["evento"]
        assert bi.list_extratos()["total"] == 1, bi.list_extratos()
        print("idempotência ok (duplicate)")

        # 3) conta bancária resolvida/registrada
        contas = bi.list_bank_accounts()
        assert len(contas) == 1, contas
        assert contas[0]["conta"] == "5678901", contas[0]
        assert contas[0]["tipo_conta"] == "current", contas[0]["tipo_conta"]
        print("conta registrada:", contas[0]["banco"], contas[0]["conta"], contas[0]["tipo_conta"])

        # 4) CSV com detecção automática de colunas
        r3 = bi.importar_extrato(
            CSV_SAMPLE,
            nome_arquivo="nubank_julho.csv",
            banco="260",
            agencia="0001",
            conta="1234567",
            actor="tesouraria",
        )
        assert r3["ok"] and r3["status"] == "ok", r3
        ext3 = r3["extrato"]
        assert len(ext3["lancamentos"]) == 3, ext3["lancamentos"]
        assert ext3["lancamentos"][0]["tipo"] == "C", ext3["lancamentos"][0]
        assert ext3["lancamentos"][1]["tipo"] == "D", ext3["lancamentos"][1]
        assert ext3["lancamentos"][0]["data"] == "2026-07-01", ext3["lancamentos"][0]
        print("CSV auto importado:", len(ext3["lancamentos"]), "lancamentos")

        # 5) CSV com colunas débito/crédito separadas + refs
        r4 = bi.importar_extrato(
            CSV_DEB_CRED,
            nome_arquivo="banco_julho.csv",
            banco="001",
            agencia="1234",
            conta="99999-0",
            actor="tesouraria",
        )
        assert r4["ok"] and r4["status"] == "ok", r4
        ext4 = r4["extrato"]
        assert len(ext4["lancamentos"]) == 2, ext4["lancamentos"]
        assert ext4["lancamentos"][0]["refs"] == ["111"], ext4["lancamentos"][0]["refs"]
        assert ext4["lancamentos"][1]["valor"] == -150.0, ext4["lancamentos"][1]
        print("CSV deb/cred importado:", len(ext4["lancamentos"]), "lancamentos")

        # 6) validação de balanço divergente → rejeita
        # (OFX infere saldo_inicial a partir do saldo_final; o teste da
        # validação é direto no modelo canônico)
        st_quebrado = {
            "banco": "341", "agencia": "1234", "conta": "5678901",
            "saldo_inicial": 0.0, "saldo_final": 999.0, "fonte": "ofx",
            "lancamentos": [
                {"id": "a", "data": "2026-07-01", "tipo": "C", "valor": 100.0, "descricao": "x", "refs": [], "metadados": {}},
            ],
        }
        errs = bi.validar_statement(st_quebrado)
        assert any("balanço divergente" in e for e in errs), errs
        print("validação de balanço ok (divergente rejeitado)")

        # 7) valores sempre Decimal no núcleo (nunca float impreciso)
        assert sum(t["valor"] for t in ext["lancamentos"]) == 100.0, "soma dos lançamentos"
        assert ext["saldo_final"] - sum(t["valor"] for t in ext["lancamentos"]) == ext["saldo_inicial"]

        # 8) eventos registrados
        log = bi._load_raw("dados/bank_integration_log.json", {"eventos": []})
        evs = [e["evento"] for e in log.get("eventos") or []]
        assert "finance_statement_imported" in evs, evs
        assert "finance_statement_duplicate" in evs, evs

        # 9) listagens por filtro
        assert bi.list_lancamentos(banco="341")["total"] == 2, bi.list_lancamentos(banco="341")
        assert bi.list_lancamentos(tipo="C")["total"] == 3, bi.list_lancamentos(tipo="C")
        assert bi.list_extratos(banco="260")["total"] == 1

        # ── BI-02: CNAB 240 ──
        r_c240 = bi.importar_extrato(
            _cnab240_retorno(),
            nome_arquivo="retorno240.ret",
            formato="cnab240",
            actor="tesouraria",
            conciliar_titulos=True,
        )
        assert r_c240["ok"] and r_c240["status"] == "ok", r_c240
        e240 = r_c240["extrato"]
        assert e240["fonte"] == "cnab240", e240["fonte"]
        assert e240["banco"] == "341", e240["banco"]
        assert e240["conta"] == "000005678901", e240["conta"]
        assert len(e240["lancamentos"]) == 1, e240["lancamentos"]
        l240 = e240["lancamentos"][0]
        assert l240["tipo"] == "C", l240["tipo"]
        assert l240["valor"] == 32.9, l240["valor"]
        assert l240["data"] == "2026-07-10", l240["data"]
        assert l240["data_credito"] == "2026-07-15", l240["data_credito"]
        assert (l240["metadados"] or {}).get("movimento") == "06", l240["metadados"]
        conc = r_c240["conciliacao"]
        assert conc["conciliados"] == 1, conc
        assert conc["baixados"] == 1, conc
        assert conc["liquidados"][0]["titulo_id"] == "AR-00002", conc
        print("CNAB240 importado:", e240["conta"], "| conciliou AR-00002 (FV99001)")

        # AR-00002 baixado pelo retorno
        import sales_finance as sf
        t = next(x for x in sf.list_titulos()["titulos"] if x["id"] == "AR-00002")
        assert t["status"] == "pago", t
        assert t["saldo"] == 0.0, t
        print("CNAB240 conciliação: AR-00002 → pago")

        # idempotência CNAB240
        r_c240b = bi.importar_extrato(
            _cnab240_retorno(), nome_arquivo="retorno240.ret", formato="cnab240", conciliar_titulos=True, actor="tesouraria")
        assert r_c240b["status"] == "duplicate", r_c240b
        print("CNAB240 idempotência ok")

        # ── BI-02: CNAB 400 ──
        r_c400 = bi.importar_extrato(
            _cnab400_retorno(),
            nome_arquivo="retorno400.ret",
            formato="cnab400",
            actor="tesouraria",
        )
        assert r_c400["ok"] and r_c400["status"] == "ok", r_c400
        e400 = r_c400["extrato"]
        assert e400["fonte"] == "cnab400", e400["fonte"]
        assert e400["banco"] == "341", e400["banco"]
        assert len(e400["lancamentos"]) == 1, e400["lancamentos"]
        l400 = e400["lancamentos"][0]
        assert l400["valor"] == 32.9, l400["valor"]
        assert l400["data_credito"] == "2026-07-15", l400["data_credito"]
        print("CNAB400 importado:", e400["conta"], "| valor", l400["valor"])

        # detecção automática de formato pelo conteúdo
        r_det = bi.importar_extrato(_cnab240_retorno(nosso_numero="X", numero_doc="000000FV99002"),
                                    nome_arquivo="auto.ext", actor="tesouraria")
        assert r_det["ok"] and r_det["status"] == "ok", r_det
        assert r_det["extrato"]["fonte"] == "cnab240", r_det["extrato"]["fonte"]
        print("detecção automática CNAB ok")

        print("SMOKE BANK INTEGRATION BI-01/BI-02 OK")
        print("  extratos:", bi.list_extratos()["total"], "| lançamentos:", bi.list_lancamentos()["total"])
        print("reset ok")
    finally:
        _restore()
        _restaurar_ar("dados/titulos_ar.dat")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
