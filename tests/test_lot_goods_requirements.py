import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from src.technical_requirements import extract_document
from src.technical_matcher import process_payload
from src.document_parser import enrich_opportunity
from src.public_opportunity_projection import project_public_opportunity

URL = 'https://search.worldbank.org/api/v2/procnotices?qterm=OP00000001'
HEADER = '\nDescription of Goods\nUnit\nAmount\n'
TABLE = ('Reference LOT 1 title is not a table\nTEST-G3 LOT 1' + HEADER +
         '42 METER HYDRAULIC LADDER FIRE TRUCK\nNumber\n1\nTEST-G3 LOT 2' + HEADER +
         'MULTI-PURPOSE FIRE TRUCK WITH A CAPACITY OF AT LEAST 4000 LITERS\nNumber\n7\n'
         'MULTI-PURPOSE FIRE TRUCK WITH A CAPACITY OF AT LEAST 3000 LITERS\nNumber\n3\n'
         'TEST-G3 LOT 3' + HEADER +
         'MULTI-PURPOSE FIRE TRUCK WITH A CAPACITY OF AT LEAST 5000 LITERS\nNumber\n8\n'
         '3.The technical weighting will be applied as 40%.')


def row():
    return {'id': 'OP00000001', 'source': 'WORLD_BANK', 'document_extracted_text': TABLE,
            'technical_requirement_scopes': extract_document(URL, TABLE),
            'source_lot_selection_required': True,
            'document_extraction': {'checked_at': datetime.now(timezone.utc).isoformat(),
                                    'attempts': [{'url': URL, 'status': 'parsed', 'kind': 'source_page',
                                                  'format': 'world_bank_notice_json', 'notice_id': 'OP00000001'}]}}


class LotGoodsRequirementsTests(unittest.TestCase):
    def test_scopes_keep_products_in_same_lot_separate_and_never_guess_other_dimensions(self):
        scopes = extract_document(URL, TABLE)
        self.assertEqual(len(scopes), 3)
        self.assertEqual([s['lot_id'] for s in scopes], ['2', '2', '3'])
        self.assertEqual([s['source_quantity'] for s in scopes], ['7', '3', '8'])
        self.assertEqual([s['clauses'][0]['expected'] for s in scopes], [{'min':4000}, {'min':3000}, {'min':5000}])
        self.assertTrue(all(s['clauses'][0]['quote'] in TABLE for s in scopes))
        self.assertTrue(all(s['coverage'] == 'partial' for s in scopes))

    def test_ambiguous_damaged_truncated_tables_rejected_as_a_whole(self):
        for text in [TABLE+TABLE, TABLE.replace('TEST-G3 LOT 3', 'TEST-G3 LOT 4'),
                     TABLE.replace('TEST-G3 LOT 3', 'OTHER LOT 3'), TABLE.replace('Number', 'USD', 1),
                     TABLE.replace('Number\n7', 'Number\n0'), TABLE.replace('Number\n3', 'Number\n3,000'),
                     TABLE[:TABLE.index('3.The')], TABLE.replace('Unit\nAmount', 'Unit\nUnknown', 1),
                     TABLE.replace('TEST-G3 LOT 3', 'TEST-G3 LOT 2')]:
            self.assertEqual(extract_document(URL, text), [], text[-100:])

    def test_source_identity_refresh_and_clause_replay_required(self):
        for mutate in [lambda r:r.update(id='OP00000002'),
                       lambda r:r['document_extraction'].update(checked_at='2020-01-01T00:00:00+00:00'),
                       lambda r:r['document_extraction']['attempts'][0].update(status='failed'),
                       lambda r:r.update(document_extracted_text=TABLE.replace('4000', '4500')),
                       lambda r:r['technical_requirement_scopes'][0]['clauses'][0].update(expected={'min':1})]:
            r=row();mutate(r);process_payload({'opportunities':[r]}, [])
            # Changed individual requirements may survive only for unchanged products.
            self.assertFalse(any(s['scope'].endswith('4000 LITERS') for s in r['technical_comparison']['scopes']))

    def test_fire_trucks_do_not_fetch_or_compare_bus_catalogues_or_approve_financials(self):
        r=row()
        with patch('src.technical_matcher.refresh') as refresh:
            process_payload({'opportunities':[r]});refresh.assert_not_called()
        self.assertEqual(r['technical_comparison']['status'], 'manufacturer_research_required')
        self.assertTrue(all(not s['models'] for s in r['technical_comparison']['scopes']))
        bus={'manufacturer':'Bus company','model':'Bus','url':'https://example.test/bus','status':'read',
             'checked_at':datetime.now(timezone.utc).isoformat(),'facts':[{'field':'tank_capacity_l','value':9999}]}
        payload=process_payload({'opportunities':[r]}, [bus])
        self.assertEqual(payload['technical_comparison_summary']['compared_scopes'], 0)
        self.assertFalse(r['technical_comparison']['exact_spec_match_verified'])
        self.assertNotIn('verified_unit_price', r)
        public=project_public_opportunity(r)
        self.assertNotIn('technical_comparison', public)
        self.assertNotIn('technical_requirement_scopes', public)

    def test_exact_official_api_response_is_extracted_during_current_scan(self):
        import json
        html='<p>' + TABLE.replace('\n', '</p><p>') + '</p>'
        body=json.dumps({'procnotices': {'one': {'id':'OP00000001', 'notice_text':html}}}).encode()
        def download(url, limit): return body, 'application/json', url
        with patch('src.document_parser._download', side_effect=download):
            r=enrich_opportunity({'id':'OP00000001','source':'WORLD_BANK'})
        self.assertEqual(len(r['technical_requirement_scopes']), 3)
        process_payload({'opportunities':[r]}, [])
        self.assertEqual(len(r['technical_comparison']['scopes']), 3)
