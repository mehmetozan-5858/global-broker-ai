import unittest
from unittest.mock import patch

from src import document_parser, ted_xml_enricher


class TedAttachmentBudgetTests(unittest.TestCase):
    def test_discovered_specification_precedes_full_notice_and_existing_context(self):
        for fallback in (False, True):
            for existing in (False, True):
                with self.subTest(fallback=fallback, existing=existing):
                    url = 'https://ted.europa.eu/en/notice/123-2026/xml'
                    attachment = 'https://example.org/specification.txt'
                    notice = '123-2026\n' + 'Administrative notice context. ' * 2000
                    spec = 'Technical specification: flow 250 litres per minute. ' * 5
                    item = {'source': 'TED', 'source_url': url}
                    if existing:
                        item['document_extracted_text'] = 'Old generic page. ' * 3000
                    def download(target, *args):
                        if target == attachment:
                            return spec.encode(), 'text/plain', target
                        if fallback and target == url:
                            raise ValueError('xml_unavailable')
                        if fallback:
                            body = '<html><p>' + notice + '</p><a href="' + attachment + '">Specification</a></html>'
                            return body.encode(), 'text/html', target
                        return b'<Notice/>', 'application/xml', target
                    with patch.object(document_parser, '_download', side_effect=download), patch.object(
                        ted_xml_enricher, 'parse_ted_xml', return_value=(notice[:40000], [attachment])
                    ):
                        self.assertTrue(ted_xml_enricher.enrich_opportunity(item))
                    text = item['document_extracted_text']
                    self.assertTrue(text.startswith(spec.strip()))
                    self.assertLessEqual(len(text), 40000)
                    self.assertEqual(item['document_extraction']['text_chars'], len(text))
                    self.assertEqual(sum(a.get('source') == 'attachment' and a['status'] == 'parsed'
                                         for a in item['document_extraction']['attempts']), 1)
                    self.assertNotIn('verified_unit_price', item)
                    self.assertIsNot(item.get('buyer_verified'), True)

    def test_failed_attachment_preserves_notice(self):
        item = {'source': 'TED', 'source_url': 'https://ted.europa.eu/en/notice/123-2026/xml'}
        notice = 'Official notice context. ' * 20
        with patch.object(document_parser, '_download', side_effect=[
            (b'<Notice/>', 'application/xml', item['source_url']), ValueError('unavailable')
        ]), patch.object(ted_xml_enricher, 'parse_ted_xml', return_value=(notice, ['https://example.org/spec.pdf'])):
            self.assertTrue(ted_xml_enricher.enrich_opportunity(item))
        self.assertEqual(item['document_extracted_text'], notice)
        self.assertEqual(item['document_extraction']['attempts'][0]['status'], 'failed')
