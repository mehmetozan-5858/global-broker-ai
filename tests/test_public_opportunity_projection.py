import unittest

from src.public_opportunity_projection import BUYER_DISPLAY, project_public_feed, project_public_opportunity


class PublicOpportunityProjectionTests(unittest.TestCase):
    def sample(self):
        return {
            "title": "Industrial CNC machine purchase",
            "country_name": "Germany",
            "country_code": "DE",
            "quantity": "12 units",
            "deadline": "2026-11-20",
            "incoterm": "CIF",
            "source": "Official Procurement Portal",
            "source_type": "public_tender",
            "source_url": "https://example.gov/tender/1",
            "buyer_name": "Secret Buyer GmbH",
            "buyer_email": "buyer@example.com",
            "contact_phone": "+49 123 456",
            "document_extracted_text": "secret full notice",
            "supplier_research": {"verified_supplier_count": 4, "candidates": [{"name": "Supplier One"}]},
            "commercial_feasibility": {"verified_unit_price": 1000},
            "field_evidence": {
                "product": {"status": "source_backed", "value": "CNC machines", "source_url": "https://example.gov/doc"},
                "quantity": {"status": "source_backed", "value": "12 units", "source_excerpt": "private excerpt"},
            },
            "export_goods_review": {"status": "goods_candidate", "reason": "internal reason"},
            "core_field_coverage": {"verified_or_source_backed": 5, "total": 6, "private_notes": "hide"},
        }

    def test_projection_is_allowlist_not_denylist(self):
        out = project_public_opportunity(self.sample())
        self.assertEqual(out["buyer_display"], BUYER_DISPLAY)
        self.assertEqual(out["product_name"], "CNC machines")
        self.assertEqual(out["approx_quantity"], "12 units")
        self.assertEqual(out["sector_id"], "machinery")
        self.assertNotIn("buyer_name", out)
        self.assertNotIn("buyer_email", out)
        self.assertNotIn("contact_phone", out)
        self.assertNotIn("source_url", out)
        self.assertNotIn("document_extracted_text", out)
        self.assertNotIn("supplier_research", out)
        self.assertNotIn("commercial_feasibility", out)
        self.assertNotIn("field_evidence", out)
        self.assertNotIn("export_goods_review", out)
        self.assertNotIn("core_field_coverage", out)

    def test_unknown_fields_are_dropped_by_default(self):
        row = self.sample()
        row["brand_new_private_agent_output"] = {"contact": "secret"}
        self.assertNotIn("brand_new_private_agent_output", project_public_opportunity(row))

    def test_public_feed_only_contains_goods_candidates_and_safe_top_level(self):
        good = self.sample()
        bad = dict(good)
        bad["export_goods_review"] = {"status": "service_candidate"}
        feed = project_public_feed({"opportunities": [good, bad], "agent_center": {"secrets": True}})
        self.assertEqual(feed["mode"], "public_allowlist_feed")
        self.assertEqual(feed["count"], 1)
        self.assertNotIn("agent_center", feed)
        self.assertEqual(feed["opportunities"][0]["buyer_display"], BUYER_DISPLAY)


if __name__ == "__main__":
    unittest.main()
