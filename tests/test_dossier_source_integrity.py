import unittest
from src.enrichment import enrich_opportunity
from src.ted_search_fields import apply_search_fields
from src.public_opportunity_projection import project_public_opportunity
from src.data_completion_queue import build

class DossierSourceIntegrityTests(unittest.TestCase):
    def row(self):
        return {'source':'TED','publication-number':'123456-2026','identifier-lot':['LOT-0001'],
                'estimated-value-lot':['120000','120000'],'estimated-value-cur-lot':['EUR','EUR']}

    def test_repeated_search_budget_survives_full_dossier_and_public_projection(self):
        row=apply_search_fields(self.row())
        enrich_opportunity(row)
        self.assertEqual(row['estimated_value'],'120000')
        self.assertEqual(row['dossier']['budget_value'],'120000')
        self.assertEqual(row['dossier']['budget_currency'],'EUR')
        self.assertEqual(project_public_opportunity(row)['estimated_budget'],'120000')

    def test_procedure_currency_cannot_replace_scoped_lot_currency(self):
        row=self.row(); row['estimated-value-cur-proc']='USD'
        row=apply_search_fields(row);enrich_opportunity(row)
        self.assertEqual(row['dossier']['budget_currency'],'EUR')
        self.assertEqual(row['currency'],'EUR')

    def test_unselected_lots_never_form_a_flat_quantity_or_budget(self):
        row=self.row();row['identifier-lot']=['LOT-0001','LOT-0002'];row['quantity-lot']=['10','20']
        apply_search_fields(row);enrich_opportunity(row)
        self.assertIsNone(row['dossier']['quantity'])
        self.assertIsNone(row['dossier']['budget_value'])
        self.assertNotIn('quantity',row)
        self.assertNotIn('estimated_value',row)

    def test_ambiguous_single_lot_raw_values_are_not_concatenated(self):
        row=self.row();row['estimated-value-lot']=['120000','220000']
        apply_search_fields(row);enrich_opportunity(row)
        self.assertIsNone(row['dossier']['budget_value'])
        self.assertNotIn('estimated_value',row)
        build({'opportunities':[row]})
        self.assertIn('quantity_or_budget',row['data_completion']['missing_fields'])

    def test_accepted_budget_can_fill_core_quantity_or_budget_requirement(self):
        row=apply_search_fields(self.row());enrich_opportunity(row)
        build({'opportunities':[row]})
        self.assertNotIn('quantity_or_budget',row['data_completion']['missing_fields'])

    def test_conflicting_fact_does_not_appear_as_dossier_budget(self):
        row=apply_search_fields(self.row());row['estimated_value']='50'
        enrich_opportunity(row)
        self.assertIsNone(row['dossier']['budget_value'])
        self.assertNotIn('estimated_budget',project_public_opportunity(row))

    def test_canonical_source_precedes_language_variant_links(self):
        row={'source_url':'https://example.test/en/notice','links':{'html':['https://example.test/ar/notice']}}
        enrich_opportunity(row)
        self.assertEqual(row['document_url'],'https://example.test/en/notice')
        self.assertEqual(row['official_links'][0],row['source_url'])

if __name__=='__main__': unittest.main()
