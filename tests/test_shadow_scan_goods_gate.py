import unittest
from pathlib import Path


WORKFLOW = (Path(__file__).resolve().parents[1] / ".github/workflows/shadow-scan.yml").read_text(encoding="utf-8")


class ShadowScanGoodsGateTests(unittest.TestCase):
    def test_goods_gate_runs_before_enrichment(self):
        gate = WORKFLOW.index("scan_step physical_goods_gate")
        enrich = WORKFLOW.index("scan_step enrichment")
        self.assertLess(gate, enrich)

    def test_live_validation_rejects_non_goods_records(self):
        self.assertIn("physical-goods gate violation", WORKFLOW)
        self.assertIn("!= 'goods_candidate'", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
