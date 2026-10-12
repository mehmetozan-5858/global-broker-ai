import unittest

from src.verification import sanitize_opportunity, sanitize_payload


class BuyerVerificationStage2Tests(unittest.TestCase):
    def test_official_notice_confirms_source_but_not_full_verification(self):
        item = {
            "buyer-name": "Example Ministry",
            "buyer-country": "Germany",
            "source": "TED",
            "source_url": "https://example.eu/notice/1",
            "deal_score": 80,
        }
        sanitize_opportunity(item)
        self.assertFalse(item["buyer_verified"])
        self.assertEqual(item["buyer_verification"]["status"], "source_confirmed")
        self.assertEqual(item["buyer_verification"]["verification_level"], 1)
        self.assertTrue(item["buyer_verification"]["official_source_confirmed"])

    def test_authoritative_registry_evidence_can_verify_buyer(self):
        item = {
            "buyer-name": "Example Public Entity",
            "buyer-country": "France",
            "source": "TED",
            "source_url": "https://example.eu/notice/2",
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
        self.assertEqual(item["buyer_verification"]["status"], "verified")
        self.assertEqual(item["buyer_verification"]["verification_level"], 3)

    def test_weak_registry_evidence_does_not_verify(self):
        item = {
            "buyer-name": "Example Buyer",
            "buyer-country": "Italy",
            "source_url": "https://example.eu/notice/3",
            "buyer_registry_evidence": [
                {
                    "authority": "search_engine",
                    "url": "https://example.com/result",
                    "name_match": True,
                    "country_match": True,
                }
            ],
        }
        sanitize_opportunity(item)
        self.assertFalse(item["buyer_verified"])
        self.assertEqual(item["buyer_verification"]["status"], "source_confirmed")

    def test_payload_builds_prioritized_verification_queue(self):
        payload = {
            "opportunities": [
                {
                    "id": "A",
                    "buyer-name": "Source Confirmed Buyer",
                    "buyer-country": "Norway",
                    "source": "TED",
                    "source_url": "https://example.eu/notice/a",
                    "deal_score": 90,
                    "contact_enrichment": {"status": "source_backed"},
                },
                {
                    "id": "B",
                    "buyer-name": "Name Only",
                    "buyer-country": "Spain",
                    "deal_score": 95,
                },
                {
                    "id": "C",
                    "buyer-country": "Poland",
                    "deal_score": 70,
                },
            ]
        }
        sanitize_payload(payload)
        summary = payload["buyer_verification_summary"]
        self.assertEqual(summary["opportunities"], 3)
        self.assertEqual(summary["verified"], 0)
        self.assertEqual(summary["source_confirmed"], 1)
        self.assertEqual(summary["identity_found_source_missing"], 1)
        self.assertEqual(summary["identity_pending"], 1)
        self.assertEqual(summary["queue_count"], 3)
        self.assertEqual(summary["queue"][0]["opportunity_id"], "A")


if __name__ == "__main__":
    unittest.main()
