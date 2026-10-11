import unittest

from src.contact_enrichment import enrich_opportunity, enrich_payload


class ContactEnrichmentTests(unittest.TestCase):
    def test_extracts_contextual_email_and_phone_from_source_text(self):
        row = {
            "document_extracted_text": (
                "Procurement contact for this tender: Jane Doe. "
                "Email: tenders@example.gov Phone: +44 20 7946 0958."
            ),
            "source_url": "https://example.gov/tender/123",
        }
        out = enrich_opportunity(row)
        self.assertTrue(out["direct_contact_available"])
        self.assertTrue(out["contact_source_backed"])
        self.assertEqual(out["contact_email"], "tenders@example.gov")
        self.assertEqual(out["contact_phone"], "+44 20 7946 0958")
        self.assertEqual(out["contact_enrichment"]["route_type"], "direct_contact")

    def test_does_not_promote_uncontextual_email(self):
        row = {
            "document_extracted_text": "Copyright notice webmaster@example.org archive copy.",
            "source_url": "https://example.org/tender/123",
        }
        out = enrich_opportunity(row)
        self.assertFalse(out["direct_contact_available"])
        self.assertFalse(out["contact_source_backed"])
        self.assertEqual(out["contact_enrichment"]["route_type"], "official_source_route")

    def test_structured_https_website_is_source_backed_route(self):
        row = {"buyer_website": "https://buyer.example.com"}
        out = enrich_opportunity(row)
        self.assertFalse(out["direct_contact_available"])
        self.assertTrue(out["contact_source_backed"])
        self.assertEqual(out["contact_enrichment"]["route_type"], "verified_web")

    def test_payload_summary_counts_contact_quality(self):
        payload = {
            "opportunities": [
                {"contact_email": "buy@example.com"},
                {"buyer_website": "https://buyer.example.com"},
                {"source_url": "https://source.example/tender"},
            ]
        }
        out = enrich_payload(payload)
        summary = out["contact_enrichment_summary"]
        self.assertEqual(summary["direct_contacts"], 1)
        self.assertEqual(summary["source_backed_contacts"], 2)
        self.assertEqual(summary["contact_routes"], 3)


if __name__ == "__main__":
    unittest.main()
