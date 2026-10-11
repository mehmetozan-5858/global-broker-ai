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
        self.assertIn("En az 4 alan", portal)
        self.assertIn("coverage(b)-coverage(a)", portal)
        self.assertIn("Ürün ara", portal)
        self.assertIn("maskedBuyer", portal)
        self.assertIn("/api/introduction", portal)
        self.assertIn("kontrollü tanıştırma", portal)
        self.assertIn("Alıcı kimliği kontrollü tanıştırma ile paylaşılır", portal)
        self.assertNotIn("/api/contact_unlock", portal)
        self.assertNotIn("Doğrulanmış alıcı", portal)
        self.assertNotIn('product(o)+" "+buyer(o)', portal)

    def test_missing_values_are_still_explicit(self):
        portal = (ROOT / "web/customer-portal.js").read_text(encoding="utf-8")
        self.assertIn("Ülke bilgisi kaynakta henüz netleşmedi", portal)
        self.assertIn("Miktar kaynakta belirtilmemiş", portal)
        self.assertIn("Son tarih kaynakta belirtilmemiş", portal)
        self.assertIn("Teslim / Incoterm bilgisi belirtilmemiş", portal)
        self.assertIn("Doğrulama kategorisi belirtilmemiş", portal)
        self.assertNotIn("Doğrulanmış alıcı", portal)


if __name__ == "__main__":
    unittest.main()
