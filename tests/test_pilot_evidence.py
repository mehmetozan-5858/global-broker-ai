import unittest

from src.pilot_evidence import apply
from src.verification import sanitize_payload


class PilotEvidenceTests(unittest.TestCase):
    def test_first_pilot_gets_authoritative_buyer_evidence_without_fake_price(self):
        row = {
            "id": "saudi-etimad-261039003553",
            "source": "Saudi Etimad official visitor API",
            "source_url": "https://tenders.etimad.sa/example",
            "buyer-name": "الهيئة السعودية للمياه",
            "buyer-country": "Saudi Arabia",
        }
        payload = apply({"opportunities": [row]})
        sanitize_payload(payload)
        self.assertTrue(row["buyer_verified"])
        self.assertEqual(row["buyer_verification"]["status"], "verified")
        self.assertEqual(row["buyer_verification"]["independent_registry_checks"], 2)
        self.assertNotIn("verified_unit_price", row)
        self.assertNotIn("quantity", row)

    def test_supplier_leads_remain_exact_spec_pending(self):
        row = {"id": "saudi-etimad-261039003553"}
        apply({"opportunities": [row]})
        research = row["stage4_research"]
        leads = research["supplier_leads"]
        self.assertGreaterEqual(len(leads), 6)
        self.assertTrue(all("exact_spec_pending" in lead["status"] for lead in leads))
        self.assertNotIn("supplier_candidates", row)
        self.assertEqual(research["document_access_gate"]["status"], "full_tender_document_required")
        self.assertFalse(research["document_access_gate"]["payment_authorized"])

    def test_independent_qualification_does_not_become_exact_supplier_verification(self):
        row = {"id": "saudi-etimad-261039003553"}
        apply({"opportunities": [row]})
        leads = row["stage4_research"]["supplier_leads"]
        riyadh = next(x for x in leads if x["name"] == "Riyadh Cables")
        self.assertEqual(riyadh["independent_qualification"]["scope"], "LV Power cables")
        self.assertNotIn("supplier_candidates", row)
        self.assertNotIn("verified_unit_price", row)

    def test_unlisted_opportunity_is_unchanged(self):
        row = {"id": "other"}
        payload = apply({"opportunities": [row]})
        self.assertEqual(payload["pilot_evidence_summary"]["applied"], 0)
        self.assertEqual(row, {"id": "other"})


if __name__ == "__main__":
    unittest.main()
