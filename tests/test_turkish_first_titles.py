import unittest
from pathlib import Path

class TurkishFirstTitlesTests(unittest.TestCase):
    def test_chinese_headline_has_turkish_display(self):
        html=(Path(__file__).resolve().parents[1]/"web"/"app.html").read_text(encoding="utf-8")
        self.assertIn("2026 bireysel personel ekipmanı alımı",html)
        self.assertIn("Türkçe çeviri doğrulaması bekleniyor",html)
        self.assertIn("productDisplay(o)",html)

    def test_original_is_not_falsely_marked_translated(self):
        html=(Path(__file__).resolve().parents[1]/"web"/"app.html").read_text(encoding="utf-8")
        self.assertIn("if(tr&&!/",html)
        self.assertIn("title_original",html)

if __name__=="__main__":
    unittest.main()
