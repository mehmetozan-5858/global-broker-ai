import unittest

from src.supplier_research import MIN_VERIFIED_SUPPLIERS, process_payload


class Stage3SupplierMatchingTests(unittest.TestCase):
    def base_item(self):
        return {
            "title_original": "Industrial pumps",
            "deal_score": 60,
            "field_evidence": {
                "product": {"value": "Industrial pumps"},
                "country": {"value": "Saudi Arabia"},
            },
            "specification_analysis": {"supplier_sourcing_ready": True},
        }

    def candidate(self, n):
        return {
            "name": f"Pump Maker {n}",
            "source_url": f"https://example{n}.com/pumps",
            "product_match_evidence": "Manufacturer of industrial pumps",
            "identity_verification_evidence": f"Official company website identifies Pump Maker {n}",
        }

    def test_ready_opportunity_enters_supplier_matching_queue(self):
        payload = process_payload({"opportunities": [self.base_item()]})
        queue = payload["supplier_matching_queue"]
        self.assertEqual(queue["stage"], 3)
        self.assertEqual(queue["task_count"], 1)
        task = queue["tasks"][0]
        self.assertEqual(task["additional_verified_suppliers_needed"], MIN_VERIFIED_SUPPLIERS)
        self.assertFalse(task["external_contact_authorized"])

    def test_three_verified_suppliers_make_pool_ready(self):
        item = self.base_item()
        item["supplier_candidates"] = [self.candidate(1), self.candidate(2), self.candidate(3)]
        payload = process_payload({"opportunities": [item]})
        summary = payload["supplier_research_summary"]
        self.assertEqual(summary["verified_suppliers"], 3)
        self.assertEqual(summary["opportunities_with_minimum_verified_pool"], 1)
        self.assertEqual(payload["supplier_matching_queue"]["tasks"][0]["status"], "minimum_verified_pool_ready")

    def test_unready_specification_is_not_sent_to_matching_queue(self):
        item = self.base_item()
        item["specification_analysis"] = {"supplier_sourcing_ready": False}
        payload = process_payload({"opportunities": [item]})
        self.assertEqual(payload["supplier_matching_queue"]["task_count"], 0)
        self.assertEqual(payload["supplier_research_summary"]["blocked"], 1)


if __name__ == "__main__":
    unittest.main()
