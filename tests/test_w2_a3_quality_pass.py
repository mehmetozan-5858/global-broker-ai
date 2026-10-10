from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class W2A3QualityPassTests(unittest.TestCase):
    def test_a3_runs_again_after_source_enrichment(self):
        workflow = (ROOT / ".github/workflows/shadow-scan.yml").read_text(encoding="utf-8")
        first = workflow.index("field_evidence_initial")
        parser = workflow.index("document_parser")
        ted = workflow.index("ted_xml_enricher")
        specification = workflow.index("specification 90")
        final = workflow.index("field_evidence_final")
        self.assertLess(first, parser)
        self.assertLess(parser, ted)
        self.assertLess(ted, specification)
        self.assertLess(specification, final)
        self.assertIn('python -m src.field_evidence "$NEXT"', workflow)

    def test_customer_portal_has_quality_filter_and_protected_buyer_identity(self):
        portal = (ROOT / "web/customer-portal.js").read_text(encoding="utf-8")
        self.assertIn('id="cpQuality"', portal)
        self.assertIn("En az 4/6 alan", portal)
        self.assertIn("function buyer(o)", portal)
        self.assertIn("coverage(b)-coverage(a)", portal)
        self.assertIn("Ürün ara", portal)
        self.assertIn("maskedBuyer", portal)
        self.assertIn('field(facts,"Alıcı",maskedBuyer()', portal)
        self.assertNotIn('product(o)+" "+buyer(o)', portal)

    def test_missing_values_are_still_explicit(self):
        portal = (ROOT / "web/customer-portal.js").read_text(encoding="utf-8")
        self.assertIn("Şehir belirtilmemiş", portal)
        self.assertIn("Miktar belirtilmemiş", portal)
        self.assertIn("Son tarih belirtilmemiş", portal)
        self.assertIn("Alıcı belirtilmemiş", portal)


if __name__ == "__main__":
    unittest.main()
