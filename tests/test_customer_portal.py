import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class CustomerPortalTests(unittest.TestCase):
    def test_portal_filters_to_physical_goods_and_has_core_filters(self):
        js=(ROOT/"web/customer-portal.js").read_text(encoding="utf-8")
        self.assertIn("goods_candidate",js)
        self.assertIn('id="cpQuery"',js)
        self.assertIn('id="cpCountry"',js)
        self.assertIn('id="cpCity"',js)
        self.assertIn('field_evidence',js)
        self.assertIn('Miktar belirtilmemiş',js)
        self.assertIn('Şehir belirtilmemiş',js)
        self.assertIn('Kaynak alanı:',js)
        self.assertIn('/api/contact_unlock',js)
        self.assertIn('opportunity_id',js)

    def test_portal_does_not_invent_missing_values(self):
        js=(ROOT/"web/customer-portal.js").read_text(encoding="utf-8")
        self.assertNotIn('Ülke başlıktan tahmin',js)
        self.assertNotIn('Math.random',js)
        self.assertNotIn('fake',js.lower())

    def test_deploy_injects_customer_portal_and_ci_checks_syntax(self):
        deploy=(ROOT/".github/workflows/deploy-mobile.yml").read_text(encoding="utf-8")
        ci=(ROOT/".github/workflows/verified-brokerage-ci.yml").read_text(encoding="utf-8")
        self.assertIn('customer-portal.js',deploy)
        self.assertIn('node --check web/customer-portal.js',ci)

    def test_a3_gate_runs_before_enrichment(self):
        workflow=(ROOT/".github/workflows/shadow-scan.yml").read_text(encoding="utf-8")
        evidence=workflow.index('scan_step field_evidence')
        enrichment=workflow.index('scan_step enrichment')
        self.assertLess(evidence,enrichment)
        self.assertIn('A3 field evidence missing from live payload',workflow)


if __name__=="__main__":
    unittest.main()
