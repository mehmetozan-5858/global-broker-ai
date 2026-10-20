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

    def test_scope_review_removes_flat_price_and_quantity_without_inventing_lot_count(self):
        row = self.sample()
        row.update(source_lot_selection_required=True, public_source_terms={"kind":"notice_estimate", "estimated_budget":"500", "budget_currency":"USD"})
        out = project_public_opportunity(row)
        self.assertTrue(out["lot_selection_required"])
        self.assertNotIn("approx_quantity", out)
        self.assertNotIn("estimated_budget", out)
        self.assertNotIn("lot_count", out)
        self.assertIn("lot_selection", out["dossier_missing_fields"])

    def test_source_review_metadata_never_includes_document_or_private_missing_notes(self):
        row = self.sample()
        row["document_extraction"] = {"parsed_count":1,"attempts":[{"status":"parsed","format":"world_bank_notice_json","url":"https://private.example/notice"}]}
        row["data_completion"] = {"missing_fields":["quantity_or_budget","deadline","Secret buyer email@example.test",{"note":"private"}]}
        out = project_public_opportunity(row)
        self.assertEqual(out["source_text_status"], "official_notice_read")
        self.assertEqual(out["dossier_missing_fields"], ["quantity_or_budget","deadline"])
        self.assertNotIn("private.example", str(out))
        self.assertNotIn("email@example.test", str(out))
        self.assertNotIn("secret full notice", str(out))

    def test_safe_review_metadata_survives_feed_then_api_projection(self):
        row = self.sample()
        row.update(source_lot_selection_required=True, ted_lot_count=2)
        row["document_extraction"] = {"parsed_count":1}
        row["data_completion"] = {"missing_fields":["quantity_or_budget"]}
        first = project_public_opportunity(row)
        second = project_public_opportunity(first)
        for key in ("source_text_status","dossier_missing_fields","lot_selection_required","lot_count"):
            self.assertEqual(second[key], first[key])
        self.assertNotIn("approx_quantity", second)

    def test_read_count_without_text_or_boolean_count_is_not_read_confirmation(self):
        for extraction in ({"parsed_count":1}, {"parsed_count":True}, {"parsed_count":"1"}):
            row = self.sample(); row["document_extraction"] = extraction
            if extraction["parsed_count"] == 1 and type(extraction["parsed_count"]) is int:
                row.pop("document_extracted_text")
            self.assertEqual(project_public_opportunity(row)["source_text_status"], "pending")

    def test_unknown_or_malformed_review_metadata_is_dropped(self):
        for status in ({"private":"secret"}, ["read"], "approved", True):
            row = self.sample(); row["source_text_status"] = status
            self.assertNotIn("source_text_status", project_public_opportunity(row))
        row = self.sample(); row["source_lot_selection_required"] = "true"
        self.assertNotIn("lot_selection_required", project_public_opportunity(row))

    def test_masked_feed_keeps_customer_fields_and_result_notice_restriction(self):
        row = self.sample()
        row.update(source="TED", **{"form-type":"result"})
        row["public_product_detail"] = "Industrial machine scope"
        row["public_source_terms"] = {"kind":"notice_estimate","estimated_budget":"500","budget_currency":"EUR"}
        first = project_public_opportunity(row)
        second = project_public_opportunity(first)
        for key in ("goods_status","approx_quantity","source_backed_fields","source_field_total","product_detail","notice_context","estimated_budget","budget_currency"):
            self.assertEqual(second[key], first[key])
        self.assertTrue(second["notice_context"]["research_only"])
        self.assertNotIn("Secret Buyer", str(second))


if __name__ == "__main__":
    unittest.main()
