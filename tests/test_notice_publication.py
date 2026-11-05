import json
import tempfile
import subprocess
import sys
import unittest
from pathlib import Path

from src.public_opportunity_projection import project_public_opportunity
from src.launch_readiness_report import build as launch_report

ROOT=Path(__file__).resolve().parents[1]

class NoticePublicationTests(unittest.TestCase):
    def test_pipeline_keeps_only_approved_budget_and_removes_private_lot_documents(self):
        workflow=(ROOT/'.github/workflows/shadow-scan.yml').read_text()
        self.assertIn('python -m src.public_opportunity_projection data/latest-opportunities.private.json data/latest-opportunities.json', workflow)
        row={'export_goods_review':{'status':'goods_candidate'},'estimated_value':'34000','budget_currency':'EUR','ted_lot_count':2,'ted_lot_selection_required':False,
             'ted_lots':[{'description':'PRIVATE LOT CONTENT'},{'description':'PRIVATE SECOND LOT'}],
             'structured_source_evidence':{'estimated_value':{'value':'34000','currency':'EUR','inferred':False,
                'source_path':'procurementproject/requestedtendertotal/estimatedoverallcontractamount','source_url':'https://private.example/doc'}}}
        payload={'opportunities':[row],'launch_gate':{'checks':{'payment_provider_tested':False}}}
        launch_report(payload)
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'private.json'
            destination=Path(folder)/'public.json'
            source.write_text(json.dumps(payload))
            subprocess.run([sys.executable, '-m', 'src.public_opportunity_projection', str(source), str(destination)], cwd=ROOT, check=True, capture_output=True)
            output=destination.read_text()
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
        # Internal operational summaries stay private; projection must not
        # turn missing commercial approvals into public readiness claims.
        self.assertNotIn('launch_readiness_report', json.loads(output))
        groups=payload['launch_readiness_report']['categories']
        self.assertIn('commercial_launch_conditions',groups)
        self.assertIn('payment_provider_tested',groups['commercial_launch_conditions']['pending'])
