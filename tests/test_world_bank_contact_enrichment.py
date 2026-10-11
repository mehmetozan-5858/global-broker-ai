import unittest

from src.contact_enrichment import enrich_opportunity


class WorldBankContactEnrichmentTests(unittest.TestCase):
    def test_notice_text_can_supply_source_backed_direct_contact(self):
        item = {
            "source": "WORLD_BANK",
            "source_url": "https://projects.worldbank.org/example",
            "notice_text": "Procurement contact: procurement.office@example.org Telephone: +1 202 555 0188",
        }
        result = enrich_opportunity(item)
        self.assertTrue(result["direct_contact_available"])
        self.assertTrue(result["contact_source_backed"])
        self.assertEqual(result["contact_email"], "procurement.office@example.org")
        self.assertIn("202", result["contact_phone"])
        self.assertEqual(result["contact_enrichment"]["evidence_source"], "notice_text")

    def test_unrelated_email_without_contact_context_is_not_promoted(self):
        item = {
            "source": "WORLD_BANK",
            "source_url": "https://projects.worldbank.org/example",
            "notice_text": "Copyright archive@example.org. This notice concerns office equipment.",
        }
        result = enrich_opportunity(item)
        self.assertFalse(result["direct_contact_available"])
        self.assertEqual(result["contact_enrichment"]["route_type"], "official_source_route")


if __name__ == "__main__":
    unittest.main()
