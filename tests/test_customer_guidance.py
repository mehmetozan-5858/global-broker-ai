import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class CustomerGuidanceTests(unittest.TestCase):
    def test_static_customer_uses_controlled_introduction_bridge(self):
        deploy=(ROOT/'.github/workflows/deploy-mobile.yml').read_text(encoding='utf-8')
        shell=(ROOT/'web/customer-shell.html').read_text(encoding='utf-8')
        bridge=(ROOT/'web/introduction-bridge.js').read_text(encoding='utf-8')
        self.assertIn('introduction-bridge.js',deploy)
        self.assertIn('introduction-bridge.js',shell)
        self.assertNotIn('<script src="contact-unlock-bridge.js"',deploy)
        self.assertNotIn("addScript(d,'/web/contact-unlock-bridge.js')",shell)
        self.assertIn('request_introduction',bridge)
        self.assertIn('broker-introduction-verify',bridge)
        self.assertNotIn('broker-contact-unlock',bridge)

    def test_customer_sections_have_plain_language_guidance(self):
        js=(ROOT/'web/customer-guidance.js').read_text(encoding='utf-8')
        for key in ('opps','buyers','suppliers','pricing','logistics','risk','contract','commission','payments','settings'):
            self.assertIn(key+':[',js)
        self.assertIn('BU BÖLÜM NE İŞE YARAR?',js)
        self.assertIn('Ne yapmalısınız?',js)
        self.assertIn('Alıcı kimliği kontrollü tanıştırma ile paylaşılır',js)

    def test_public_preview_uses_neutral_buyer_label(self):
        deploy=(ROOT/'.github/workflows/deploy-mobile.yml').read_text(encoding='utf-8')
        self.assertIn("Alıcı kimliği kontrollü tanıştırma ile paylaşılır",deploy)
        self.assertNotIn("Doğrulanmış alıcı — giriş yaparak erişim kurallarını inceleyin",deploy)


if __name__=='__main__':
    unittest.main()
