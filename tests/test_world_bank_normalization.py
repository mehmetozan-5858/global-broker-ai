import io
import json
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from src.broker import normalize_world_bank, world_bank_search
from src.data_completion_queue import build
from src.field_evidence import annotate
from src.public_opportunity_projection import project_public_opportunity


class WorldBankNormalizationTests(unittest.TestCase):
    def notice(self, **changes):
        row={'id':'OP00473154','bid_description':'Fixture supply of emergency vehicles',
             'project_ctry_name':'Turkiye','submission_deadline_date':'2026-11-20T00:00:00Z',
             'contact_organization':'Fixture Municipality','project_name':'Fixture Regional Reconstruction',
             'noticedate':'06-Oct-2026','procurement_method_name':'Request for Bids','notice_type':'Invitation for Bids'}
        row.update(changes)
        return row

    def normalize(self, row):
        with patch('src.broker.auto_translate_tr',return_value=''):
            return normalize_world_bank(row)

    def test_search_requests_actual_procnotices_fields_and_excludes_contact_secrets(self):
        response=io.BytesIO(json.dumps({'procnotices':{'1':self.notice()}}).encode())
        with patch('src.broker.urllib.request.urlopen',return_value=response) as request:
            rows=world_bank_search(2)
        fields=parse_qs(urlsplit(request.call_args.args[0].full_url).query)['fl'][0].split(',')
        for field in ['project_ctry_name','submission_deadline_date','contact_organization','noticedate']:
            self.assertIn(field,fields)
        for field in ['contact_email','contact_phone_no','contact_name','contact_address','notice_text']:
            self.assertNotIn(field,fields)
        self.assertEqual(rows[0]['id'],'OP00473154')

    def test_official_fields_reach_core_dossier_without_inventing_quantity_or_price(self):
        row=self.normalize(self.notice());annotate(row);build({'opportunities':[row]})
        self.assertEqual(row['buyer-name'],'Fixture Municipality')
        self.assertEqual(row['buyer-country'],'Turkiye')
        self.assertEqual(row['deadline-receipt-tender-date-lot'],'2026-11-20T00:00:00Z')
        self.assertEqual(row['source_url'],'https://projects.worldbank.org/en/projects-operations/procurement-detail/OP00473154')
        self.assertEqual(row['data_completion']['missing_fields'],['quantity_or_budget'])
        self.assertFalse(row['buyer_verified']);self.assertNotIn('verified_unit_price',row)
        self.assertNotIn('document_extracted_text',row)

    def test_project_title_never_substitutes_for_buyer_organization(self):
        row=self.normalize(self.notice(contact_organization=''));build({'opportunities':[row]})
        self.assertEqual(row['buyer-name'],'');self.assertIn('buyer_identity',row['data_completion']['missing_fields'])

    def test_region_is_preserved_without_becoming_a_country(self):
        row=self.normalize(self.notice(project_ctry_name='Western and Central Africa'))
        annotate(row);build({'opportunities':[row]})
        self.assertEqual(row['world_bank_project_region'],'Western and Central Africa')
        self.assertEqual(row['buyer-country'],'');self.assertIsNone(row['field_evidence']['country']['value'])
        self.assertIn('country',row['data_completion']['missing_fields'])

    def test_invalid_notice_ids_cannot_construct_a_source_address(self):
        for identity in ['',None,'OP00473154/evil','OP00473154?token=x','https://evil.invalid','OP1']:
            row=self.normalize(self.notice(id=identity));self.assertEqual(row['source_url'],'')

    def test_public_projection_keeps_recovered_country_and_date_but_masks_buyer(self):
        row=self.normalize(self.notice());annotate(row)
        projected=project_public_opportunity(row)
        self.assertEqual(projected['country'],'Turkiye');self.assertEqual(projected['deadline'],'2026-11-20T00:00:00Z')
        self.assertNotIn('Fixture Municipality',json.dumps(projected))
        self.assertNotIn('source_url',projected);self.assertNotIn('contact_organization',projected)
