import io
import unittest
import zipfile
from unittest.mock import patch

from src import document_parser, document_links, ted_xml_parser
from src.specification import analyze_opportunity


class AttachmentSelectionTests(unittest.TestCase):
    def test_multilingual_technical_annex_beats_generic_three_document_budget(self):
        labels = (
            "Pliego de prescripciones técnicas",
            "Memorial descritivo",
            "Termo de referência",
            "Technische specificaties",
            "Caiet de sarcini",
        )
        for label in labels:
            with self.subTest(label=label):
                html = ('<html><p>' + 'Official notice. ' * 20 + '</p>'
                        + ''.join(f'<a href="/general{i}.pdf">Generic form</a>' for i in range(3))
                        + '<a href="/critical.pdf">' + label + '</a></html>')
                _, selected = document_parser._parse_html_page(
                    html.encode("utf-8"), "https://example.test/notice"
                )
                self.assertEqual(selected[0], "https://example.test/critical.pdf")
                self.assertEqual(len(selected), 3)

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

    def test_discovered_technical_label_precedes_full_direct_or_linked_document(self):
        for linked in (False, True):
            with self.subTest(linked=linked):
                generic = 'https://example.test/general.txt'
                notice = 'https://example.test/notice'
                annex = 'https://example.test/attachment.txt'
                spec = 'Technical requirements: flow 250 litres per minute. ' * 5
                item = {'document_url': notice, 'official_links': [generic]}
                if linked:
                    item = {'document_url': generic, 'official_links': [notice]}
                    # The document is served from a URL without an extension.
                    generic = 'https://example.test/download'
                    item['document_url'] = generic
                def download(url, *args):
                    if url == generic:
                        return ('General administrative content. ' * 2000).encode(), ('application/pdf' if linked else 'text/plain'), url
                    if url == annex:
                        return spec.encode(), 'text/plain', url
                    return ('<p>' + 'Notice context. ' * 20 + '</p><a href="' + annex + '">Technical specification</a>').encode(), 'text/html', url
                # A linked binary document occupies the single page slot; allow
                # the separate notice page in this fixture to exercise both.
                with patch.object(document_parser, '_download', side_effect=download), patch.object(
                    document_parser, '_parse_pdf', return_value='General administrative content. ' * 2000
                ), patch.object(document_parser, 'MAX_SOURCE_PAGES_PER_OPPORTUNITY', 2):
                    document_parser.enrich_opportunity(item)
                text = item['document_extracted_text']
                self.assertTrue(text.startswith(spec.strip()))
                self.assertEqual(len(text), 40000)
                self.assertEqual(item['document_extraction']['text_chars'], len(text))
                attempt = next(a for a in item['document_extraction']['attempts'] if a['url'] == annex)
                self.assertEqual(attempt['discovered_from'], notice)
                self.assertNotIn('verified_unit_price', item)

    def test_direct_attachment_uses_discovered_label_without_second_download(self):
        first = 'https://example.test/a.txt'
        second = 'https://example.test/b.txt'
        notice = 'https://example.test/notice'
        item = {'document_url': notice, 'official_links': [first, second]}
        spec = 'Exact technical requirements from second document. ' * 5
        def download(url, *args):
            if url == first:
                return ('Generic administrative content. ' * 2000).encode(), 'text/plain', url
            if url == second:
                return spec.encode(), 'text/plain', url
            return ('<p>' + 'Notice context. ' * 20 + '</p><a href="' + second + '">Technical specification</a>').encode(), 'text/html', url
        with patch.object(document_parser, '_download', side_effect=download) as reader:
            document_parser.enrich_opportunity(item)
        self.assertTrue(item['document_extracted_text'].startswith(spec.strip()))
        self.assertEqual(sum(call.args[0] == second for call in reader.call_args_list), 1)
        self.assertEqual(item['document_extraction']['discovered_attachment_count'], 0)

    def test_failed_discovered_specification_retains_current_generic_text(self):
        generic = 'https://example.test/general.txt'
        notice = 'https://example.test/notice'
        item = {'document_url': notice, 'official_links': [generic]}
        text = 'Current administrative document. ' * 2000
        def download(url, *args):
            if url == generic:
                return text.encode(), 'text/plain', url
            if url == notice:
                return ('<p>' + 'Notice context. ' * 20 + '</p><a href="/spec.txt">Technical specification</a>').encode(), 'text/html', url
            raise TimeoutError('source timeout')
        with patch.object(document_parser, '_download', side_effect=download):
            document_parser.enrich_opportunity(item)
        self.assertEqual(item['document_extracted_text'], text[:40000])
        self.assertEqual(item['document_extraction']['attempts'][-1]['status'], 'failed')

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
