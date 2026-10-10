import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ShadowScanHealthGateTests(unittest.TestCase):
    def test_shadow_scan_requires_watchdog_and_deal_outputs_before_publish(self):
        workflow = (ROOT / ".github/workflows/shadow-scan.yml").read_text(encoding="utf-8")
        self.assertIn("'watchdog'", workflow)
        self.assertIn("'deal_lifecycle_summary'", workflow)
        self.assertIn("'launch_readiness_report'", workflow)
        self.assertIn("unexpected production launch", workflow)

    def test_remaining_pipeline_is_still_the_source_of_health_outputs(self):
        workflow = (ROOT / ".github/workflows/shadow-scan.yml").read_text(encoding="utf-8")
        self.assertIn('python -m src.remaining_pipeline "$NEXT"', workflow)
        self.assertIn("A4-A12", workflow)


if __name__ == "__main__":
    unittest.main()
