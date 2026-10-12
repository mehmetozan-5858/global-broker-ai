import unittest
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
