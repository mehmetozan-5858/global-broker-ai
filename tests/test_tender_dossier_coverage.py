import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class TenderDossierCoverageTests(unittest.TestCase):
    def test_missing_field_checklist_and_coverage(self):
        js=(ROOT/"web"/"tender-dossier.js").read_text(encoding="utf-8")
        self.assertIn("Eksik / teyit bekleyen alanlar",js)
        self.assertIn("temel alan için bilgi veya kaynak bulgusu mevcut",js)
        self.assertIn("parts.indexOf(x)===i",js)
        self.assertIn("extraction.parsed_count",js)

if __name__=="__main__":
    unittest.main()
