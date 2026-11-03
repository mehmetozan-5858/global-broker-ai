import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CustomerTabReadinessTests(unittest.TestCase):
    def test_both_customer_entrypoints_load_module(self):
        shell = (ROOT / "web/customer-shell.html").read_text(encoding="utf-8")
        deployment = (ROOT / ".github/workflows/deploy-mobile.yml").read_text(encoding="utf-8")
        self.assertIn("addScript(d,'/web/customer-tab-readiness.js')", shell)
        self.assertIn('<script src="customer-tab-readiness.js" defer></script>', deployment)

    def test_all_customer_navigation_tabs_have_help(self):
        source = (ROOT / "web/customer-tab-readiness.js").read_text(encoding="utf-8")
        for key in ("agents", "opps", "report", "settings", "markets", "buyers", "suppliers", "pricing", "logistics", "trade", "risk", "communication", "negotiation", "contract", "commission", "payments"):
            self.assertIn(key + ":{", source)
        self.assertIn("typeof window.openCard==='function'", source)
        self.assertIn("if(!host)return", source)
        self.assertIn("if(old)old.remove()", source)

    def test_no_unverified_commercial_metrics_or_privileged_apis(self):
        source = (ROOT / "web/customer-tab-readiness.js").read_text(encoding="utf-8")
        for forbidden in (
            "admin_opportunities", "user_roles", "commission_ledger",
            "fetch(", "XMLHttpRequest", "localStorage", "innerHTML",
            "doğrulanmış alıcılarımız", "garantili kazanç",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("Bilgilendirme:", source)
        self.assertIn("gerçek fırsat", source)


if __name__ == "__main__":
    unittest.main()
