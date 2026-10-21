import io
import unittest
import zipfile
from unittest.mock import patch

from src import document_parser, document_links, ted_xml_parser
from src.specification import analyze_opportunity


class AttachmentSelectionTests(unittest.TestCase):
    def test_late_technical_html_attachment_survives_three_link_budget(self):
        body = ('<html><p>' + 'Source context. ' * 20 + '</p>'
                '<a href="/privacy.pdf">Privacy policy</a>'
                '<a href="/guide.pdf">Portal guide</a>'
                '<a href="/rules.pdf">General rules</a>'
                '<a href="/download?filename=annex.pdf">Technical <b>specification</b></a></html>')
        _, links = document_parser._parse_html_page(body.encode(), 'https://example.test/notice')
        self.assertEqual(len(links), 3)
        self.assertEqual(links[0], 'https://example.test/download?filename=annex.pdf')
        self.assertNotIn('https://example.test/privacy.pdf', links)

    def test_late_xml_specification_is_selected_before_generic_documents(self):
        xml = ('<notice><description>' + 'Official source context. ' * 12 + '</description>'
               + ''.join(f'<a href="https://example.test/general{i}.pdf">General</a>' for i in range(3))
               + '<a href="https://example.test/download?filename=spec.docx">Technical specification</a></notice>')
        _, links = ted_xml_parser.parse_ted_xml(xml.encode(), 'https://ted.europa.eu/en/notice/1-2026/xml')
        self.assertEqual(len(links), 3)
        self.assertEqual(links[0], 'https://example.test/download?filename=spec.docx')

    def test_duplicate_link_retains_strongest_label_and_stable_ties(self):
        candidates = [('https://example.test/a.pdf', 'Guide'), ('https://example.test/b.pdf', 'General'),
                      ('https://example.test/a.pdf', 'Technical specification'), ('https://example.test/c.pdf', 'General')]
        self.assertEqual(document_links.select(candidates, 3), [url for url, _ in candidates[:2]] + ['https://example.test/c.pdf'])

    def test_only_explicit_basename_query_parameters_are_attachment_hints(self):
        for url in ['https://example.test/get?filename=spec.pdf', 'https://example.test/get?file_name=spec.docx',
                    'https://example.test/get?file=annex.txt', 'https://example.test/spec%2Epdf']:
            self.assertTrue(document_links.is_attachment_url(url), url)
        for url in ['https://example.test/get?redirect=https://other.test/spec.pdf',
                    'https://example.test/get?file=https%3A%2F%2Fother.test%2Fspec.pdf',
                    'https://user:pass@example.test/spec.pdf', 'javascript:spec.pdf']:
            self.assertFalse(document_links.is_attachment_url(url), url)

    def test_query_named_docx_is_parsed_with_binary_content_type(self):
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, 'w') as archive:
            archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>Technical specification</w:t></w:r></w:p></w:document>')
        text, kind = document_parser._parse(raw.getvalue(), 'application/octet-stream', 'https://example.test/download?filename=spec.docx')
        self.assertEqual((text, kind), ('Technical specification', 'docx'))

    def test_query_named_attachment_has_private_parser_provenance(self):
        url = 'https://example.test/download?filename=technical.txt'
        item = {'document_url': url}
        text = 'Technical specification: Quantity: 25 pcs. ISO 9001 certificate required. ' * 4
        with patch.object(document_parser, '_download', return_value=(text.encode(), 'application/octet-stream', url)):
            document_parser.enrich_opportunity(item)
        result = analyze_opportunity(item)["specification_analysis"]
        self.assertEqual(item['document_extraction']['parsed_count'], 1)
        self.assertEqual(item['document_extraction']['source_page_count'], 0)
        self.assertTrue(result['document_parsed'])
        self.assertEqual(result['parsed_document_count'], 1)
        self.assertNotIn('verified_unit_price', item)
        self.assertIsNot(item.get('buyer_verified'), True)

    def test_login_html_is_never_counted_as_a_parsed_attachment(self):
        url = 'https://example.test/download?filename=spec.pdf'
        item = {'document_url': url}
        html = ('<html><body>Login required. ' + 'Technical specification quantity 25. ' * 10 + '</body></html>').encode()
        with patch.object(document_parser, '_download', return_value=(html, 'text/html', url)):
            document_parser.enrich_opportunity(item)
        result = analyze_opportunity(item)["specification_analysis"]
        self.assertEqual(item['document_extraction']['parsed_count'], 0)
        self.assertNotIn('document_extracted_text', item)
        self.assertFalse(result['document_parsed'])
        self.assertEqual(result['unparsed_attachment_count'], 1)

    def test_scripts_cannot_supply_attachment_hints(self):
        _, links = document_parser._parse_html_page(b'<script><a href="/spec.pdf">Technical</a></script><a href="/guide.pdf">Guide</a>', 'https://example.test/notice')
        self.assertEqual(links, ['https://example.test/guide.pdf'])

    def test_malformed_link_does_not_hide_later_valid_attachment(self):
        _, html_links = document_parser._parse_html_page(b'<a href="https://[broken">Broken</a><a href="/spec.pdf">Technical specification</a>', 'https://example.test/notice')
        _, xml_links = ted_xml_parser.parse_ted_xml(b'<notice><a href="https://[broken"/><a href="https://example.test/spec.pdf">Technical specification</a></notice>', 'https://ted.europa.eu/en/notice/1-2026/xml')
        self.assertEqual(html_links, ['https://example.test/spec.pdf'])
        self.assertEqual(xml_links, ['https://example.test/spec.pdf'])
