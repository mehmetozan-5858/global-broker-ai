import unittest

from src.physical_goods_gate import apply_gate


class PhysicalGoodsGateTests(unittest.TestCase):
    def test_only_goods_candidates_reach_main_pipeline(self):
        payload = {
            "opportunities": [
                {"title_original": "Supply and delivery of 500 steel chairs", "procurement_category": "Goods"},
                {"title_original": "Supply of pumps with installation", "procurement_category": "Goods"},
                {"title_original": "Engineering consultancy for water network", "procurement_category": "Consulting Services"},
                {"title_original": "Cloud software subscription"},
                {"title_original": "Project phase two"},
            ]
        }
        out = apply_gate(payload)
        self.assertEqual(len(out["opportunities"]), 1)
        self.assertEqual(out["opportunities"][0]["export_goods_review"]["status"], "goods_candidate")
        self.assertEqual(len(out["goods_review_queue"]), 2)
        self.assertEqual(out["physical_goods_gate"]["excluded_service_or_works"], 1)
        self.assertEqual(out["physical_goods_gate"]["excluded_non_physical"], 1)
        self.assertTrue(out["physical_goods_gate"]["research_pipeline_receives_only_goods_candidates"])

    def test_gate_recalculates_stale_old_classification(self):
        payload = {
            "opportunities": [
                {
                    "title_original": "Construction works including equipment",
                    "contract-nature": "works",
                    "export_goods_review": {"status": "goods_candidate"},
                }
            ]
        }
        out = apply_gate(payload)
        self.assertEqual(out["opportunities"], [])
        self.assertEqual(out["physical_goods_gate"]["excluded_service_or_works"], 1)


if __name__ == "__main__":
    unittest.main()
