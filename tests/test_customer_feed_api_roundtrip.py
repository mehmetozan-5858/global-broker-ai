import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from api import opportunities
from src.public_opportunity_projection import project_public_feed


class CustomerFeedAPIRoundtripTests(unittest.TestCase):
    def rows(self):
        return [{'id':'fixture-one','product_name':'Industrial pump','country_code':'DE','country_name':'Germany',
                 'source':'WORLD_BANK','quantity':'25 units','buyer_name':'Private Fixture Buyer',
                 'export_goods_review':{'status':'goods_candidate'},'sector_id':'machinery',
                 'source_lot_selection_required':True,
                 'data_completion':{'missing_fields':['lot_selection','quantity_or_budget']},
                 'document_extracted_text':'Private document and fixture@example.invalid',
                 'document_extraction':{'parsed_count':1,'attempts':[{'status':'parsed','format':'world_bank_notice_json'}]}},
                {'id':'fixture-two','product_name':'Auto parts','country_code':'FR','country_name':'France',
                 'source':'Official portal','sector_id':'automotive','export_goods_review':{'status':'goods_candidate'}}]

    def request(self, rows, sectors=None, countries=None, all_sectors=False, active=True, token=True):
        captured = []
        handler = object.__new__(opportunities.handler)
        handler.headers = {'Authorization':'Bearer synthetic-fixture'} if token else {}
        handler._json = lambda status, payload: captured.append((status, payload))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'feed.json'; path.write_text(json.dumps({'opportunities':rows}))
            identity = ({'id':'fixture-user'}, {'active':active,'all_sectors':all_sectors,'plan_id':'fixture'},
                        {'selected_sectors':sectors or [],'selected_countries':countries or []})
            with patch.object(opportunities, '_identity_and_access', return_value=identity), patch.object(opportunities, '_data_path', return_value=path):
                handler.do_GET()
        return captured[0]

    def test_masked_snapshot_reaches_authorized_customer_with_scope_and_privacy(self):
        rows = project_public_feed({'opportunities':self.rows()})['opportunities']
        status, body = self.request(rows, ['machinery'], ['DE'])
        self.assertEqual(status, 200); self.assertEqual(body['count'], 1)
        row = body['opportunities'][0]
        self.assertEqual(row['goods_status'], 'goods_candidate')
        self.assertEqual(row['source_text_status'], 'official_notice_read')
        self.assertTrue(row['lot_selection_required'])
        self.assertNotIn('approx_quantity', row)
        self.assertNotIn('Private Fixture Buyer', json.dumps(body))
        self.assertNotIn('fixture@example', json.dumps(body))

    def test_sector_and_country_restrictions_still_apply_to_masked_snapshot(self):
        rows = project_public_feed({'opportunities':self.rows()})['opportunities']
        for sectors, countries in [(['medical'], []), (['machinery'], ['FR']), ([], [])]:
            self.assertEqual(self.request(rows, sectors, countries)[1]['count'], 0)
        self.assertEqual(self.request(rows, all_sectors=True)[1]['count'], 2)

    def test_auth_and_active_plan_are_still_required(self):
        rows = project_public_feed({'opportunities':self.rows()})['opportunities']
        self.assertEqual(self.request(rows, all_sectors=True, token=False)[0], 401)
        self.assertEqual(self.request(rows, all_sectors=True, active=False)[0], 403)

    def test_raw_goods_are_supported_but_unknown_and_conflicting_service_rows_are_rejected(self):
        raw = self.rows()
        unknown = {'goods_status':'approved','sector_id':'machinery'}
        service = {'goods_status':'goods_candidate','export_goods_review':{'status':'service_candidate'},'sector_id':'machinery'}
        self.assertEqual(self.request(raw + [unknown, service], all_sectors=True)[1]['count'], 2)
