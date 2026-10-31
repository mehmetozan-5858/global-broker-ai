import contextlib
import io
import json
import unittest
from unittest.mock import patch
from src import ted_document_probe as probe

class TedDocumentProbeExitTest(unittest.TestCase):
    def run_probe(self, parsed):
        def documents(row):
            row['document_extraction']={'parsed_count':int(parsed)}
        output=io.StringIO()
        with patch.object(probe,'ted_search',return_value={'notices':[{'id':'fixture'}]}), \
             patch.object(probe,'apply_search_fields',side_effect=lambda row:row), \
             patch.object(probe,'notice_context',return_value={'call_for_tenders':True}), \
             patch.object(probe.document_parser,'enrich_opportunity',side_effect=documents), \
             patch.object(probe,'enrich_opportunity',return_value=False),contextlib.redirect_stdout(output):
            code=probe.main()
        return code,json.loads(output.getvalue().split(' ',1)[1])
    def test_zero_documents_fails_even_when_probe_itself_completes(self):
        code,summary=self.run_probe(False)
        self.assertEqual(code,1)
        self.assertEqual(summary['minimum_document_gate'],'failed')
        self.assertEqual(summary['parsed'],0)
        self.assertFalse(summary['full_attachment_acceptance'])
    def test_one_read_document_only_passes_minimum_gate(self):
        code,summary=self.run_probe(True)
        self.assertEqual(code,0)
        self.assertEqual(summary['minimum_document_gate'],'passed')
        self.assertFalse(summary['full_attachment_acceptance'])
        self.assertEqual(summary['xml_parsed'],0)
    def test_no_candidate_does_not_report_success(self):
        with patch.object(probe,'ted_search',return_value={'notices':[]}):
            with self.assertRaises(RuntimeError):probe.main()
