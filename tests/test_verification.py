import unittest

from src.verification import buyer_is_verified, sanitize_opportunity


class TestBuyerVerification(unittest.TestCase):
    def test_name_alone_is_not_verification(self):
        item = {"buyer-name": "Example Ministry", "buyer_verified": True}
        sanitize_opportunity(item)
        self.assertFalse(item["buyer_verified"])
        self.assertEqual(item["compliance_status"], "buyer_identified_due_diligence_pending")

    def test_explicit_verified_record_requires_evidence(self):
        item = {"buyer-name": "Example Ministry", "buyer_verification": {"status": "verified", "evidence": []}}
        self.assertFalse(buyer_is_verified(item))

    def test_authoritative_registry_evidence_passes(self):
        item = {
            "buyer-name": "Example Ministry",
            "buyer-country": "Germany",
            "source": "TED",
            "source_url": "https://example.test/tender/123",
            "buyer_registry_evidence": [
                {
                    "authority": "public_entity_registry",
                    "url": "https://registry.example.gov/entity/123",
                    "name_match": True,
                    "country_match": True,
                }
            ],
        }
        sanitize_opportunity(item)
        self.assertTrue(item["buyer_verified"])
        self.assertEqual(item["compliance_status"], "buyer_verified_due_diligence_complete")

    def test_risk_agent_separates_source_identification(self):
        item = {"buyer-name": "Example Ministry", "risk_agent": {"buyer_source_verified": True}}
        sanitize_opportunity(item)
        self.assertTrue(item["risk_agent"]["buyer_source_identified"])
        self.assertFalse(item["risk_agent"]["buyer_verified"])
        self.assertNotIn("buyer_source_verified", item["risk_agent"])

    def test_workflow_buyer_status_remains_pending(self):
        item = {
            "buyer-name": "Example Ministry",
            "workflow": {"buyer": {"verified": True, "status": "verified"}},
        }
        sanitize_opportunity(item)
        self.assertFalse(item["workflow"]["buyer"]["verified"])
        self.assertEqual(item["workflow"]["buyer"]["status"], "source_identified_due_diligence_pending")


if __name__ == "__main__":
    unittest.main()
