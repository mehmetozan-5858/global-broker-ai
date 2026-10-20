import copy
import unittest
from src.notice_fact_cache import process
from src.public_opportunity_projection import project_public_opportunity

DATE='2026-10-19'
def cache():
    return {'notices':{'681530-2026':{'lot_count':1,'verified_at':DATE,'fields':{'estimated_value':'600000','budget_currency':'EUR','submission_deadline_date':'2026-10-23','private_buyer':'do not retain'}}}}
def notice():
    return {'source':'TED','publication-number':'681530-2026','document_extraction':{'ted_xml_parsed':False}}

class NoticeFactCacheTests(unittest.TestCase):
    def test_failed_fetch_retains_approved_fields_and_their_real_source_age(self):
        row=notice();result=process([row],cache(),'2026-10-20T12:00:00+00:00')
        self.assertEqual(row['estimated_value'],'600000')
        self.assertEqual(row['notice_source_state'],'previously_verified_document')
        self.assertEqual(row['notice_source_verified_at'],DATE)
        self.assertEqual(result['last_scan']['reused_notices'],1)
        public=project_public_opportunity(row)
        self.assertEqual(public['estimated_budget'],'600000')
        self.assertEqual(public['source_verified_at'],DATE)
        self.assertNotIn('verified_unit_price',row)
        self.assertNotIn('private_buyer',str(result))

    def test_another_notice_or_multilot_conflict_never_gets_cached_values(self):
        for change in [{'publication-number':'999999-2026'},{'ted_lot_count':2},{'ted_lot_selection_required':True},{'source':'Other'}]:
            row=notice();row.update(change);process([row],cache())
            self.assertNotIn('estimated_value',row)

    def test_current_values_are_not_overwritten_or_mixed_with_cached_currency(self):
        row=notice();row.update(estimated_value='900',budget_currency='USD')
        process([row],cache())
        self.assertEqual(row['estimated_value'],'900')
        self.assertEqual(row['budget_currency'],'USD')
        self.assertNotIn('public_source_terms',row)

    def test_successful_new_xml_invalidates_prior_values_that_disappeared(self):
        row=notice();row['document_extraction']['ted_xml_parsed']=True;row['ted_lot_count']=1
        result=process([row],cache())
        self.assertNotIn('681530-2026',result['notices'])
        self.assertNotIn('estimated_value',row)

    def test_new_explicit_source_fact_refreshes_safe_cache(self):
        row=notice();row.update(estimated_value='500000',budget_currency='EUR',ted_lot_count=1)
        row['document_extraction']['ted_xml_parsed']=True
        row['structured_source_evidence']={'estimated_value':{'inferred':False,'source_path':'procurementproject/requestedtendertotal/estimatedoverallcontractamount'}}
        result=process([row],cache(),'2026-10-20T12:00:00+00:00')
        self.assertEqual(result['notices']['681530-2026']['fields']['estimated_value'],'500000')
        self.assertNotIn('submission_deadline_date',result['notices']['681530-2026']['fields'])
        self.assertEqual(result['notices']['681530-2026']['verified_at'],'2026-10-20T12:00:00+00:00')

    def test_partial_cache_without_budget_does_not_create_estimate_or_abort_batch(self):
        for fields in [{'quantity': '25 pieces'}, {'submission_deadline_date': '2026-10-23'},
                       {'quantity': '25 pieces', 'estimated_value': '600', 'budget_currency': ''}]:
            with self.subTest(fields=fields):
                saved = cache()
                saved['notices']['681530-2026']['fields'] = fields
                row = notice()
                second = notice()
                result = process([row, second], saved)
                self.assertEqual(result['last_scan']['reused_notices'], 2)
                for candidate in (row, second):
                    self.assertNotIn('estimated_value', candidate)
                    self.assertNotIn('budget_currency', candidate)
                    self.assertNotIn('public_source_terms', candidate)
                    self.assertEqual(candidate['notice_source_verified_at'], DATE)
