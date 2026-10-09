import unittest
from pathlib import Path

JS=(Path(__file__).resolve().parents[1]/"web"/"country-markets.js").read_text(encoding="utf-8")

class CountryMarketTests(unittest.TestCase):
    def test_country_codes_and_unknowns(self):
        for code in ("BGR","CHE","CZE","DEU","country_code","resolvedCountry(o)"):
            self.assertIn(code,JS)
        self.assertIn("Ülkesi tespit edilemeyenler",JS)
        self.assertIn("Ülke başlıktan tahmin edildi",JS)
    def test_gulf_sources_are_explicitly_not_live_feeds(self):
        for domain in ("tenders.etimad.sa","mof.gov.ae","monaqasat.mof.gov.qa"):
            self.assertIn(domain,JS)
        self.assertIn("henüz otomatik talep aktarılmıyor",JS)

if __name__=="__main__":
    unittest.main()
