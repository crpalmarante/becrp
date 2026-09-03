"""Integration tests for accounts payable (AP) creation from NF-e receiving.

Tests the flow: receiving complete → purchase_finance.create_from_receiving → AP titles.
Covers duplicatas, single-parcel, idempotency, and value calculation.
"""
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import purchase_finance
import receiving_mvp
import nfe_monitor

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MONITOR_FILE = os.path.join(DATA_DIR, "nfe_monitor.json")
RECEIVINGS_FILE = os.path.join(DATA_DIR, "receivings.json")
AP_FILE = os.path.join(DATA_DIR, "titulos_ap.json")

_counter = 0


def _next_id():
    global _counter
    _counter += 1
    return 9000 + _counter


def _next_chave():
    prefix = "43260762832155000141550010000"
    num_part = f"{_counter + 8500:015d}"
    return (prefix + num_part)[:44]


def _save_originals():
    _orig = {}
    for f in (MONITOR_FILE, RECEIVINGS_FILE, AP_FILE):
        if os.path.exists(f):
            with open(f) as fh:
                _orig[f] = json.load(fh)
        else:
            _orig[f] = {}
    return _orig


def _restore(originals):
    for f, content in originals.items():
        os.makedirs(os.path.dirname(f), exist_ok=True)
        with open(f, "w") as fh:
            json.dump(content, fh, ensure_ascii=False, indent=2)


def _remove_ap_entries(rids):
    """Remove AP titles by receiving_id."""
    data = purchase_finance._load()
    data["titulos"] = [t for t in data.get("titulos", [])
                       if t.get("receiving_id") not in rids]
    purchase_finance._save(data)


def _make_receiving(**overrides):
    """Build a minimal receiving dict for direct AP testing."""
    rid = _next_id()
    chave = f"4326076283215500014155001000000{rid:010d}"
    base = {
        "id": rid,
        "status": "completed",
        "origem": "nfe",
        "estabelecimento_id": "matriz",
        "fornecedor_id": "bp_test",
        "fornecedor_nome": "Fornecedor Teste",
        "fornecedor_cnpj": "11222333000181",
        "documento_ref": chave,
        "nfe": {
            "chave": chave,
            "numero": str(900 + rid),
            "serie": "1",
            "valor_total": 500.00,
            "fornecedor_cnpj": "11222333000181",
            "duplicatas": [],
        },
        "items": [],
    }
    base.update(overrides)
    return base


