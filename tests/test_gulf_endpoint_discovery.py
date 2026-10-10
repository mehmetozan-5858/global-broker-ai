import unittest

from src.gulf_endpoint_discovery import endpoint_hints, script_urls


class GulfEndpointDiscoveryTests(unittest.TestCase):
    def test_script_urls_keep_same_origin_only(self):
        markup = '<script src="/js/app.js"></script><script src="https://evil.example/x.js"></script>'
        self.assertEqual(
            script_urls(markup, 'https://tenders.etimad.sa/Tender/AllTendersForVisitor'),
            ['https://tenders.etimad.sa/js/app.js'],
        )

    def test_endpoint_hints_strip_query_and_reject_cross_origin(self):
        text = '''
        const a="/api/Tender/Search?token=secret";
        const b="https://tenders.etimad.sa/Tender/GetTenders?page=2";
        const c="https://evil.example/api/Tender/Search?token=bad";
        const d="/assets/app.js";
        '''
        hints = endpoint_hints(text, 'https://tenders.etimad.sa/Tender/AllTendersForVisitor')
        self.assertIn('https://tenders.etimad.sa/api/Tender/Search', hints)
        self.assertIn('https://tenders.etimad.sa/Tender/GetTenders', hints)
        self.assertFalse(any('secret' in x or 'evil.example' in x or x.endswith('.js') for x in hints))


if __name__ == '__main__':
    unittest.main()
