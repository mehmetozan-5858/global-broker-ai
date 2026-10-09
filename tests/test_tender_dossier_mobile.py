import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class TenderDossierMobileTests(unittest.TestCase):
    def test_evidence_sections_and_missing_data_are_explicit(self):
        s = (ROOT / "web/tender-dossier.js").read_text(encoding="utf-8")
        for field in ("eligibility_evidence", "technical_evidence", "quantity_evidence",
                      "delivery_evidence", "award_evidence", "required_documents",
                      "bid_security", "payment_terms", "document_purchase_deadline"):
            self.assertIn(field, s)
        self.assertIn("Kaynakta doğrulanamadı", s)
        self.assertIn("baseCard=function(o)", s)

    def test_mobile_deploy_loads_dossier(self):
        s = (ROOT / ".github/workflows/deploy-mobile.yml").read_text(encoding="utf-8")
        self.assertIn('tender-dossier.js', s)

if __name__ == "__main__":
    unittest.main()
