"""Tests for partner_lookup.py — RFC-4005 partner lookup module."""

from unittest.mock import patch
import partner_lookup


# ---------- Sample partner data ----------

SAMPLE_PARTNERS = {
    "bp001": {
        "display_name": "Bom Preço",
        "legal_name": "Bom Preço LTDA",
        "trade_name": "Bom Preço",
        "partner_code": "BP001",
        "roles": ["CUSTOMER"],
        "status": "ACTIVE",
        "documents": [
            {"document_type": "CNPJ", "document_number": "12.345.678/0001-90"},
        ],
        "addresses": [{
            "address_type": "BILLING",
            "street": "Rua A",
            "number": "10",
            "city": "SP",
            "state": "SP",
            "preferred": True,
        }],
        "contacts": [{
            "phone": "11988888888",
            "email": "bom@preco.com",
            "preferred": True,
        }],
    },
    "bp002": {
        "display_name": "Sul Alimentos",
        "roles": ["CUSTOMER", "SUPPLIER"],
        "status": "ACTIVE",
        "documents": [
            {"document_type": "CNPJ", "document_number": "98.765.432/0001-10"},
        ],
    },
    "bp003": {
        "display_name": "João Silva",
        "person_type": "PERSON",
        "roles": ["CUSTOMER"],
        "status": "ACTIVE",
        "documents": [
            {"document_type": "CPF", "document_number": "123.456.789-00"},
        ],
    },
    "bp004_inactive": {
        "display_name": "Inactive Corp",
        "roles": ["SUPPLIER"],
        "status": "INACTIVE",
        "documents": [
            {"document_type": "CNPJ", "document_number": "11.111.111/0001-11"},
        ],
    },
    "bp005_external": {
        "display_name": "External Ref Corp",
        "roles": ["SUPPLIER"],
        "status": "ACTIVE",
        "documents": [
            {"document_type": "EXTERNAL_REF", "document_number": "EXT-999"},
        ],
    },
}


def _mock_partners(data=None):
    """Context manager to mock _load_partners with sample data."""
    return patch.object(partner_lookup, "_load_partners", return_value=data or SAMPLE_PARTNERS)


# ---------- Test lookup ----------

