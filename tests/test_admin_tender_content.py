import unittest
from pathlib import Path

HTML=(Path(__file__).resolve().parents[1]/"web"/"admin.html").read_text(encoding="utf-8")

class AdminTenderContentTests(unittest.TestCase):
    def test_direct_content_instead_of_raw_links(self):
        self.assertIn("body=adminTenderContent(o)",HTML)
        self.assertIn("Teknik şartlar",HTML)
        self.assertIn("Katılım / yeterlilik koşulları",HTML)
        self.assertIn("Başvuru belgeleri, teminat ve ödeme",HTML)
        self.assertIn("Resmî bağlantılar (isteğe bağlı)",HTML)
    def test_no_unverified_readiness_claim(self):
        self.assertNotIn("✅ Yönetici ön incelemesine hazır",HTML)
        self.assertIn("şartname teyidi gerekli",HTML)
    def test_links_are_capped(self):
        self.assertIn("}).slice(0,3)",HTML)

if __name__=="__main__":
    unittest.main()
