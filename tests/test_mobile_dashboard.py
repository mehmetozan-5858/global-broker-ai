"""Guardrails for mobile CEO panel deployment without external network calls."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class MobileDashboardTests(unittest.TestCase):
    def test_dashboard_has_shadow_mode_and_no_contact_actions(self):
        script = (ROOT / "web" / "ceo-dashboard.js").read_text(encoding="utf-8")
        self.assertIn("Gölge Mod", script)
        self.assertIn("ready_for_external_contact", (ROOT / "src" / "sales_pack.py").read_text(encoding="utf-8"))
        self.assertNotIn("fetch(", script)
        self.assertNotIn("XMLHttpRequest", script)

    def test_mobile_deploy_loads_script(self):
        workflow = (ROOT / ".github" / "workflows" / "deploy-mobile.yml").read_text(encoding="utf-8")
        self.assertIn("ceo-dashboard.js", workflow)
        self.assertIn("cp -r web/* public/", workflow)

    def test_private_ceo_report_not_deployed_or_committed(self):
        deploy = (ROOT / ".github" / "workflows" / "deploy-mobile.yml").read_text(encoding="utf-8")
        scan = (ROOT / ".github" / "workflows" / "shadow-scan.yml").read_text(encoding="utf-8")
        self.assertNotIn("latest-ceo-report.json", deploy)
        self.assertNotIn("git add data/latest-ceo-report.json", scan)
        self.assertNotIn("git add data/latest-opportunities.json data/latest-ceo-report.json", scan)

if __name__ == "__main__":
    unittest.main()
