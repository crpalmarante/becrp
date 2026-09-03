"""Integration tests for NF-e XML import: ingest → process → verify → complete.

Tests the full lifecycle without touching the HTTP server — uses Python
modules directly (same pattern as the rest of the test suite).

Uses both synthetic XML (for unit-level tests) and the real XML files from
data/nfe_inbound/ (for integration-level tests against actual NF-e data).
"""
import sys
import os
import json
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import nfe_monitor
import nfe_inbound
import receiving_mvp

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MONITOR_FILE = os.path.join(DATA_DIR, "nfe_monitor.json")
RECEIVINGS_FILE = os.path.join(DATA_DIR, "receivings.json")

# ── Helpers ─────────────────────────────────────────────────


def _save_originals():
    """Snapshot monitor + receivings so we can restore after tests."""
    _orig = {}
    for f in (MONITOR_FILE, RECEIVINGS_FILE):
        if os.path.exists(f):
            with open(f) as fh:
                _orig[f] = json.load(fh)
        else:
            _orig[f] = {}
    return _orig


def _restore(originals):
    """Restore monitor + receivings to pre-test state."""
    for f, content in originals.items():
        os.makedirs(os.path.dirname(f), exist_ok=True)
        with open(f, "w") as fh:
            json.dump(content, fh, ensure_ascii=False, indent=2)


_counter = 0


def _next_chave():
    """Generate a unique 44-digit NF-e chave."""
    global _counter
    _counter += 1
    # NF-e chave: 44 digits — cUF(2)+AAMM(4)+CNPJ(14)+mod(2)+serie(3)+nNF(9)+cNF(8)+cDV(1)
    # Use fixed prefix + zero-padded counter for uniqueness
    prefix = "43260762832155000141550010000"  # 29 digits
    num_part = f"{_counter:015d}"  # 15 digits (mod+serie+nNF+cNF+cDV = 44 - 29 = 15)
    chave = (prefix + num_part)[:44]
    return chave


def _make_nfe_xml(chave, numero, items_xml, cnpj_emitente="11222333000181",
                  cnpj_dest="62832155000141", modelo="55"):
    """Build a minimal NF-e XML string with a valid 44-digit chave."""
    items_block = ""
    for i, item in enumerate(items_xml, 1):
        items_block += f"""
      <det nItem="{i}">
        <prod>
          <cProd>{item.get('cProd', f'PROD{i:03d}')}</cProd>
          <cEAN>{item.get('cEAN', '')}</cEAN>
          <xProd>{item.get('xProd', f'Produto Teste {i}')}</xProd>
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

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe>
    <infNFe Id="NFe{chave}" versao="4.00">
      <ide>
        <cUF>43</cUF>
        <natOp>Compra para comercializacao</natOp>
        <mod>{modelo}</mod>
        <serie>1</serie>
        <nNF>{numero}</nNF>
        <dhEmi>2026-09-01T10:00:00-03:00</dhEmi>
        <tpNF>1</tpNF>
        <idDest>1</idDest>
        <cMunFG>4314100</cMunFG>
        <tpImp>1</tpImp>
        <tpEmis>1</tpEmis>
        <cDV>0</cDV>
        <tpAmb>2</tpAmb>
        <finNFe>1</finNFe>
        <indFinal>0</indFinal>
        <indPres>1</indPres>
        <procEmi>0</procEmi>
        <verProc>BECRP-TEST</verProc>
      </ide>
      <emit>
        <CNPJ>{cnpj_emitente}</CNPJ>
        <xNome>FORNECEDOR TESTE LTDA</xNome>
        <xFant>Forn Teste</xFant>
        <enderEmit>
          <xLgr>Rua Teste</xLgr>
          <nro>100</nro>
          <xBairro>Centro</xBairro>
          <cMun>4314100</cMun>
          <xMun>Passo Fundo</xMun>
          <UF>RS</UF>
          <CEP>99010000</CEP>
        </enderEmit>
        <IE>1234567890</IE>
      </emit>
      <dest>
        <CNPJ>{cnpj_dest}</CNPJ>
        <xNome>COMERCIAL DESTINO LTDA</xNome>
        <enderDest>
          <xLgr>Rua Destino</xLgr>
          <nro>200</nro>
          <xBairro>Centro</xBairro>
          <cMun>4314100</cMun>
          <xMun>Passo Fundo</xMun>
          <UF>RS</UF>
          <CEP>99010001</CEP>
        </enderDest>
        <indIEDest>9</indIEDest>
      </dest>
      {items_block}
      <total>
        <ICMSTot>
          <vBC>0.00</vBC>
          <vICMS>0.00</vICMS>
          <vProd>{valor_total:.2f}</vProd>
          <vNF>{valor_total:.2f}</vNF>
        </ICMSTot>
      </total>
    </infNFe>
  </NFe>
</nfeProc>"""


