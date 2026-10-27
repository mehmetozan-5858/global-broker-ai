"""The live release probe must fail on the real portal-only false green."""
import unittest
from unittest.mock import patch
from src.ted_document_probe import probe_rows, main


class DocumentProbeAcceptanceTests(unittest.TestCase):
    def rows(self):
        return [{'publication-number':f'{i}-2026','ted_document_link_count':1} for i in (123,124)]

    def context(self, row):
        row['document_extraction']={'parsed_count':1,'attempts':[
            {'status':'parsed','source':'source_page'}, None]}

    def official(self, row):
        row['document_extraction']['ted_xml_parsed']=True
        return True

    def test_portal_success_does_not_skip_official_reader_or_pass(self):
        with patch('src.ted_document_probe.notice_context',return_value={'call_for_tenders':True}), \
             patch('src.ted_document_probe.document_parser.enrich_opportunity',side_effect=self.context), \
             patch('src.ted_document_probe.enrich_opportunity',return_value=False) as read:
            summary=probe_rows(self.rows())
        self.assertEqual(read.call_count,2)
        self.assertEqual(summary['portal_pages_parsed'],2)
        self.assertEqual(summary['official_notices_parsed'],0)
        self.assertFalse(summary['acceptance_passed'])

    def test_all_official_notices_required(self):
        with patch('src.ted_document_probe.notice_context',return_value={'call_for_tenders':True}), \
             patch('src.ted_document_probe.document_parser.enrich_opportunity',side_effect=self.context), \
             patch('src.ted_document_probe.enrich_opportunity',side_effect=self.official):
            summary=probe_rows(self.rows())
        self.assertTrue(summary['acceptance_passed'])
        self.assertEqual(summary['official_notices_parsed'],2)

    def test_cli_returns_failure_for_missing_documents(self):
        with patch('src.ted_document_probe.ted_search',return_value={'notices':[]}), \
             patch('src.ted_document_probe.probe_rows',return_value={'acceptance_passed':False}), \
             patch('builtins.print'):
            with self.assertRaises(SystemExit):main()

    def test_no_candidates_is_not_success(self):
        with self.assertRaises(RuntimeError):probe_rows([])
