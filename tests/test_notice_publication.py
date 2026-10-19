import json
import os
import re
import tempfile
import textwrap
import unittest
from pathlib import Path

from src.public_opportunity_projection import project_public_opportunity

ROOT=Path(__file__).resolve().parents[1]

class NoticePublicationTests(unittest.TestCase):
    def test_pipeline_keeps_only_approved_budget_and_removes_private_lot_documents(self):
        workflow=(ROOT/'.github/workflows/shadow-scan.yml').read_text()
        section=workflow.split('- name: Build public-safe masked feed',1)[1]
        match=re.search(r"python - <<'PY'\n(.*?)\n          PY",section,re.S)
        code=textwrap.dedent(match.group(1))
        row={'estimated_value':'34000','budget_currency':'EUR','ted_lot_count':2,'ted_lot_selection_required':False,
             'ted_lots':[{'description':'PRIVATE LOT CONTENT'}],
             'structured_source_evidence':{'estimated_value':{'value':'34000','currency':'EUR','inferred':False,
                'source_path':'procurementproject/requestedtendertotal/estimatedoverallcontractamount','source_url':'https://private.example/doc'}}}
        with tempfile.TemporaryDirectory() as folder:
            previous=os.getcwd()
            try:
                os.chdir(folder);Path('data').mkdir()
                Path('data/latest-opportunities.private.json').write_text(json.dumps({'opportunities':[row]}))
                exec(compile(code,'public-publication-step','exec'),{})
                output=Path('data/latest-opportunities.json').read_text()
            finally:
                os.chdir(previous)
        self.assertNotIn('PRIVATE LOT CONTENT',output)
        self.assertNotIn('https://private.example',output)
        self.assertNotIn('structured_source_evidence',output)
        self.assertNotIn('ted_lots',output)
        safe=json.loads(output)['opportunities'][0]
        public=project_public_opportunity(safe)
        self.assertEqual(public['estimated_budget'],'34000')
        self.assertEqual(public['budget_currency'],'EUR')
        self.assertEqual(public['lot_count'],2)
        self.assertFalse(public['lot_selection_required'])