def _make_nfe_xml(chave, numero, items_xml, duplicatas=None,
                  cnpj_emitente="11222333000181", cnpj_dest="62832155000141"):
    items_block = ""
    for i, item in enumerate(items_xml, 1):
        items_block += f"""
      <det nItem="{i}">
        <prod>
          <cProd>{item.get('cProd', f'PROD{i:03d}')}</cProd>
          <cEAN>{item.get('cEAN', '')}</cEAN>
          <xProd>{item.get('xProd', f'Produto {i}')}</xProd>
          <NCM>{item.get('NCM', '00000000')}</NCM>
          <CFOP>5102</CFOP>
          <uCom>{item.get('uCom', 'UN')}</uCom>
          <qCom>{item.get('qCom', '10')}</qCom>
          <vUnCom>{item.get('vUnCom', '10.00')}</vUnCom>
          <vProd>{item.get('vProd', '100.00')}</vProd>
          <cEANTrib>{item.get('cEAN', '')}</cEANTrib>
          <uTrib>{item.get('uCom', 'UN')}</uTrib>
          <qTrib>{item.get('qCom', '10')}</qTrib>
          <vUnTrib>{item.get('vUnCom', '10.00')}</vUnTrib>
        </prod>
      </det>"""

    valor_total = sum(float(it.get("vProd", "100.00")) for it in items_xml)
    dup_block = ""
    if duplicatas:
        dup_entries = ""
        for d in duplicatas:
            dup_entries += f"""
        <dup>
          <nDup>{d['nDup']}</nDup>
          <dVenc>{d['dVenc']}</dVenc>
          <vDup>{d['vDup']}</vDup>
        </dup>"""
        dup_block = f"\n      <cobr>\n        <dup>{dup_entries}\n        </dup>\n      </cobr>"

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe>
    <infNFe Id="NFe{chave}" versao="4.00">
      <ide>
        <cUF>43</cUF><natOp>Compra para comercializacao</natOp><mod>55</mod>
        <serie>1</serie><nNF>{numero}</nNF><dhEmi>2026-09-01T10:00:00-03:00</dhEmi>
        <tpNF>1</tpNF><idDest>1</idDest><cMunFG>4314100</cMunFG>
        <tpImp>1</tpImp><tpEmis>1</tpEmis><cDV>0</cDV><tpAmb>2</tpAmb>
        <finNFe>1</finNFe><indFinal>0</indFinal><indPres>1</indPres>
        <procEmi>0</procEmi><verProc>BECRP-TEST</verProc>
      </ide>
      <emit>
        <CNPJ>{cnpj_emitente}</CNPJ><xNome>FORNECEDOR TESTE LTDA</xNome>
        <xFant>Forn Teste</xFant>
        <enderEmit><xLgr>Rua Teste</xLgr><nro>100</nro><xBairro>Centro</xBairro>
        <cMun>4314100</cMun><xMun>Passo Fundo</xMun><UF>RS</UF><CEP>99010000</CEP>
        </enderEmit><IE>1234567890</IE>
      </emit>
      <dest>
        <CNPJ>{cnpj_dest}</CNPJ><xNome>COMERCIAL DESTINO LTDA</xNome>
        <enderDest><xLgr>Rua Destino</xLgr><nro>200</nro><xBairro>Centro</xBairro>
        <cMun>4314100</cMun><xMun>Passo Fundo</xMun><UF>RS</UF><CEP>99010001</CEP>
        </enderDest><indIEDest>9</indIEDest>
      </dest>
      {items_block}
      {dup_block}
      <total>
        <ICMSTot>
          <vBC>0.00</vBC><vICMS>0.00</vICMS>
          <vProd>{valor_total:.2f}</vProd><vNF>{valor_total:.2f}</vNF>
        </ICMSTot>
      </total>
    </infNFe>
  </NFe>
