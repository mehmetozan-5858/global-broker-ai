import unittest

from src.launch_readiness_report import build


class LaunchReadinessReportTests(unittest.TestCase):
    def test_worldwide_scope_does_not_hide_gulf_launch_blocker(self):
        payload = {
            "launch_gate": {
                "launch_ready": False,
                "blockers": ["gulf_current_scan_verified", "payment_provider_tested"],
                "checks": {"gulf_current_scan_verified": False, "payment_provider_tested": False},
            },
            "gulf_sources": {
                "saudi_live_ingestion_verified": True,
                "qatar_live_ingestion_verified": True,
                "uae_live_ingestion_verified": False,
            },
        }
        result = build(payload)
        self.assertTrue(result["global_market_scope"])
        self.assertFalse(result["production_launch_ready"])
        self.assertEqual(result["mode"], "shadow")
        self.assertFalse(result["priority_gulf_sources"]["United Arab Emirates"]["live_this_scan"])
        self.assertIn("payment_provider_tested", result["categories"]["legal_payment_contact"]["pending"])
        self.assertIsNone(result["readiness_percent"])

    def test_missing_checks_are_fail_closed(self):
        result = build({})
        self.assertFalse(result["production_launch_ready"])
        self.assertFalse(result["categories"]["security_storage"]["ready"])
        self.assertEqual(result["categories"]["security_storage"]["passed"], 0)

    def test_full_checks_do_not_override_launch_gate(self):
        from src.launch_readiness_report import CATEGORIES
        checks = {name: True for group in CATEGORIES.values() for name in group}
        result = build({"launch_gate": {"launch_ready": False, "checks": checks}})
        self.assertFalse(result["production_launch_ready"])
        self.assertEqual(result["mode"], "shadow")


if __name__ == "__main__":
    unittest.main()