# ── Tests ───────────────────────────────────────────────────


class TestNfeImportIngest:
    """NF-e ingest XML → monitor."""

    def setup_method(self):
        self.originals = _save_originals()
        self.chave = _next_chave()
        self.numero = 9000 + int(self.chave[-4:]) % 1000
        self.xml = _make_nfe_xml(
            self.chave, self.numero,
            [{"cProd": "TEST001", "cEAN": "7899999999001", "xProd": "Arroz Teste 1kg",
              "qCom": "5", "vUnCom": "20.00", "vProd": "100.00"},
             {"cProd": "TEST002", "cEAN": "", "xProd": "Feijao Teste",
              "qCom": "3", "vUnCom": "15.00", "vProd": "45.00"}],
        )

    def teardown_method(self):
        _restore(self.originals)

    def test_ingest_xml_new(self):
        """ingest_xml stores document in monitor with status=new."""
        result = nfe_monitor.ingest_xml(self.xml, filename="test_nfe.xml",
                                        source="test", user_id="test_user")
        assert result["duplicate"] is False
        doc = result["document"]
        assert doc["status"] == "new"
        assert doc["chave"] == self.chave
        assert doc["modelo"] == "55"
        assert doc["fornecedor_cnpj"] == "11222333000181"

    def test_duplicate_detection(self):
        """Same chave → duplicate flag."""
        nfe_monitor.ingest_xml(self.xml, filename="test2.xml",
                               source="test", user_id="test_user")
        result2 = nfe_monitor.ingest_xml(self.xml, filename="test3.xml",
                                         source="test", user_id="test_user")
        assert result2["duplicate"] is True
        assert "já no monitor" in result2["message"]

    def test_nfc_e_65_rejected(self):
        """NFC-e modelo 65 → error status in monitor."""
        chave65 = _next_chave()
        xml65 = _make_nfe_xml(
            chave65, 8001,
            [{"cProd": "NFC001", "xProd": "Produto NFC", "qCom": "1",
              "vUnCom": "10.00", "vProd": "10.00"}],
            modelo="65",
        )
        result = nfe_monitor.ingest_xml(xml65, filename="nfc_test.xml",
                                        source="test", user_id="test_user")
        doc = result["document"]
        assert doc["status"] == "error"
        assert "NFC-e" in doc["error"]

    def test_invalid_xml_error(self):
        """Invalid XML → error status in monitor."""
        result = nfe_monitor.ingest_xml(b"<invalid>not a real nfe</invalid>",
                                        filename="bad.xml", source="test",
                                        user_id="test_user")
        assert result["document"]["status"] == "error"

    def test_empty_xml_error(self):
        """Empty XML → raises ValueError."""
        try:
            nfe_monitor.ingest_xml(b"", filename="empty.xml",
                                   source="test", user_id="test_user")
            assert False, "Expected ValueError for empty XML"
        except ValueError as e:
            assert "vazio" in str(e).lower()


class TestNfeImportProcess:
    """NF-e process_document → receiving draft."""

    def setup_method(self):
        self.originals = _save_originals()
        self.chave = _next_chave()
        self.numero = 9100 + int(self.chave[-4:]) % 1000
        self.xml = _make_nfe_xml(
            self.chave, self.numero,
            [{"cProd": "TEST001", "cEAN": "7899999999001", "xProd": "Arroz Teste 1kg",
              "qCom": "5", "vUnCom": "20.00", "vProd": "100.00"},
             {"cProd": "TEST002", "cEAN": "", "xProd": "Feijao Teste",
              "qCom": "3", "vUnCom": "15.00", "vProd": "45.00"}],
        )

    def teardown_method(self):
        _restore(self.originals)

    def test_process_creates_receiving(self):
        """process_document creates a receiving draft from NF-e."""
        result = nfe_monitor.ingest_xml(self.xml, filename="proc_test.xml",
                                        source="test", user_id="test_user")
        doc_id = result["document"]["id"]

        doc = nfe_monitor.process_document(doc_id, user_id="test_user")
        assert doc["status"] == "done"
        assert doc["receiving_id"] is not None

        # Verify receiving draft
        recs = receiving_mvp.list_receivings()
        rec = next((r for r in recs if r["id"] == doc["receiving_id"]), None)
        assert rec is not None
        assert rec["status"] == "draft"
        assert rec["origem"] == "nfe"
        assert rec["fornecedor_cnpj"] == "11222333000181"
        assert len(rec["items"]) == 2

        # Check items were matched
        item1 = rec["items"][0]
        assert item1["qty_expected"] == 5.0
        assert item1["nfe_item"]["ean"] == "7899999999001"


