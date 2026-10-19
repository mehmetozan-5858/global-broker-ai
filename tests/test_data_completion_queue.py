import unittest

from src.data_completion_queue import build


class DataCompletionQueueTests(unittest.TestCase):
    def test_feed_aliases_do_not_create_false_missing_fields(self):
        row = {"borrower": "Public Buyer", "title": "Industrial pumps", "qty": 12,
               "responseDeadLine": "2026-12-31", "project_ctry_code": "DE",
               "notice_url": "https://example.org/notice/123"}
        self.assertEqual(build({"opportunities": [row]})["core_complete"], 1)

    def test_missing_ids_stay_addressable_across_reordering(self):
        a = {"title_original": "Pumps", "source": "official A"}
        b = {"title_original": "Valves", "source": "official B"}
        def ids(rows):
            return {x["product"]: x["opportunity_id"] for x in build({"opportunities": rows})["queue"]}
        first = ids([a,b])
        self.assertEqual(first, ids([b,a]))
        self.assertTrue(all(first.values()))
        self.assertEqual(len(set(first.values())), 2)

    def test_unknown_and_invalid_values_cannot_complete_a_record(self):
        row = {"buyer_name": "Buyer", "product_name": "Pump", "quantity": False,
               "deadline": "TBD", "country": "DE", "source_url": "https://"}
        result = build({"opportunities": [row]})
        self.assertEqual(result["core_complete"], 0)
        self.assertEqual(set(result["queue"][0]["missing_core_fields"]),
                         {"quantity_or_budget", "deadline", "official_source"})
        for quantity in [0, -1, "0", {}]:
            row["quantity"] = quantity
            self.assertIn("quantity_or_budget", build({"opportunities": [row]})["queue"][0]["missing_core_fields"])

    def test_project_title_is_not_buyer_identity(self):
        row = {"project_name": "Bridge Project", "title": "Pumps"}
        self.assertIn("buyer_identity", build({"opportunities": [row]})["queue"][0]["missing_core_fields"])

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
