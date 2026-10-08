import unittest

from src.enrichment import enrich_opportunity, enrich_payload


class OpportunityEnrichmentTests(unittest.TestCase):
    def test_cpv_code_becomes_readable_product(self):
        item = {
            "classification-cpv": ["38000000", "38310000"],
            "title_tr": "Uluslararası satın alma talebi",
            "detail_tr": "Laboratuvar ekipmanı alımı",
            "buyer-name": "Example Buyer",
            "buyer-country": "RO",
            "source_url": "https://example.test/tender/1",
            "deadline-receipt-tender-date-lot": "2026-11-01",
            "quantity-lot": "10",
        }
        out = enrich_opportunity(item)
        self.assertIn("Laboratuvar", out["product_name"])
        self.assertEqual(out["dossier"]["cpv"][0]["code"], "38000000")

    def test_exact_cpv_label_is_preserved_with_code(self):
        item = {"classification-cpv": "38310000"}
        out = enrich_opportunity(item)
        self.assertEqual(out["dossier"]["cpv"], [{"code": "38310000", "label_tr": "Hassas teraziler"}])

    def test_missing_fields_are_not_invented(self):
        out = enrich_opportunity({"title_original": "Purchase of equipment"})
        self.assertIsNone(out["dossier"]["buyer_name"])
        self.assertIsNone(out["dossier"]["quantity"])
        self.assertIsNone(out["dossier"]["budget_value"])
        self.assertFalse(out["dossier"]["supplier_sourcing_ready"])

    def test_supplier_search_uses_readable_product_and_is_blocked_when_incomplete(self):
        item = {
            "classification-cpv": "38000000",
            "supplier_research": {"status": "source_search_ready", "product_query": "38000000"},
        }
        out = enrich_opportunity(item)
        self.assertNotEqual(out["supplier_research"]["product_query"], "38000000")
        self.assertEqual(out["supplier_research"]["status"], "dossier_enrichment_pending")
        self.assertTrue(out["supplier_research"]["blocked_by_missing_fields"])

    def test_links_are_collected_from_nested_source_fields(self):
        item = {
            "links": {"html": ["https://example.test/a"], "docs": "https://example.test/spec.pdf"},
            "source_url": "https://example.test/a",
        }
        out = enrich_opportunity(item)
        self.assertEqual(out["official_links"], ["https://example.test/a", "https://example.test/spec.pdf"])
        self.assertEqual(out["document_url"], "https://example.test/a")

    def test_china_opportunity_gets_market_research_queue(self):
        item = {
            "market_region": "Çin / Doğu Asya",
            "classification-cpv": "15000000",
            "workflow": {},
        }
        out = enrich_opportunity(item)
        self.assertEqual(out["workflow"]["china_market_research"]["status"], "demand_validation_pending")
        self.assertIn("Çin", out["workflow"]["china_market_research"]["goal"])

    def test_payload_marks_source_only_mode(self):
        payload = enrich_payload({"opportunities": [{"classification-cpv": "38000000"}]})
        self.assertEqual(payload["enrichment"]["mode"], "source_only_no_hallucination")
        self.assertEqual(payload["enrichment"]["enriched_count"], 1)


if __name__ == "__main__":
    unittest.main()
