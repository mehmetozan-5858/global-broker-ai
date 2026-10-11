from pathlib import Path
import unittest


class CustomerPortalPublicFeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = Path('web/customer-portal.js').read_text(encoding='utf-8')

    def test_uses_allowlisted_public_fields(self):
        for token in ('goods_status', 'approx_quantity', 'source_backed_fields', 'source_field_total'):
            self.assertIn(token, self.text)

    def test_does_not_claim_buyer_is_verified(self):
        self.assertNotIn('Doğrulanmış alıcı', self.text)
        self.assertIn('Alıcı kimliği kontrollü tanıştırma ile paylaşılır', self.text)

    def test_missing_values_are_customer_safe(self):
        self.assertIn('Miktar kaynakta belirtilmemiş', self.text)
        self.assertIn('Teslim / Incoterm bilgisi belirtilmemiş', self.text)
        self.assertIn('Eksik alanlar tahmin edilmez', self.text)

    def test_introduction_route_remains_controlled(self):
        self.assertIn("fetch('/api/introduction'", self.text)
        self.assertNotIn('contact-unlock', self.text)


if __name__ == '__main__':
    unittest.main()