class TestNfeImportFullFlow:
    """Full NF-e import: ingest → process → verify → complete."""

    def setup_method(self):
        self.originals = _save_originals()
        self.chave = _next_chave()
        self.numero = 9200 + int(self.chave[-4:]) % 1000
        self.xml = _make_nfe_xml(
            self.chave, self.numero,
            [{"cProd": "TEST001", "cEAN": "7899999999001", "xProd": "Arroz Teste 1kg",
              "qCom": "5", "vUnCom": "20.00", "vProd": "100.00"},
             {"cProd": "TEST002", "cEAN": "", "xProd": "Feijao Teste",
              "qCom": "3", "vUnCom": "15.00", "vProd": "45.00"}],
        )

    def teardown_method(self):
        _restore(self.originals)

    def _ingest_and_process(self):
        """Helper: ingest XML and process into receiving draft."""
        result = nfe_monitor.ingest_xml(self.xml, filename="flow_test.xml",
                                        source="test", user_id="test_user")
        assert result["duplicate"] is False
        doc = nfe_monitor.process_document(result["document"]["id"],
                                           user_id="test_user")
        assert doc["status"] == "done"
        return doc["receiving_id"]

    def test_verify_receiving(self):
        """verify_receiving sets qty_verified and moves to verified status."""
        rid = self._ingest_and_process()

        recs = receiving_mvp.list_receivings()
        rec = next(r for r in recs if r["id"] == rid)
        items = rec["items"]

        verify_payload = {
            "items": [
                {"item_index": i, "produto_id": it["produto_id"],
                 "qty_verified": it["qty_expected"]}
                for i, it in enumerate(items)
            ]
        }
        rec_verified = receiving_mvp.verify_receiving(rid, verify_payload,
                                                      user_id="test_user")
        assert rec_verified["status"] == "verified"
        for it in rec_verified["items"]:
            assert it["qty_verified"] is not None
            assert it["qty_verified"] == it["qty_expected"]

    def test_complete_receiving(self):
        """complete_receiving auto-verifies then completes."""
        rid = self._ingest_and_process()

        rec = receiving_mvp.complete_receiving(rid, user_id="test_user",
                                               auto_verify=True)
        assert rec["status"] == "completed"
        assert len(rec["items"]) == 2

    def test_full_e2e_flow(self):
        """End-to-end: ingest → process → verify → complete in sequence."""
        # 1. Ingest
        result = nfe_monitor.ingest_xml(self.xml, filename="e2e_test.xml",
                                        source="test", user_id="test_user")
        assert result["duplicate"] is False

        # 2. Process
        doc = nfe_monitor.process_document(result["document"]["id"],
                                           user_id="test_user")
        assert doc["status"] == "done"
        rid = doc["receiving_id"]

        # 3. Verify
        recs = receiving_mvp.list_receivings()
        rec = next(r for r in recs if r["id"] == rid)
        verify_payload = {
            "items": [
                {"item_index": i, "produto_id": it["produto_id"],
                 "qty_verified": it["qty_expected"]}
                for i, it in enumerate(rec["items"])
            ]
        }
        rec_v = receiving_mvp.verify_receiving(rid, verify_payload,
                                               user_id="test_user")
        assert rec_v["status"] == "verified"

        # 4. Complete
        rec_c = receiving_mvp.complete_receiving(rid, user_id="test_user")
        assert rec_c["status"] == "completed"

        # 5. Verify items preserved
        assert len(rec_c["items"]) == 2
        for it in rec_c["items"]:
            assert it["qty_verified"] == it["qty_expected"]


