import unittest

from src.source_contact_probe import PageParser, _best_contact, _same_origin


class SourceContactProbeTests(unittest.TestCase):
    def test_mailto_and_tel_are_detected(self):
        parser = PageParser()
        parser.feed('<html><body><a href="mailto:procurement@example.gov">Procurement</a><a href="tel:+1 202 555 0188">Phone</a></body></html>')
        email, phone, _ = _best_contact(parser)
        self.assertEqual(email, 'procurement@example.gov')
        self.assertEqual(phone, '+1 202 555 0188')

    def test_contextual_visible_email_is_detected(self):
        parser = PageParser()
        parser.feed('<p>Tender procurement contact: bids@example.gov</p>')
        email, phone, _ = _best_contact(parser)
        self.assertEqual(email, 'bids@example.gov')
        self.assertEqual(phone, '')

    def test_same_origin_blocks_cross_domain_hops(self):
        self.assertTrue(_same_origin('https://buyer.gov/a', 'https://buyer.gov/contact'))
        self.assertFalse(_same_origin('https://buyer.gov/a', 'https://other.gov/contact'))
        self.assertFalse(_same_origin('https://buyer.gov/a', 'http://buyer.gov/contact'))


if __name__ == '__main__':
    unittest.main()
