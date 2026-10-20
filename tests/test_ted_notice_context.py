import unittest
from src.ted_search_fields import notice_context, apply_search_fields
from src.public_opportunity_projection import project_public_opportunity
from src.offer_risk_gate import evaluate

class NoticeContextTests(unittest.TestCase):
    def test_only_competition_is_a_call_and_not_automatically_open(self):
        context=notice_context({'source':'TED','form-type':['competition','competition']})
        self.assertTrue(context['call_for_tenders'])
        self.assertNotIn('active',context)
        self.assertIn('son tarih',context['label_tr'])

    def test_non_competition_and_unknown_types_remain_research_only(self):
        for value in ['result','completion','cont-modif','planning','consultation','dir-awa-pre','bri',None,{},['result','competition']]:
            context=notice_context({'source':'TED','form-type':value})
            self.assertTrue(context['research_only'])
            self.assertFalse(context['call_for_tenders'])

    def test_projection_recomputes_type_instead_of_trusting_a_spoofed_context(self):
        row={'source':'TED','form-type':'result','notice_context':{'call_for_tenders':True,'label_tr':'https://private.test'}}
        result=project_public_opportunity(row)
        self.assertTrue(result['notice_context']['research_only'])
        self.assertNotIn('private.test',str(result))

    def test_metadata_survives_even_when_lot_or_budget_is_absent(self):
        row=apply_search_fields({'source':'TED','publication-number':'123456-2026','form-type':'result'})
        self.assertEqual(row['notice_context']['form_type'],'result')

    def test_historical_notice_cannot_open_internal_offer_gate(self):
        row={'source':'TED','form-type':'result','export_goods_review':{'status':'goods_candidate'},
             'buyer_verification':{'verified':True},'specification_analysis':{'supplier_sourcing_ready':True},
             'supplier_research':{'verified_supplier_count':2},
             'commercial_feasibility':{'calculation_ready':True,'landed_cost_ready':True,'facts':{'destination':{'value':'DE'}}},
             'commercial_terms':{'missing':[],'terms':{}}}
        result=evaluate(row)
        self.assertFalse(result['draft_offer_ready'])
        self.assertIn('not_current_tender_call',result['blockers'])
        self.assertFalse(result['external_action_authorized'])
        row['form-type']='competition'
        self.assertTrue(evaluate(row)['draft_offer_ready'])

if __name__=='__main__':unittest.main()