class TestNfeImportRealXml:
    """Integration tests using real NF-e XML files from data/nfe_inbound/."""

    INBOUND_DIR = os.path.join(DATA_DIR, "nfe_inbound")

    def setup_method(self):
        self.originals = _save_originals()
        # Find XMLs not yet in the monitor
        monitor_data = json.load(open(MONITOR_FILE)) if os.path.exists(MONITOR_FILE) else {}
        monitor_chaves = {d.get("chave") for d in monitor_data.get("documents", [])}
        self.available = []
        if os.path.isdir(self.INBOUND_DIR):
            for f in sorted(os.listdir(self.INBOUND_DIR)):
                if not f.endswith(".xml"):
                    continue
                path = os.path.join(self.INBOUND_DIR, f)
                with open(path) as fh:
                    txt = fh.read()
                import re
                m = re.search(r'Id="NFe(\d+)"', txt)
                if m and m.group(1) not in monitor_chaves:
                    self.available.append(path)
        # Use at most 3 for speed
        self.test_files = self.available[:3]

    def teardown_method(self):
        _restore(self.originals)

    def test_real_xml_ingest_and_process(self):
        """Ingest + process each real XML file creates receiving drafts."""
        for path in self.test_files:
            with open(path, "rb") as f:
                xml = f.read()

            result = nfe_monitor.ingest_xml(xml, filename=os.path.basename(path),
                                            source="test_real", user_id="test_user")
            if result.get("duplicate"):
                continue  # skip already-imported
            doc = result["document"]
            assert doc["status"] == "new"

            processed = nfe_monitor.process_document(doc["id"], user_id="test_user")
            assert processed["status"] == "done"
            assert processed["receiving_id"] is not None

            recs = receiving_mvp.list_receivings()
            rec = next((r for r in recs if r["id"] == processed["receiving_id"]), None)
            assert rec is not None
            assert rec["origem"] == "nfe"
            assert len(rec["items"]) > 0

    def test_real_xml_full_e2e(self):
        """Full E2E on first available real XML: ingest → process → verify → complete."""
        if not self.test_files:
            return  # no unprocessed XMLs available

        path = self.test_files[0]
        with open(path, "rb") as f:
            xml = f.read()

        # 1. Ingest
        result = nfe_monitor.ingest_xml(xml, filename=os.path.basename(path),
                                        source="test_real_e2e", user_id="test_user")
        if result.get("duplicate"):
            return  # already imported
        assert result["duplicate"] is False

        # 2. Process
        doc = nfe_monitor.process_document(result["document"]["id"],
                                           user_id="test_user")
        assert doc["status"] == "done"
        rid = doc["receiving_id"]

        # 3. Verify
        recs = receiving_mvp.list_receivings()
        rec = next(r for r in recs if r["id"] == rid)
        verify_payload = {
            "items": [
                {"item_index": i, "produto_id": it["produto_id"],
                 "qty_verified": it["qty_expected"]}
                for i, it in enumerate(rec["items"])
            ]
        }
        rec_v = receiving_mvp.verify_receiving(rid, verify_payload,
                                               user_id="test_user")
        assert rec_v["status"] == "verified"

        # 4. Complete
        rec_c = receiving_mvp.complete_receiving(rid, user_id="test_user")
        assert rec_c["status"] == "completed"
        assert len(rec_c["items"]) > 0
        for it in rec_c["items"]:
            assert it["qty_verified"] == it["qty_expected"]

    def test_sample_xml_full_e2e(self):
        """Full E2E on the sample XML: ingest → process → verify → complete."""
        sample_path = os.path.join(DATA_DIR, "samples", "nfe-entrada-demo.xml")
        if not os.path.exists(sample_path):
            return

        with open(sample_path, "rb") as f:
            xml = f.read()

        result = nfe_monitor.ingest_xml(xml, filename="nfe-entrada-demo.xml",
                                        source="test_sample", user_id="test_user")
        if result.get("duplicate"):
            return

        doc = nfe_monitor.process_document(result["document"]["id"],
                                           user_id="test_user")
        if doc.get("status") == "duplicate":
            return
        assert doc["status"] == "done"
        rid = doc["receiving_id"]

        recs = receiving_mvp.list_receivings()
        rec = next(r for r in recs if r["id"] == rid)
        verify_payload = {
            "items": [
                {"item_index": i, "produto_id": it["produto_id"],
                 "qty_verified": it["qty_expected"]}
                for i, it in enumerate(rec["items"])
            ]
        }
        rec_v = receiving_mvp.verify_receiving(rid, verify_payload,
                                               user_id="test_user")
        assert rec_v["status"] == "verified"

        rec_c = receiving_mvp.complete_receiving(rid, user_id="test_user")
        assert rec_c["status"] == "completed"