</nfeProc>"""


class TestPurchaseFinanceDirect:
    """Test create_from_receiving directly with mock receiving dicts."""

    def setup_method(self):
        self.originals = _save_originals()
        self._created_rids = []
        # Start with empty AP file to avoid cross-test contamination
        purchase_finance._save({"titulos": [], "seq": 0})

    def teardown_method(self):
        _restore(self.originals)

    def test_single_parcel_no_duplicatas(self):
        """Without duplicatas → 1 AP title with 30-day term."""
        rec = _make_receiving()
        self._created_rids.append(rec["id"])
        ap = purchase_finance.create_from_receiving(rec, usuario="test")
        assert ap["already"] is False
        titulos = ap["titulos"]
        assert len(titulos) == 1

        t = titulos[0]
        assert t["status"] == "aberto"
        assert t["valor"] == 500.0
        assert t["parcela"] == 1
        assert t["parcelas"] == 1
        assert t["partner_id"] == "bp_test"
        assert t["receiving_id"] == rec["id"]

    def test_duplicatas_creates_multiple_titles(self):
        """NF-e with duplicatas → one AP title per duplicate."""
        rec = _make_receiving()
        self._created_rids.append(rec["id"])
        rid = rec["id"]
        rec["nfe"]["duplicatas"] = [
            {"n_dup": "001", "vencimento": "2026-10-01", "valor": 150.00},
            {"n_dup": "002", "vencimento": "2026-11-01", "valor": 150.00},
        ]
        rec["nfe"]["valor_total"] = 300.00

        ap = purchase_finance.create_from_receiving(rec, usuario="test")
        assert ap["already"] is False
        titulos = sorted(ap["titulos"], key=lambda t: t["parcela"])
        assert len(titulos) == 2

        assert titulos[0]["n_dup"] == "001"
        assert titulos[0]["valor"] == 150.0
        assert titulos[0]["vencimento"] == "2026-10-01"
        assert titulos[1]["n_dup"] == "002"
        assert titulos[1]["valor"] == 150.0
        assert titulos[1]["vencimento"] == "2026-11-01"

    def test_idempotent_returns_existing(self):
        """Calling create_from_receiving twice → second call returns already=True."""
        rec = _make_receiving()
        self._created_rids.append(rec["id"])

        ap1 = purchase_finance.create_from_receiving(rec, usuario="test")
        assert ap1["already"] is False

        ap2 = purchase_finance.create_from_receiving(rec, usuario="test")
        assert ap2["already"] is True
        assert len(ap2["titulos"]) >= 1

    def test_titulo_persisted_in_json(self):
        """AP titles are persisted to titulos_ap.json."""
        rec = _make_receiving()
        self._created_rids.append(rec["id"])
        rid = rec["id"]

        ap = purchase_finance.create_from_receiving(rec, usuario="test")
        assert ap["already"] is False

        data = purchase_finance._load()
        persisted = [t for t in data.get("titulos", [])
                     if t.get("receiving_id") == rid]
        assert len(persisted) == 1
        assert persisted[0]["valor"] == 500.0
        assert persisted[0]["status"] == "aberto"

    def test_fields_populated(self):
        """AP title has all required fields."""
        rec = _make_receiving()
        self._created_rids.append(rec["id"])

        ap = purchase_finance.create_from_receiving(rec, usuario="tester")
        assert ap["already"] is False
        t = ap["titulos"][0]

        assert t["id"].startswith("AP-")
        assert t["cnpj"] == "11222333000181"
        assert t["fornecedor"] == "Fornecedor Teste"
        assert t["usuario"] == "tester"
        assert "criado_em" in t

    def test_valor_vencimento_defaults(self):
        """When duplicata has no value → use total; no venc → +30d."""
        rec = _make_receiving()
        self._created_rids.append(rec["id"])
        rec["nfe"]["duplicatas"] = [
            {"n_dup": "001", "vencimento": "", "valor": 0},
        ]
        rec["nfe"]["valor_total"] = 200.00

        ap = purchase_finance.create_from_receiving(rec, usuario="test")
        assert ap["already"] is False
        t = ap["titulos"][0]
        assert t["valor"] == 200.0
        assert t["vencimento"] != ""


class TestPurchaseFinanceFullFlow:
    """Test AP creation through the full NF-e flow (ingest → complete)."""

    def setup_method(self):
        self.originals = _save_originals()
        self.chave = _next_chave()
        self.numero = 8300 + int(self.chave[-4:]) % 1000
        self._created_rids = []
        # Start with empty AP file to avoid cross-test contamination
        purchase_finance._save({"titulos": [], "seq": 0})

    def teardown_method(self):
        _restore(self.originals)

    def test_complete_receiving_creates_ap(self):
        """complete_receiving → AP titles in rec['accounts_payable'] and persisted."""
        xml = _make_nfe_xml(self.chave, self.numero, [
            {"cProd": "P001", "xProd": "Produto A", "qCom": "10",
             "vUnCom": "30.00", "vProd": "300.00"},
        ])
        result = nfe_monitor.ingest_xml(xml, filename="flow_ap.xml",
                                        source="test_ap", user_id="test")
        doc = nfe_monitor.process_document(result["document"]["id"],
                                           user_id="test")
        rid = doc["receiving_id"]
        self._created_rids.append(rid)

        recs = receiving_mvp.list_receivings()
        rec = next(r for r in recs if r["id"] == rid)
        verify_payload = {
            "items": [
                {"item_index": i, "produto_id": it["produto_id"],
                 "qty_verified": it["qty_expected"]}
                for i, it in enumerate(rec["items"])
            ]
        }
        receiving_mvp.verify_receiving(rid, verify_payload, user_id="test")
        rec_c = receiving_mvp.complete_receiving(rid, user_id="test")

        assert rec_c["status"] == "completed"
        ap_info = rec_c.get("accounts_payable", {})
        assert ap_info.get("count", 0) >= 1
        assert "titulos" in ap_info
        assert len(ap_info["titulos"]) >= 1

        data = purchase_finance._load()
        persisted = [t for t in data.get("titulos", [])
                     if t.get("receiving_id") == rid]
        assert len(persisted) >= 1, f"Expected AP for rid={rid}"
        assert persisted[0]["status"] == "aberto"
        assert persisted[0]["partner_id"] == rec_c.get("fornecedor_id")
