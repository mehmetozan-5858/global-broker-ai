import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELD = (ROOT / "src/field_evidence.py").read_text(encoding="utf-8")
QUICK = (ROOT / "web/customer-priority.js").read_text(encoding="utf-8")
DEPLOY = (ROOT / ".github/workflows/deploy-mobile.yml").read_text(encoding="utf-8")
CI = (ROOT / ".github/workflows/verified-brokerage-ci.yml").read_text(encoding="utf-8")


class W2A3PriorityQueueTests(unittest.TestCase):
    def test_a3_builds_research_queue_without_inference(self):
        self.assertIn('field_research_queue', FIELD)
        self.assertIn('critical_missing_fields', FIELD)
        self.assertIn('"quantity", "deadline"', FIELD)
        self.assertIn('research source/document only; do not infer missing facts', FIELD)
        self.assertIn('high_priority_research', FIELD)

    def test_w2_has_quick_quality_views(self):
        self.assertIn('Hızlı görünüm', QUICK)
        self.assertIn('En güçlü', QUICK)
        self.assertIn('6/6 tam veri', QUICK)
        self.assertIn('cpQuality', QUICK)

    def test_customer_priority_script_is_deployed_and_checked(self):
        self.assertIn('customer-priority.js', DEPLOY)
        self.assertIn('node --check web/customer-priority.js', CI)


if __name__ == "__main__":
    unittest.main()
