import unittest
from unittest.mock import patch

from src import document_parser, document_links
from src.source_navigation import document_indexes
from src.specification import analyze_opportunity


class DocumentIndexNavigationTests(unittest.TestCase):
    def test_only_explicit_same_origin_parent_links_are_followed(self):
        base = 'https://example.test/tender/200'
        links = [
            {'href': '/tender/199', 'label': "Vai all’elenco lotti"},
            {'href': '/tender/198', 'label': 'Main tender'},
            {'href': '/tender/197', 'label': 'Other procurement'},
            {'href': 'https://other.test/tender/199', 'label': 'All lots'},
            {'href': 'https://user:secret@example.test/tender/199', 'label': 'All lots'},
            {'href': '/login', 'label': 'All lots'},
            {'href': '/tender/199?delete=1', 'label': 'All lots'},
            {'href': '/tender/200#parent', 'label': 'All lots'},
            {'href': '/tender/200', 'label': 'All lots'},
            {'href': 'https://[broken', 'label': 'All lots'},
        ]
        self.assertEqual(document_indexes(links, base), ['https://example.test/tender/199', 'https://example.test/tender/198'])

    def test_parent_technical_docs_outrank_child_forms_with_correct_provenance(self):
        child = 'https://example.test/tender/200'
        parent = 'https://example.test/tender/199'
        first = b'<p>' + b'Child notice context. ' * 15 + b'</p><a href="/form.txt">Application form</a><a href="/tender/199">Vai all\'elenco lotti</a>'
        parent_html = (b'<p>Other lot Quantity: 999 buses.</p>'
                       b'<a href="/privacy.txt">Privacy</a><a href="/contract.txt">Contract</a>'
                       b'<a href="/Allegato+1+Capitolato_Tecnico.pdf">Capitolato tecnico</a>'
                       b'<a href="/Allegato+4+Criteri+valutazione.pdf">Criteri di valutazione</a>'
                       b'<a href="/tender/198">Main tender</a>')
        spec = 'Technical specification: CNG urban buses, minimum 27 passengers. ' * 5
        def download(url, *args):
            if url == child: return first, 'text/html', url
            if url == parent: return parent_html, 'text/html', url
            if url.endswith('.pdf'): return b'%PDF-test', 'application/pdf', url
            return ('Application form. ' * 3000).encode(), 'text/plain', url
        item = {'document_url': child, 'source_lot_selection_required': True}
        with patch.object(document_parser, '_download', side_effect=download) as reader, patch.object(document_parser, '_parse_pdf', return_value=spec):
            document_parser.enrich_opportunity(item)
        info = item['document_extraction']
        self.assertEqual(info['document_index_count'], 1)
        urls = [call.args[0] for call in reader.call_args_list]
        self.assertNotIn('https://example.test/tender/198', urls)
        self.assertNotIn('https://example.test/privacy.txt', urls)
        self.assertEqual(sum(u.endswith(('.pdf', '.txt')) for u in urls), 3)
        self.assertTrue(item['document_extracted_text'].startswith(spec.strip()))
        self.assertNotIn('999 buses', item['document_extracted_text'])
        self.assertLessEqual(len(item['document_extracted_text']), 40000)
        docs = [a for a in info['attempts'] if a.get('source') == 'attachment' and a.get('kind') == 'pdf']
        self.assertEqual(len(docs), 2)
        self.assertTrue(all(a['discovered_from'] == parent for a in docs))
        self.assertFalse(analyze_opportunity(item)['specification_analysis']['supplier_sourcing_ready'])
        self.assertIs(item['source_lot_selection_required'], True)
        self.assertNotIn('verified_unit_price', item)
        self.assertNotIn('buyer_verified', item)

    def test_technical_annex_precedes_earlier_evaluation_criteria(self):
        criteria = 'https://example.test/Allegato+4+Criteri+valutazione.pdf'
        technical = 'https://example.test/Allegato+1+Capitolato_Tecnico.pdf'
        self.assertEqual(document_links.select([(criteria, 'Criteri'), (technical, 'Capitolato tecnico')], 3), [technical, criteria])

    def test_one_index_attempt_limit_even_on_failure(self):
        child = 'https://example.test/tender/200'
        item = {'document_url': child}
        html = b'<p>' + b'Current source context. ' * 20 + b'</p><a href="/tender/199">All lots</a><a href="/tender/198">Main tender</a>'
        with patch.object(document_parser, '_download', side_effect=[(html, 'text/html', child), TimeoutError('timeout')]) as reader:
            document_parser.enrich_opportunity(item)
        self.assertEqual(reader.call_count, 2)
        self.assertEqual(item['document_extraction']['document_index_count'], 1)

    def test_failed_index_does_not_erase_current_child_text(self):
        child = 'https://example.test/tender/200'
        body = b'<p>' + b'Current lot context. ' * 20 + b'</p><a href="/tender/199">All lots</a>'
        item = {'document_url': child}
        with patch.object(document_parser, '_download', side_effect=[(body, 'text/html', child), TimeoutError('timeout')]):
            document_parser.enrich_opportunity(item)
        self.assertIn('Current lot context', item['document_extracted_text'])
        self.assertEqual(item['document_extraction']['attempts'][-1]['status'], 'failed')
        self.assertEqual(item['document_extraction']['document_index_count'], 1)

    def test_cross_origin_redirect_cannot_supply_parent_evidence(self):
        child = 'https://example.test/tender/200'
        body = b'<p>' + b'Child context. ' * 20 + b'</p><a href="/tender/199">All lots</a>'
        item = {'document_url': child}
        with patch.object(document_parser, '_download', side_effect=[(body, 'text/html', child), (b'<a href="/spec.pdf">Technical</a>', 'text/html', 'https://other.test/tender/199')]) as reader:
            document_parser.enrich_opportunity(item)
        self.assertEqual(reader.call_count, 2)
        self.assertIn('document_index_origin_changed', item['document_extraction']['attempts'][-1]['error'])
        self.assertEqual(item['document_extraction']['discovered_attachment_count'], 0)

    def test_index_page_alone_is_not_parsed_technical_document(self):
        child = 'https://example.test/tender/200'
        item = {'document_url': child}
        with patch.object(document_parser, '_download', side_effect=[
            (b'<p>' + b'Generic child context. ' * 20 + b'</p><a href="/tender/199">All lots</a>', 'text/html', child),
            (b'<p>Quantity: 999 buses. Technical specification. ISO 9001</p>', 'text/html', 'https://example.test/tender/199')]):
            document_parser.enrich_opportunity(item)
        self.assertNotIn('999 buses', item['document_extracted_text'])
        self.assertFalse(analyze_opportunity(item)['specification_analysis']['document_parsed'])

    def test_index_success_without_source_text_does_not_inflate_parsed_count(self):
        child = 'https://example.test/tender/200'
        item = {'document_url': child}
        with patch.object(document_parser, '_download', side_effect=[
            (b'<a href="/tender/199">All lots</a>', 'text/html', child),
            (b'<p>Other lot Quantity: 999 buses</p>', 'text/html', 'https://example.test/tender/199')]):
            document_parser.enrich_opportunity(item)
        self.assertNotIn('document_extracted_text', item)
        self.assertEqual(item['document_extraction']['parsed_count'], 0)
        self.assertEqual(item['document_extraction']['status'], 'attempted_no_text')

    def test_existing_direct_document_is_not_downloaded_twice(self):
        child = 'https://example.test/tender/200'
        spec = 'https://example.test/spec.txt'
        item = {'document_url': child, 'official_links': [spec]}
        text = 'Technical specification flow 250 litres per minute. ' * 6
        def download(url, *args):
            if url == spec: return text.encode(), 'text/plain', url
            if url == child: return b'<p>' + b'Child context. ' * 20 + b'</p><a href="/tender/199">All lots</a>', 'text/html', url
            return b'<a href="/spec.txt">Technical specification</a>', 'text/html', url
        with patch.object(document_parser, '_download', side_effect=download) as reader:
            document_parser.enrich_opportunity(item)
        self.assertEqual(sum(c.args[0] == spec for c in reader.call_args_list), 1)
        self.assertTrue(item['document_extracted_text'].startswith(text.strip()))
