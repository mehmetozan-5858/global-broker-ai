import unittest

from src.sales_acceleration import acceleration_score, enrich_payload, next_action


class SalesAccelerationTests(unittest.TestCase):
    def test_specification_ready_unverified_buyer_goes_to_buyer_verification(self):
        item = {
            "supplier_ready": True,
            "sales_priority": {"grade": "C", "reasons": []},
            "source_url": "https://example.org/1",
            "title_tr": "Makine alımı",
        }
        action = next_action(item)
        self.assertEqual(action["action"], "verify_buyer")
        self.assertEqual(action["owner"], "Risk")

    def test_incomplete_specification_is_first_blocker(self):
        item = {
            "sales_priority": {"grade": "C", "reasons": []},
            "buyer_verification": {"status": "verified", "evidence": ["registry"]},
        }
        self.assertEqual(next_action(item)["action"], "complete_specification")

    def test_verified_chain_advances_to_supplier(self):
        item = {
            "supplier_ready": True,
            "sales_priority": {"grade": "C", "reasons": ["verified_buyer"]},
            "supplier_status": "pending",
        }
        self.assertEqual(next_action(item)["action"], "verify_supplier")

    def test_work_priority_rewards_source_backed_readiness_not_guesses(self):
        bare = acceleration_score({})
        ready = acceleration_score({
            "supplier_ready": True,
            "source_url": "https://example.org/2",
            "estimated_value": 500000,
            "deadline": "2026-12-01",
            "title_tr": "Industrial equipment",
        })
        self.assertEqual(bare, 0)
        self.assertGreaterEqual(ready, 80)

    def test_payload_builds_sorted_top_queue(self):
        payload = {
            "opportunities": [
                {"source_id": "low", "sales_priority": {"grade": "C", "reasons": []}},
                {
                    "source_id": "high",
                    "supplier_ready": True,
                    "source_url": "https://example.org/high",
                    "estimated_value": 100,
                    "deadline": "2026-11-01",
                    "title_tr": "Makine",
                    "sales_priority": {"grade": "C", "reasons": []},
                },
            ]
        }
        enrich_payload(payload, top_n=2)
        queue = payload["sales_acceleration_summary"]["top_queue"]
        self.assertEqual(queue[0]["source_id"], "high")
        self.assertTrue(payload["opportunities"][0]["sales_acceleration"]["does_not_claim_close_probability"])


if __name__ == "__main__":
    unittest.main()
