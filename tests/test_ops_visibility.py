import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class OpsVisibilityTests(unittest.TestCase):
    def test_customer_and_admin_shells_load_system_health(self):
        customer = (ROOT / "web/customer-shell.html").read_text(encoding="utf-8")
        admin = (ROOT / "web/app-shell.html").read_text(encoding="utf-8")
        self.assertIn("/web/system-health.js", customer)
        self.assertIn("/web/system-health.js", admin)

    def test_system_health_surfaces_watchdog_deals_and_launch_gate_truthfully(self):
        js = (ROOT / "web/system-health.js").read_text(encoding="utf-8")
        self.assertIn("watchdog", js)
        self.assertIn("deal_lifecycle_summary", js)
        self.assertIn("launch_readiness_report", js)
        self.assertIn("canlıya hazır yüzdesi", js)
        self.assertIn("ölçülemiyor", js)
        self.assertNotIn("auto_restart_executed=true", js)

    def test_ci_checks_all_injected_operational_scripts(self):
        workflow = (ROOT / ".github/workflows/verified-brokerage-ci.yml").read_text(encoding="utf-8")
        for name in (
            "customer-brand-bridge.js",
            "operational-panels.js",
            "opportunity-readiness.js",
            "opportunity-dossier.js",
            "ceo-priority.js",
            "today-tasks.js",
            "task-center.js",
            "system-health.js",
        ):
            self.assertIn(f"node --check web/{name}", workflow)


if __name__ == "__main__":
    unittest.main()
