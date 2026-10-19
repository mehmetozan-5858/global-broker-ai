import copy
import unittest

from src.enrichment import enrich_opportunity
from src.opportunity_identity import stable_opportunity_id
from src.product_detail import source_product_detail
from src.public_opportunity_projection import project_public_opportunity
from src.supplier_research import prepare
from src.stage4_supplier_financial_gate import process_payload


def notice():
    return {
        'source': 'TED', 'publication-number': '681487-2026',
        'opportunity_id': 'existing-identity',
        'title_original': 'Denmark – Machines and apparatus for testing and measuring – One Photonic Wafer Probe Station and one Photonic Assembly Station',
        'title_tr': 'Makine / ekipman alımı',
        'product_name': 'Makine / ekipman alımı',
        'specification_analysis': {'supplier_sourcing_ready': True},
    }


class SupplierCapabilityEvidenceTests(unittest.TestCase):
    def test_source_detail_keeps_real_product_and_existing_identity(self):
        row = notice()
        prior = stable_opportunity_id(row)
        enrich_opportunity(row)
        self.assertEqual(row['product_name'], 'Makine / ekipman alımı')
        self.assertEqual(stable_opportunity_id(row), prior)
        self.assertEqual(project_public_opportunity(row)['product_detail'], 'One Photonic Wafer Probe Station and one Photonic Assembly Station')

    def test_detail_removes_known_buyer_identity_contacts_and_urls(self):
        row = {'title_original': 'Pump for Secret Buyer contact x@example.com +90 555 123 4567 https://private.example', 'buyer-name': 'Secret Buyer'}
        detail = source_product_detail(row)
        for private in ('Secret Buyer', 'x@example.com', '555 123', 'private.example'):
            self.assertNotIn(private, detail)

    def test_arbitrary_title_is_not_added_to_public_projection(self):
        self.assertNotIn('product_detail', project_public_opportunity({'title_original':'Private Buyer needs goods'}))

    def test_real_researched_candidates_keep_requirement_links_and_pending_gaps(self):
        row = notice()
        result = prepare(row)
        self.assertEqual(result['verified_supplier_count'], 2)
        self.assertIn('Photonic', result['search_query'])
        self.assertNotIn('Makine / ekipman', result['search_query'])
        for c in result['candidate_suppliers']:
            self.assertTrue(c['capability_matches'])
            self.assertTrue(c['pending_requirements'])
            self.assertFalse(c['exact_spec_match_verified'])
            self.assertFalse(c['financial_evidence_eligible'])
        process_payload({'opportunities':[row]})
        self.assertFalse(any(c['financial_evidence_eligible'] for c in result['candidate_suppliers']))
        public = project_public_opportunity(row)
        self.assertEqual(public['supplier_capability_count'], 2)
        self.assertNotIn('candidate_suppliers', public)
        self.assertNotIn('FormFactor', str(public))

    def test_other_notice_or_source_or_changed_scope_never_gets_seed_candidates(self):
        for patch in ({'publication-number':'123456-2026'}, {'source':'Other'}, {'title_original':'Furniture'}):
            row = notice();row.update(patch)
            self.assertEqual(prepare(row)['verified_supplier_count'], 0)

    def test_repeated_processing_does_not_duplicate_or_share_mutable_evidence(self):
        row = notice();prepare(row);prepare(row)
        self.assertEqual(len(row['supplier_candidates']), 2)
        row['supplier_candidates'][0]['pending_requirements'].clear()
        fresh = notice();prepare(fresh)
        self.assertTrue(fresh['supplier_candidates'][0]['pending_requirements'])