class TestLookup:
    """Tests for partner_lookup.lookup() — the main RFC-4005 function."""

    def test_lookup_by_cnpj(self):
        with _mock_partners():
            r = partner_lookup.lookup(cnpj="12.345.678/0001-90", audit=False)
        assert r["status"] == "found"
        assert r["match"] == "cnpj"
        assert r["partner"]["id"] == "bp001"

    def test_lookup_by_cnpj_digits(self):
        with _mock_partners():
            r = partner_lookup.lookup(cnpj="98765432000110", audit=False)
        assert r["status"] == "found"
        assert r["partner"]["id"] == "bp002"

    def test_lookup_by_cpf(self):
        with _mock_partners():
            r = partner_lookup.lookup(cpf="12345678900", audit=False)
        assert r["status"] == "found"
        assert r["partner"]["id"] == "bp003"

    def test_lookup_by_partner_code(self):
        with _mock_partners():
            r = partner_lookup.lookup(partner_code="BP001", audit=False)
        assert r["status"] == "found"
        assert r["partner"]["id"] == "bp001"

    def test_lookup_by_partner_id(self):
        with _mock_partners():
            r = partner_lookup.lookup(partner_id="bp002", audit=False)
        assert r["status"] == "found"
        assert r["partner"]["id"] == "bp002"

    def test_lookup_by_external_ref(self):
        with _mock_partners():
            r = partner_lookup.lookup(external_ref="EXT-999", audit=False)
        assert r["status"] == "found"
        assert r["partner"]["id"] == "bp005_external"

    def test_lookup_not_found(self):
        with _mock_partners():
            r = partner_lookup.lookup(cnpj="00000000000000", audit=False)
        assert r["status"] == "not_found"
        assert r["partner"] is None
        assert len(r["partners"]) == 0

    def test_lookup_inactive_excluded(self):
        with _mock_partners():
            r = partner_lookup.lookup(cnpj="11111111000111", audit=False)
        assert r["status"] == "not_found"

    def test_lookup_role_filter_supplier(self):
        with _mock_partners():
            r = partner_lookup.lookup(cnpj="12345678000190", role="SUPPLIER", audit=False)
        # bp001 is CUSTOMER only
        assert r["status"] == "not_found"

    def test_lookup_role_filter_customer(self):
        with _mock_partners():
            r = partner_lookup.lookup(cnpj="12345678000190", role="CUSTOMER", audit=False)
        assert r["status"] == "found"
        assert r["partner"]["id"] == "bp001"

    def test_lookup_role_supplier_matches_also_has_customer(self):
        """bp002 has both CUSTOMER and SUPPLIER — role filter on SUPPLIER matches."""
        with _mock_partners():
            r = partner_lookup.lookup(cnpj="98765432000110", role="SUPPLIER", audit=False)
        assert r["status"] == "found"
        assert r["partner"]["id"] == "bp002"

    def test_lookup_role_does_not_match_unrelated(self):
        """CUSTOMER role does not match CARRIER."""
        with _mock_partners():
            r = partner_lookup.lookup(cnpj="12345678000190", role="CARRIER", audit=False)
        assert r["status"] == "not_found"

    def test_lookup_returns_summary_fields(self):
        with _mock_partners():
            r = partner_lookup.lookup(cnpj="12345678000190", audit=False)
        p = r["partner"]
        assert "id" in p
        assert "display_name" in p
        assert "roles" in p
        assert "cnpj" in p
        assert "status" in p
        assert p["cnpj"] == "12345678000190"

    def test_lookup_external_ref_priority(self):
        """external_ref is checked before CNPJ."""
        data = {
            "a": {
                "display_name": "By ExtRef",
                "roles": ["SUPPLIER"],
                "documents": [{"document_type": "EXTERNAL_REF", "document_number": "EXT-123"}],
            },
            "b": {
                "display_name": "By CNPJ",
                "roles": ["SUPPLIER"],
                "documents": [{"document_type": "CNPJ", "document_number": "11111111000111"}],
            },
        }
        with _mock_partners(data):
            r = partner_lookup.lookup(
                external_ref="EXT-123",
                cnpj="11111111000111",
                audit=False,
            )
        assert r["status"] == "found"
        assert r["partner"]["id"] == "a"

    def test_lookup_cnpj_used_when_no_external_ref(self):
        data = {
            "a": {
                "display_name": "By CNPJ",
                "roles": ["SUPPLIER"],
                "documents": [{"document_type": "CNPJ", "document_number": "11111111000111"}],
            },
        }
        with _mock_partners(data):
            r = partner_lookup.lookup(cnpj="11111111000111", audit=False)
        assert r["status"] == "found"
        assert r["partner"]["id"] == "a"

    def test_lookup_returns_criteria(self):
        with _mock_partners():
            r = partner_lookup.lookup(cnpj="12345678000190", role="CUSTOMER", audit=False)
        assert "criteria" in r
        assert r["criteria"]["cnpj"] == "12345678000190"
        assert r["criteria"]["role"] == "CUSTOMER"

    def test_lookup_external_ref_in_criteria(self):
        with _mock_partners():
            r = partner_lookup.lookup(external_ref="EXT-999", audit=False)
        assert r["criteria"]["external_ref"] == "EXT-999"

    def test_lookup_multiple_matches(self):
        """Two partners with same CNPJ → multiple status."""
        data = {
            "dup1": {
                "display_name": "Dup 1",
                "roles": ["SUPPLIER"],
                "documents": [{"document_type": "CNPJ", "document_number": "55555555000111"}],
            },
            "dup2": {
                "display_name": "Dup 2",
                "roles": ["SUPPLIER"],
                "documents": [{"document_type": "CNPJ", "document_number": "55555555000111"}],
            },
        }
        with _mock_partners(data):
            r = partner_lookup.lookup(cnpj="55555555000111", audit=False)
        assert r["status"] == "multiple"
        assert len(r["partners"]) == 2


# ---------- Test search ----------

