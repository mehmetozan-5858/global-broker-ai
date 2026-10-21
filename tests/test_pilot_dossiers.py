import unittest
from datetime import date
from src.pilot_dossiers import build


class PilotDossiersTests(unittest.TestCase):
    def test_ranks_real_evidence_without_inventing_it(self):
        weak = {"id": "weak", "product_name": "Pump"}
        strong = {
            "id": "strong", "product_name": "Industrial Pump",
            "source_url": "https://official.example/tender/1",
            "buyer_name": "Buyer Co", "quantity": "200", "deadline": "2026-12-01",
            "country": "Türkiye", "buyer_verified": True,
            "specification_analysis": {"supplier_sourcing_ready": True},
            "supplier_research": {"verified_supplier_count": 1},
            "price_margin_gate": {"price_ready": True},
        }
        data = build({"opportunities": [weak, strong]})
        summary = data["pilot_dossier_summary"]
        self.assertEqual(summary["first_ten"][0]["opportunity_id"], "strong")
        self.assertEqual(summary["fully_evidenced_count"], 1)
        self.assertIn("verified_supplier", weak["commercial_dossier"]["missing_evidence"])
        self.assertIn("exact_specification", weak["commercial_dossier"]["missing_evidence"])
        self.assertNotIn("verified_unit_price", weak)

    def test_document_url_counts_as_official_source_but_not_exact_spec(self):
        row = {
            "id": "ted-row",
            "document_url": "https://ted.europa.eu/en/notice/663841-2026/xml",
            "product_name": "LHP carry equipment",
            "buyer_name": "Politie",
            "quantity": "32000",
            "deadline": "2026-11-05",
            "country": "NLD",
            "buyer_verified": True,
        }
        build({"opportunities": [row]})
        dossier = row["commercial_dossier"]
        self.assertNotIn("source_url", dossier["missing_evidence"])
        self.assertIn("exact_specification", dossier["missing_evidence"])
        self.assertEqual(
            dossier["official_source"],
            "https://ted.europa.eu/en/notice/663841-2026/xml",
        )

    def test_exact_specification_precedes_supplier_pricing(self):
        row = {
            "id": "x",
            "source_url": "https://official.example/x",
            "product_name": "Bag",
            "buyer_name": "Buyer",
            "quantity": "10",
            "deadline": "2026-12-01",
            "country": "NLD",
            "buyer_verified": True,
        }
        data = build({"opportunities": [row]})
        self.assertEqual(
            data["pilot_dossier_summary"]["first_ten"][0]["next_step"],
            "extract exact technical specification from procurement documents",
        )

    def test_empty_and_limited(self):
        self.assertEqual(build({"opportunities": []})["pilot_dossier_summary"]["selected_count"], 0)
        data = build({"opportunities": [{"id": str(i)} for i in range(12)]})
        self.assertEqual(data["pilot_dossier_summary"]["selected_count"], 10)
        self.assertEqual(len(data["pilot_dossier_summary"]["first_ten"]), 10)


if __name__ == "__main__":
    unittest.main()


class PilotFreshnessTests(unittest.TestCase):
    def row(self, identity, deadline):
        return {"id": identity, "deadline": deadline, "product_name": "Pump", "quantity": "25",
                "source_url": "https://official.example/tender", "buyer_name": "Buyer", "country": "NLD"}

    def test_current_notice_outranks_better_filled_expired_notice_without_deleting_it(self):
        expired = self.row("old", "2026-10-20")
        expired.update(buyer_verified=True, specification_analysis={"supplier_sourcing_ready": True},
                       supplier_research={"verified_supplier_count": 1}, price_margin_gate={"price_ready": True})
        current = {"id": "current", "deadline": "2026-10-21"}
        result = build({"opportunities": [expired, current]}, today=date(2026, 10, 21))
        summary = result["pilot_dossier_summary"]
        self.assertEqual(summary["first_ten"][0]["opportunity_id"], "current")
        self.assertEqual(summary["opportunities_reviewed"], 2)
        self.assertEqual(summary["fully_evidenced_count"], 0)
        self.assertIn("current_deadline", expired["commercial_dossier"]["missing_evidence"])

    def test_result_notice_with_future_date_is_research_only(self):
        result = self.row("result", "2026-12-01")
        result.update(source="TED", **{"form-type": "result"})
        current = {"id": "current", "deadline": "2026-11-01"}
        summary = build({"opportunities": [result, current]}, today=date(2026, 10, 21))["pilot_dossier_summary"]
        self.assertEqual(summary["first_ten"][0]["opportunity_id"], "current")
        self.assertIn("call_for_tenders", result["commercial_dossier"]["missing_evidence"])

    def test_unselected_lots_block_flat_quantity_and_specification(self):
        for flag in ("source_lot_selection_required", "ted_lot_selection_required"):
            row = self.row("lot", "2026-11-01")
            row[flag] = True
            row["specification_analysis"] = {"supplier_sourcing_ready": True}
            summary = build({"opportunities": [row]}, today=date(2026, 10, 21))["pilot_dossier_summary"]
            dossier = row["commercial_dossier"]
            for missing in ("lot_selection", "quantity", "exact_specification"):
                self.assertIn(missing, dossier["missing_evidence"])
            self.assertFalse(dossier["exact_specification_ready"])
            self.assertIn("select and verify one lot", summary["first_ten"][0]["next_step"])

    def test_unknown_deadline_and_normalized_deadline(self):
        row = self.row("unknown", "bad-date")
        build({"opportunities": [row]}, today=date(2026, 10, 21))
        self.assertEqual(row["commercial_dossier"]["freshness_status"], "deadline_unknown_review")
        row["deadline_normalized"] = "2026-11-01"
        build({"opportunities": [row]}, today=date(2026, 10, 21))
        self.assertNotIn("current_deadline", row["commercial_dossier"]["missing_evidence"])
        self.assertFalse(row["commercial_dossier"]["external_outreach_enabled"])
