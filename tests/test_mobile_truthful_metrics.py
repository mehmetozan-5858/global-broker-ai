import unittest
from pathlib import Path

APP = (Path(__file__).resolve().parents[1] / "web" / "app.html")

class TruthfulMobileMetricsTests(unittest.TestCase):
    def test_unknown_agent_counts_not_equal_total_leads(self):
        s = APP.read_text(encoding="utf-8")
        self.assertIn("if(k==='ceo'||k==='opps'||k==='buyers')return a.length;return '—'", s)
        self.assertNotIn("if(k==='secure')return a.filter(function(o){return completeness(o)>=70}).length;return a.length", s)

    def test_completeness_not_mislabeled_as_verified_supplier(self):
        s = APP.read_text(encoding="utf-8")
        self.assertIn("Dosyası %70+", s)
        self.assertNotIn("Tedarikçiye Hazır", s)
        self.assertNotIn("Tedarikçi aramaya hazır", s)

    def test_verified_buyer_label_is_unambiguous(self):
        s = APP.read_text(encoding="utf-8")
        self.assertIn("Alıcı kimliği doğrulanmış", s)
        self.assertNotIn("Kaynakta alıcı mevcut", s)

if __name__ == "__main__":
    unittest.main()
