import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CustomerTruthLabelTests(unittest.TestCase):
    def test_neutral_buyer_wording_guard_is_deployed(self):
        guard = (ROOT / 'web/customer-truth-label.js').read_text(encoding='utf-8')
        shell = (ROOT / 'web/customer-shell.html').read_text(encoding='utf-8')
        deploy = (ROOT / '.github/workflows/deploy-mobile.yml').read_text(encoding='utf-8')
        safe = 'Alıcı kimliği kontrollü tanıştırma ile paylaşılır'
        self.assertIn(safe, guard)
        self.assertIn('customer-truth-label.js', shell)
        self.assertIn('customer-truth-label.js', deploy)
        self.assertIn(safe, deploy)

    def test_customer_delivery_does_not_present_masked_buyer_as_verified(self):
        deploy = (ROOT / '.github/workflows/deploy-mobile.yml').read_text(encoding='utf-8')
        self.assertNotIn("clean['buyer_display']='Doğrulanmış alıcı", deploy)
        self.assertNotIn('Doğrulanmış alıcı — giriş yaparak erişim kurallarını inceleyin', deploy)


if __name__ == '__main__':
    unittest.main()