class TestSearch:
    """Tests for partner_lookup.search() — text search with scoring."""

    def test_search_by_name(self):
        with _mock_partners():
            results = partner_lookup.search("Bom Preço", limit=10)
        assert len(results) >= 1
        assert any(r["id"] == "bp001" for r in results)

    def test_search_by_cnpj(self):
        with _mock_partners():
            results = partner_lookup.search("12345678000190", limit=10)
        assert len(results) >= 1
        assert results[0]["id"] == "bp001"
        assert results[0]["score"] >= 100

    def test_search_by_partner_code(self):
        with _mock_partners():
            results = partner_lookup.search("BP001", limit=10)
        assert any(r["id"] == "bp001" for r in results)

    def test_search_by_id(self):
        with _mock_partners():
            results = partner_lookup.search("bp003", limit=10)
        assert any(r["id"] == "bp003" for r in results)

    def test_search_empty_query(self):
        results = partner_lookup.search("")
        assert results == []

    def test_search_excludes_inactive(self):
        with _mock_partners():
            results = partner_lookup.search("Inactive Corp", limit=10)
        assert all(r["id"] != "bp004_inactive" for r in results)

    def test_search_limit(self):
        with _mock_partners():
            results = partner_lookup.search("a", limit=1)
        assert len(results) <= 1

    def test_search_role_filter(self):
        with _mock_partners():
            results = partner_lookup.search("Bom Preço", role="SUPPLIER", limit=10)
        assert all(r["id"] != "bp001" for r in results)  # bp001 is CUSTOMER only

    def test_search_sorted_by_score(self):
        with _mock_partners():
            results = partner_lookup.search("12345678000190", limit=10)
        if len(results) > 1:
            scores = [r["score"] for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_search_by_partial_name(self):
        with _mock_partners():
            results = partner_lookup.search("Sul", limit=10)
        assert any(r["id"] == "bp002" for r in results)


# ---------- Test as_b2b_cliente ----------

class TestAsB2BCliente:
    """Tests for partner_lookup.as_b2b_cliente() — B2B shape conversion."""

    def test_shape_fields(self):
        p = {
            "display_name": "B2B Test",
            "legal_name": "B2B Test LTDA",
            "trade_name": "B2B",
            "partner_code": "B2B001",
            "person_type": "COMPANY",
            "roles": ["CUSTOMER"],
            "documents": [
                {"document_type": "CNPJ", "document_number": "12345678000190"},
                {"document_type": "IE", "document_number": "123456789"},
            ],
            "addresses": [{
                "address_type": "BILLING",
                "street": "Rua B2B",
                "number": "50",
                "city": "Rio",
                "state": "RJ",
                "preferred": True,
            }],
            "contacts": [{
                "phone": "21999999999",
                "email": "b2b@test.com",
            }],
            "credit_limit": 50000,
            "payment_terms": "30",
        }
        result = partner_lookup.as_b2b_cliente("b2b_001", p)
        assert result["id"] == "b2b_001"
        assert result["cnpj"] == "12345678000190"
        assert result["razao_social"] == "B2B Test LTDA"
        assert result["pessoa"] == "PJ"
        assert result["telefone"] == "21999999999"
        assert result["email"] == "b2b@test.com"
        assert result["credit_limit"] == 50000
        assert result["payment_terms"] == "30"

    def test_person_type_pf(self):
        p = {
            "display_name": "PF Test",
            "person_type": "PERSON",
            "roles": ["CUSTOMER"],
        }
        result = partner_lookup.as_b2b_cliente("pf_001", p)
        assert result["pessoa"] == "PF"

    def test_missing_fields_graceful(self):
        p = {"display_name": "Minimal"}
        result = partner_lookup.as_b2b_cliente("min_001", p)
        assert result["id"] == "min_001"
        assert result["cnpj"] == ""
        assert result["credit_limit"] == 0

    def test_address_format(self):
        p = {
            "addresses": [{
                "street": "Rua X",
                "number": "100",
                "district": "Centro",
                "city": "BH",
                "state": "MG",
                "zip_code": "30000-000",
                "preferred": True,
            }],
        }
        result = partner_lookup.as_b2b_cliente("addr_001", p)
        assert "Rua X" in result["endereco_cobranca"]
        assert "BH" in result["endereco_cobranca"]
        assert "MG" in result["endereco_cobranca"]

    def test_ie_from_documents(self):
        p = {
            "documents": [
                {"document_type": "IE", "document_number": "987654321"},
            ],
        }
        result = partner_lookup.as_b2b_cliente("ie_001", p)
        assert result["ie"] == "987654321"


# ---------- Test list_customers_b2b ----------

class TestListCustomersB2B:
    """Tests for partner_lookup.list_customers_b2b()."""

    def test_returns_only_customers(self):
        with _mock_partners():
            result = partner_lookup.list_customers_b2b()
        ids = [r["id"] for r in result]
        assert "bp001" in ids
        assert "bp003" in ids
        assert "bp002" in ids  # bp002 has both CUSTOMER and SUPPLIER
        # bp004_inactive excluded (INACTIVE)
        assert "bp004_inactive" not in ids
        assert "bp005_external" not in ids  # SUPPLIER only

    def test_sorted_by_razao_social(self):
        with _mock_partners():
            result = partner_lookup.list_customers_b2b()
        names = [r["razao_social"] for r in result]
        assert names == sorted(names, key=str.lower)

    def test_excludes_inactive(self):
        data = {
            "a": {
                "display_name": "Active",
                "roles": ["CUSTOMER"],
                "status": "ACTIVE",
            },
            "b": {
                "display_name": "Inactive",
                "roles": ["CUSTOMER"],
                "status": "INACTIVE",
            },
        }
        with _mock_partners(data):
            result = partner_lookup.list_customers_b2b()
        ids = [r["id"] for r in result]
        assert "a" in ids
        assert "b" not in ids

    def test_default_role_is_customer(self):
        """Without explicit role, defaults to CUSTOMER."""
        data = {
            "c1": {
                "display_name": "Customer 1",
                "roles": ["CUSTOMER"],
                "status": "ACTIVE",
            },
            "s1": {
                "display_name": "Supplier 1",
                "roles": ["SUPPLIER"],
                "status": "ACTIVE",
            },
        }
        with _mock_partners(data):
            result = partner_lookup.list_customers_b2b()
        ids = [r["id"] for r in result]
        assert "c1" in ids
        assert "s1" not in ids
