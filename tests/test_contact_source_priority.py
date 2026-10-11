import unittest

from src.contact_source_priority import prioritize_payload, score_row, source_family


class ContactSourcePriorityTests(unittest.TestCase):
    def test_sam_source_with_buyer_and_contact_terms_scores_high(self):
        row = {
            "source": "SAM_GOV",
            "source_url": "https://sam.gov/opp/example",
            "buyer-name": "Example Agency",
            "document_extracted_text": "Procurement contact information will be provided here.",
            "buyer_verified": True,
        }
        score, reasons = score_row(row)
        self.assertGreaterEqual(score, 160)
        self.assertIn("source:sam.gov", reasons)
        self.assertIn("contact_terms_in_source", reasons)

    def test_known_portal_family_is_detected(self):
        row = {"source_url": "https://tenders.etimad.sa/Tender/123", "source": "Saudi Etimad official visitor API"}
        self.assertEqual(source_family(row), "etimad")

    def test_prioritize_payload_writes_metadata(self):
        payload = {"opportunities": [{"source": "Qatar Monaqasat", "official_url": "https://monaqasat.mof.gov.qa/tender/1"}]}
        out = prioritize_payload(payload)
        row = out["opportunities"][0]
        self.assertIn("contact_discovery_priority", row)
        self.assertEqual(row["contact_source_family"], "monaqasat")
        self.assertEqual(out["contact_source_priority_summary"]["scored"], 1)

    def test_existing_direct_contact_is_not_deprioritized(self):
        score, reasons = score_row({"contact_email": "buyer@example.gov", "source": "unknown"})
        self.assertEqual(score, 1000)
        self.assertIn("already_direct", reasons)


if __name__ == "__main__":
    unittest.main()
