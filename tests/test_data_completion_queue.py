import unittest

from src.data_completion_queue import build


class DataCompletionQueueTests(unittest.TestCase):
    def test_complete_and_incomplete_rows_are_counted(self):
        payload = {
            "opportunities": [
                {
                    "opportunity_id": "A",
                    "buyer_name": "Buyer A",
                    "product_name": "Pump",
                    "quantity": "10 units",
                    "deadline": "2026-12-31",
                    "country": "DE",
                    "source_url": "https://example.org/a",
                },
                {
                    "opportunity_id": "B",
                    "product_name": "Valve",
                    "country": "FR",
                },
            ]
        }

        result = build(payload)

        self.assertEqual(result["opportunities_reviewed"], 2)
        self.assertEqual(result["core_complete"], 1)
        self.assertEqual(result["core_incomplete"], 1)
        self.assertEqual(result["queue_count"], 1)
        self.assertIn("buyer_identity", result["queue"][0]["missing_core_fields"])
        self.assertEqual(result["queue"][0]["next_agent"], "source_research_agent")

    def test_near_complete_official_source_gets_priority(self):
        payload = {
            "opportunities": [
                {
                    "opportunity_id": "near",
                    "buyer_name": "Buyer",
                    "product_name": "Machine",
                    "quantity": "1",
                    "country": "IT",
                    "source_url": "https://example.org/near",
                },
                {
                    "opportunity_id": "far",
                    "product_name": "Machine 2",
                },
            ]
        }

        result = build(payload)

        self.assertEqual(result["queue"][0]["opportunity_id"], "near")
        self.assertEqual(result["queue"][0]["missing_core_fields"], ["deadline"])
        self.assertEqual(result["queue"][0]["next_agent"], "source_terms_agent")


if __name__ == "__main__":
    unittest.main()
