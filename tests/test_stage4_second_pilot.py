import unittest

from src.exportable_goods import classify
from src.pilot_evidence_nl import apply
from src.verification import sanitize_payload


class Stage4SecondPilotTests(unittest.TestCase):
    def test_netherlands_police_dossier_gets_real_source_and_buyer_verification(self):
        row = {
            "id": "gb_04100c0f0da5c6a5c11d27f6253bf28c",
            "source": "TED",
            "document_url": "https://ted.europa.eu/en/notice/663841-2026/xml",
            "buyer-name": "Politie",
            "buyer-country": "NLD",
            "quantity": "32000",
        }
        payload = apply({"opportunities": [row]})
        sanitize_payload(payload)
        self.assertEqual(row["source_url"], "https://ted.europa.eu/en/notice/-/detail/663841-2026")
        self.assertTrue(row["buyer_verified"])
        self.assertEqual(row["buyer_verification"]["independent_registry_checks"], 2)
        self.assertEqual(row["stage4_research"]["quantity"], "32000")
        self.assertEqual(len(row["stage4_research"]["supplier_leads"]), 4)
        self.assertFalse(row["stage4_research"]["document_access_gate"]["external_purchase_required"])
        self.assertNotIn("verified_unit_price", row)

    def test_supplier_leads_are_not_promoted_before_exact_spec_match(self):
        row = {"id": "gb_04100c0f0da5c6a5c11d27f6253bf28c"}
        apply({"opportunities": [row]})
        leads = row["stage4_research"]["supplier_leads"]
        self.assertTrue(all("exact_spec_pending" in x["status"] for x in leads))
        self.assertNotIn("supplier_candidates", row)
        self.assertEqual(row["stage4_research"]["price_status"], "not_quoted")

    def test_local_manpower_tender_cannot_enter_goods_pipeline(self):
        row = {
            "title_original": "Framework Agreement for the Supply of Local Manpower for Various Sports Venues on a Call-Off",
            "procurement_category": "goods",
            "contract-nature": "supplies",
        }
        decision = classify(row)
        self.assertEqual(decision["status"], "review_mixed")
        self.assertNotEqual(decision["status"], "goods_candidate")


if __name__ == "__main__":
    unittest.main()
