import json
import unittest
from unittest.mock import patch

from src import document_parser
from src.a5_source_terms import extract
from src.data_completion_queue import build
from src.public_opportunity_projection import project_public_opportunity
from src.specification import analyze_opportunity


class WorldBankNoticeReaderTests(unittest.TestCase):
    identity = 'OP00473154'
    body = '<p>Technical requirements: laboratory equipment with minimum capacity 500 units and ISO 9001 certification.</p><p>Quantity: 25 pcs</p><p>Delivery location: Ankara central warehouse</p><p>Contact: fixture-private@example.invalid</p>'

    def row(self):
        return {'id': self.identity, 'source': 'WORLD_BANK',
                'source_url': 'https://projects.worldbank.org/en/projects-operations/procurement-detail/' + self.identity}

    def response(self, rows=None, final_url=None):
        return (json.dumps({'procnotices': rows if rows is not None else {'1': {'id': self.identity, 'notice_text': self.body}}}).encode(),
                'application/json', final_url or 'https://search.worldbank.org/api/v2/procnotices?qterm=' + self.identity)

    def test_exact_notice_is_read_instead_of_javascript_shell_and_stays_private(self):
        row = self.row()
        with patch.object(document_parser, '_download', return_value=self.response()) as download:
            document_parser.enrich_opportunity(row)
        download.assert_called_once()
        self.assertIn('fl=id%2Cnotice_text', download.call_args.args[0])
        self.assertEqual(row['document_extraction']['parsed_count'], 1)
        extract(row)
        self.assertEqual(row['quantity'], '25 pcs')
        self.assertEqual(row['delivery_location'], 'Ankara central warehouse')
        self.assertEqual(row['a5_source_term_evidence']['quantity']['source_field'], 'document_extracted_text')
        self.assertNotIn('verified_unit_price', row)
        public = json.dumps(project_public_opportunity(row))
        self.assertNotIn('fixture-private', public)
        self.assertNotIn('document_extracted_text', public)
        self.assertNotIn('search.worldbank.org', public)

    def test_other_notice_duplicate_or_missing_body_is_never_used(self):
        for rows in [[{'id': 'OP00000001', 'notice_text': self.body}],
                     [{'id': self.identity, 'notice_text': self.body}] * 2,
                     [{'id': self.identity}], [{'id': self.identity, 'notice_text': '<p>short</p>'}]]:
            with self.subTest(rows=len(rows)):
                attempts, parts = [], []
                with patch.object(document_parser, '_download', return_value=self.response(rows)):
                    self.assertFalse(document_parser._world_bank_notice(self.row(), attempts, parts))
                self.assertEqual(parts, [])
                self.assertEqual(attempts[0]['status'], 'failed')

    def test_bad_ids_and_other_sources_never_query_api(self):
        for change in [{'id': 'OP00473154?x'}, {'source': 'TED'}, {'id': None}]:
            row = self.row(); row.update(change)
            with patch.object(document_parser, '_download') as download:
                self.assertFalse(document_parser._world_bank_notice(row, [], []))
            download.assert_not_called()

    def test_unexpected_api_redirect_is_rejected(self):
        with patch.object(document_parser, '_download', return_value=self.response(final_url='https://example.test/api/v2/procnotices')):
            parts = []
            self.assertFalse(document_parser._world_bank_notice(self.row(), [], parts))
        self.assertEqual(parts, [])

    def test_oversized_notice_is_not_truncated_into_an_apparently_complete_scope(self):
        rows = [{'id': self.identity, 'notice_text': self.body + ('x' * document_parser.MAX_EXTRACTED_CHARS)}]
        with patch.object(document_parser, '_download', return_value=self.response(rows)):
            parts = []
            self.assertFalse(document_parser._world_bank_notice(self.row(), [], parts))
        self.assertEqual(parts, [])

    def test_lot_mentions_keep_text_but_block_flat_quantity_and_supplier_readiness(self):
        row = self.row()
        rows = [{'id': self.identity, 'notice_text': self.body + '<p>Lot 1: laboratory equipment</p><p>Lot 2: furniture</p>'}]
        with patch.object(document_parser, '_download', return_value=self.response(rows)):
            document_parser.enrich_opportunity(row)
        self.assertIn('document_extracted_text', row)
        result = extract(row)
        self.assertTrue(row['source_lot_selection_required'])
        self.assertNotIn('quantity', row)
        self.assertEqual(result['review_required']['quantity'], 'lot_selection_required')
        analyze_opportunity(row)
        self.assertFalse(row['specification_analysis']['supplier_sourcing_ready'])
        self.assertEqual(row['specification_analysis']['status'], 'lot_selection_required')
        build({'opportunities': [row]})
        self.assertIn('lot_selection', row['data_completion']['missing_fields'])

    def test_api_failure_falls_back_to_current_canonical_page(self):
        row = self.row()
        with patch.object(document_parser, '_download', side_effect=[TimeoutError('unavailable'),
                (self.body.encode(), 'text/html', row['source_url'])]) as download:
            document_parser.enrich_opportunity(row)
        self.assertEqual(download.call_count, 2)
        self.assertEqual(row['document_extraction']['parsed_count'], 1)
        self.assertEqual(row['document_extraction']['attempts'][0]['status'], 'failed')
        self.assertEqual(row['document_extraction']['attempts'][1]['status'], 'parsed')
