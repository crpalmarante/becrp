"""Tests for product_localization.py — RFC-4004 product localization module."""

import json
import os
import shutil
import product_localization


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
REFS_FILE = os.path.join(DATA_DIR, "supplier_product_refs.json")
BACKUP = REFS_FILE + ".test_bak"


def _backup():
    if os.path.exists(REFS_FILE):
        shutil.copy2(REFS_FILE, BACKUP)


def _restore():
    if os.path.exists(BACKUP):
        shutil.move(BACKUP, REFS_FILE)
    elif os.path.exists(REFS_FILE):
        os.remove(REFS_FILE)


def _load_refs():
    if not os.path.exists(REFS_FILE):
        return {"refs": []}
    with open(REFS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"refs": []}
    if not isinstance(data.get("refs"), list):
        data["refs"] = []
    return data


def _save_refs(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(REFS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _clear_refs():
    _save_refs({"refs": []})


# ---------- Sample catalog ----------

SAMPLE_CATALOG = [
    {"id": "1", "nome": "Arroz 5kg", "codigo_barras": "7891234560018", "sku": "", "ativo": True},
    {"id": "2", "nome": "Feijao 1kg", "codigo_barras": "7891234560025", "sku": "", "ativo": True},
    {"id": "3", "nome": "Oleo de Soja 900ml", "codigo_barras": "7891234560032", "sku": "OLEO900", "ativo": True},
    {"id": "4", "nome": "Acucar 2kg", "codigo_barras": "7891234560049", "sku": "", "ativo": True},
    {"id": "5", "nome": "Cafe 500g", "codigo_barras": "7891234560056", "sku": "CAFE500", "ativo": True},
    {"id": "99", "nome": "Inactive Product", "codigo_barras": "0000000000000", "sku": "INACT", "ativo": False},
]


# ---------- Test list_refs ----------

class TestListRefs:
    """Tests for product_localization.list_refs()."""

    def setup_method(self):
        _backup()
        _clear_refs()
        product_localization.upsert_ref(
            supplier_cnpj="11111111000100",
            product_id="1",
            supplier_code="SUP001",
            gtin="7891234560018",
            product_nome="Arroz",
        )
        product_localization.upsert_ref(
            supplier_cnpj="11111111000100",
            product_id="2",
            supplier_code="SUP002",
            product_nome="Feijao",
        )
        product_localization.upsert_ref(
            supplier_cnpj="22222222000100",
            product_id="3",
            supplier_code="SUP003",
            product_nome="Oleo",
        )

    def teardown_method(self):
        _restore()

    def test_list_all(self):
        refs = product_localization.list_refs()
        assert len(refs) == 3

    def test_list_filtered_by_cnpj(self):
        refs = product_localization.list_refs(supplier_cnpj="11111111000100")
        assert len(refs) == 2
        assert all(r["supplier_cnpj"] == "11111111000100" for r in refs)

    def test_list_filtered_no_match(self):
        refs = product_localization.list_refs(supplier_cnpj="99999999999999")
        assert len(refs) == 0


# ---------- Test find_ref ----------

class TestFindRef:
    """Tests for product_localization.find_ref()."""

    def setup_method(self):
        _backup()
        _clear_refs()
        product_localization.upsert_ref(
            supplier_cnpj="11111111000100",
            product_id="1",
            supplier_code="SUP001",
            gtin="7891234560018",
            product_nome="Arroz",
        )

    def teardown_method(self):
        _restore()

    def test_find_by_code(self):
        ref = product_localization.find_ref("11111111000100", supplier_code="SUP001")
        assert ref is not None
        assert ref["product_id"] == "1"

    def test_find_by_ean(self):
        ref = product_localization.find_ref("11111111000100", ean="7891234560018")
        assert ref is not None
        assert ref["product_id"] == "1"

    def test_find_not_found(self):
        ref = product_localization.find_ref("11111111000100", supplier_code="NOPE")
        assert ref is None

    def test_find_wrong_cnpj(self):
        ref = product_localization.find_ref("99999999999999", supplier_code="SUP001")
        assert ref is None


# ---------- Test upsert_ref ----------

class TestUpsertRef:
    """Tests for product_localization.upsert_ref()."""

    def setup_method(self):
        _backup()
        _clear_refs()

    def teardown_method(self):
        _restore()

    def test_create_new_ref(self):
        ref = product_localization.upsert_ref(
            supplier_cnpj="11111111000100",
            product_id="1",
            supplier_code="NEW001",
            gtin="1234567890123",
            product_nome="Test Product",
            source="nfe",
            user_id="tester",
        )
        assert ref["id"] == 1
        assert ref["product_id"] == "1"
        assert ref["supplier_code"] == "NEW001"
        assert ref["gtin"] == "1234567890123"
        assert ref["times_seen"] == 1
        assert ref["source"] == "nfe"
        assert ref["created_by"] == "tester"

    def test_update_existing_ref(self):
        product_localization.upsert_ref(
            supplier_cnpj="11111111000100",
            product_id="1",
            supplier_code="UPD001",
            product_nome="Original",
        )
        updated = product_localization.upsert_ref(
            supplier_cnpj="11111111000100",
            product_id="2",
            supplier_code="UPD001",
            product_nome="Updated",
        )
        assert updated["product_id"] == "2"
        assert updated["product_nome"] == "Updated"
        assert updated["times_seen"] == 2

    def test_create_by_ean_only(self):
        ref = product_localization.upsert_ref(
            supplier_cnpj="",
            product_id="1",
            gtin="7891234560018",
        )
        assert ref["gtin"] == "7891234560018"

    def test_validation_no_product_id(self):
        try:
            product_localization.upsert_ref(supplier_cnpj="11111111000100", product_id="")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_validation_no_identifier(self):
        try:
            product_localization.upsert_ref(
                supplier_cnpj="", product_id="1", supplier_code="", gtin=""
            )
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_persisted(self):
        product_localization.upsert_ref(
            supplier_cnpj="11111111000100",
            product_id="1",
            supplier_code="PERSIST001",
        )
        refs = product_localization.list_refs()
        assert len(refs) == 1
        assert refs[0]["supplier_code"] == "PERSIST001"


# ---------- Test match_item ----------

class TestMatchItem:
    """Tests for product_localization.match_item() — core matching logic."""

    def setup_method(self):
        _backup()
        _clear_refs()

    def teardown_method(self):
        _restore()

    def test_match_by_supplier_ref(self):
        product_localization.upsert_ref(
            supplier_cnpj="11111111000100",
            product_id="1",
            supplier_code="SUP_ARROZ",
            product_nome="Arroz",
        )
        item = {"codigo_fornecedor": "SUP_ARROZ", "ean": "", "descricao": "Arroz 5kg"}
        result = product_localization.match_item(
            item, catalog=SAMPLE_CATALOG, supplier_cnpj="11111111000100"
        )
        assert result["match"] == "supplier_ref"
        assert result["produto_id"] == "1"

    def test_match_by_ean(self):
        item = {"codigo_fornecedor": "", "ean": "7891234560032", "descricao": "Oleo"}
        result = product_localization.match_item(item, catalog=SAMPLE_CATALOG)
        assert result["match"] == "ean"
        assert result["produto_id"] == "3"

    def test_match_by_codigo(self):
        item = {"codigo_fornecedor": "OLEO900", "ean": "", "descricao": "Oleo Soja"}
        result = product_localization.match_item(item, catalog=SAMPLE_CATALOG)
        assert result["match"] == "codigo"
        assert result["produto_id"] == "3"

    def test_match_by_product_id(self):
        item = {"codigo_fornecedor": "5", "ean": "", "descricao": "Cafe"}
        result = product_localization.match_item(item, catalog=SAMPLE_CATALOG)
        assert result["match"] == "codigo"
        assert result["produto_id"] == "5"

    def test_no_match_returns_suggestions(self):
        item = {"codigo_fornecedor": "", "ean": "", "descricao": "Chocolate 100g"}
        result = product_localization.match_item(item, catalog=SAMPLE_CATALOG)
        assert result["match"] == "none"
        assert result["produto_id"] == ""
        assert isinstance(result.get("suggestions"), list)

    def test_inactive_product_excluded_from_suggest(self):
        """match_item doesn't filter inactive (only suggest_products does)."""
        # match_item by codigo matches even inactive
        item = {"codigo_fornecedor": "INACT", "ean": "", "descricao": ""}
        result = product_localization.match_item(item, catalog=SAMPLE_CATALOG)
        assert result["match"] == "codigo"  # match_item is inclusive

    def test_inactive_excluded_from_suggest(self):
        results = product_localization.suggest_products("Inactive", catalog=SAMPLE_CATALOG)
        ids = [r["id"] for r in results]
        assert "99" not in ids

    def test_supplier_ref_priority_over_ean(self):
        """Known ref takes priority even if EAN also matches."""
        product_localization.upsert_ref(
            supplier_cnpj="11111111000100",
            product_id="2",
            supplier_code="MY_CODE",
        )
        item = {"codigo_fornecedor": "MY_CODE", "ean": "7891234560018"}
        result = product_localization.match_item(
            item, catalog=SAMPLE_CATALOG, supplier_cnpj="11111111000100"
        )
        assert result["match"] == "supplier_ref"
        assert result["produto_id"] == "2"

    def test_empty_item_no_match(self):
        item = {}
        result = product_localization.match_item(item, catalog=SAMPLE_CATALOG)
        assert result["match"] == "none"


# ---------- Test suggest_products ----------

class TestSuggestProducts:
    """Tests for product_localization.suggest_products()."""

    def test_suggest_by_name(self):
        results = product_localization.suggest_products("Arroz", catalog=SAMPLE_CATALOG)
        assert len(results) >= 1
        assert results[0]["id"] == "1"

    def test_suggest_by_ean(self):
        results = product_localization.suggest_products("7891234560056", catalog=SAMPLE_CATALOG)
        assert len(results) >= 1
        assert results[0]["id"] == "5"

    def test_suggest_by_sku(self):
        results = product_localization.suggest_products("CAFE500", catalog=SAMPLE_CATALOG)
        assert len(results) >= 1
        assert results[0]["id"] == "5"

    def test_suggest_empty(self):
        results = product_localization.suggest_products("", catalog=SAMPLE_CATALOG)
        assert results == []

    def test_suggest_excludes_inactive(self):
        results = product_localization.suggest_products("Inactive", catalog=SAMPLE_CATALOG)
        ids = [r["id"] for r in results]
        assert "99" not in ids

    def test_suggest_limit(self):
        results = product_localization.suggest_products("kg", catalog=SAMPLE_CATALOG, limit=2)
        assert len(results) <= 2


# ---------- Test remember_from_receiving_item ----------

class TestRememberFromReceivingItem:
    """Tests for product_localization.remember_from_receiving_item()."""

    def setup_method(self):
        _backup()
        _clear_refs()

    def teardown_method(self):
        _restore()

    def test_remember_basic(self):
        rec = {"fornecedor_cnpj": "11111111000100"}
        item = {
            "nfe_item": {
                "codigo_fornecedor": "FORN001",
                "ean": "7891234560018",
                "descricao": "Arroz Tipo A",
            },
            "produto_nome": "Arroz 5kg",
        }
        ref = product_localization.remember_from_receiving_item(
            rec, item, produto_id="1", produto_nome="Arroz 5kg", user_id="test"
        )
        assert ref is not None
        assert ref["supplier_code"] == "FORN001"
        assert ref["gtin"] == "7891234560018"
        assert ref["source"] == "manual"
        assert ref["created_by"] == "test"

    def test_remember_no_data_returns_none(self):
        rec = {}
        item = {"nfe_item": {}}
        ref = product_localization.remember_from_receiving_item(rec, item, produto_id="1")
        assert ref is None

    def test_remember_uses_nfe_item_fields(self):
        rec = {"fornecedor_cnpj": "22222222000100"}
        item = {
            "nfe_item": {
                "codigo_fornecedor": "XYZ999",
                "ean": "",
                "descricao": "Test Desc",
            },
        }
        ref = product_localization.remember_from_receiving_item(
            rec, item, produto_id="3"
        )
        assert ref["supplier_code"] == "XYZ999"
        assert ref["supplier_description"] == "Test Desc"


# ---------- Test search_products ----------

class TestSearchProducts:
    """Tests for product_localization.search_products() — alias for suggest."""

    def test_returns_list(self):
        results = product_localization.search_products("Arroz", catalog=SAMPLE_CATALOG)
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_matches_by_name(self):
        results = product_localization.search_products("Cafe", catalog=SAMPLE_CATALOG)
        assert any(r["id"] == "5" for r in results)
