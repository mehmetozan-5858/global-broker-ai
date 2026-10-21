import copy
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from src.technical_requirements import extract_document
from src.technical_matcher import process_payload, compare_clause
from src.manufacturer_catalog import parse, PROFILES, _read
from src.public_opportunity_projection import project_public_opportunity

URL = 'https://example.test/capitolato.pdf'
TEXT = '''Caratteristica LOTTO 1 – Place A (n. 2 mezzi) LOTTO 2 – Place B (n. 1 mezzo)
Categoria veicolo M3, Classe I urbano M3, Classe I urbano
Lunghezza 7-8 metri (autobus corto) circa 8 metri
Alimentazione Metano (CNG), serbatoi omologati sul
tetto o in vano dedicato
Metano (CNG), serbatoi omologati sul
tetto o in vano dedicato
Standard emissivo Euro 6 Step E (Reg. UE 2018/1832) Euro 6 Step E (Reg. UE 2018/1832)
Capienza complessiva 27 posti (seduti + in piedi) 29/30 posti (seduti + in piedi)
'''


def now(): return datetime.now(timezone.utc).isoformat()


def row():
    return {'document_extracted_text': TEXT, 'technical_requirement_scopes': extract_document(URL, TEXT),
            'ted_lot_selection_required': True, 'document_extraction': {'checked_at': now(),
                'attempts': [{'url': URL, 'kind': 'pdf', 'status': 'parsed'}]}}


def catalog(mm=7990):
    profile = PROFILES[0]
    return {**profile, 'status': 'read', 'checked_at': now(),
            'facts': parse(profile, f'MODEL First FCLEI MAX. TOTAL WEIGHT 7 200 kg OVERAL LENGHT {mm} mm Optional equipment: CNG or electric motor drive')}


class TechnicalComparisonTests(unittest.TestCase):
    def test_extracts_first_explicit_scope_and_keeps_partial_coverage(self):
        scopes = extract_document(URL, TEXT)
        self.assertEqual(len(scopes), 1)
        self.assertEqual(scopes[0]['scope'], 'LOTTO 1')
        self.assertEqual(scopes[0]['coverage'], 'partial')
        self.assertTrue(scopes[0]['other_columns_not_inferred'])
        self.assertEqual(scopes[0]['clauses'][0]['expected'], {'min': 7000, 'max': 8000})
        self.assertEqual(scopes[0]['clauses'][1]['expected'], 27)
        self.assertTrue(all(c['quote'] in TEXT and c['source_url'] == URL for c in scopes[0]['clauses']))

    def test_unknown_duplicate_approximate_or_three_column_layout_is_not_guessed(self):
        for text in [TEXT+TEXT, TEXT.replace('7-8 metri', 'circa 8 metri'),
                     TEXT.replace('27 posti', '27/30 posti'),
                     TEXT.replace('LOTTO 2 – Place B', 'LOTTO 2 – Place B LOTTO 3 – Place C')]:
            self.assertEqual(extract_document(URL, text), [])
        self.assertEqual(extract_document('https://u:p@example.test/spec.pdf', TEXT), [])

    def test_comparison_distinguishes_length_support_conflict_option_and_unknown(self):
        r=row(); payload={'opportunities':[r]}; process_payload(payload, [catalog(), catalog(8040)])
        result=r['technical_comparison']; scope=result['scopes'][0]
        first=scope['models'][0]['clause_results']; second=scope['models'][1]['clause_results']
        self.assertEqual(first[0]['status'], 'source_supported')
        self.assertEqual(second[0]['status'], 'conflict')
        self.assertEqual(first[4]['status'], 'configuration_confirmation_required')
        self.assertEqual(first[1]['status'], 'missing_evidence')
        self.assertTrue(result['lot_selection_required'])
        self.assertTrue(result['human_review_required'])
        self.assertFalse(result['exact_spec_match_verified'])
        self.assertNotIn('supplier_candidates', r)
        self.assertNotIn('verified_unit_price', r)
        self.assertEqual(payload['technical_comparison_summary']['exact_spec_approvals'], 0)

    def test_stale_failed_or_changed_source_drops_prior_comparison(self):
        for mutate in [lambda r:r['document_extraction'].update(checked_at='2020-01-01T00:00:00+00:00'),
                       lambda r:r['document_extraction']['attempts'][0].update(status='failed'),
                       lambda r:r.update(document_extracted_text=TEXT.replace('7-8 metri','6-7 metri')),
                       lambda r:r['technical_requirement_scopes'][0]['clauses'][0].update(expected={'min':1,'max':999999})]:
            r=row();process_payload({'opportunities':[r]},[catalog()]);mutate(r)
            with patch('src.technical_matcher.refresh') as network:
                process_payload({'opportunities':[r]})
                network.assert_not_called()
            self.assertEqual(r['technical_comparison']['status'], 'requirements_not_structured')
            self.assertEqual(r['technical_comparison']['scopes'], [])

    def test_failed_or_stale_catalog_never_reuses_previous_match(self):
        for changes in [{'status':'unavailable','facts':[]}, {'checked_at':'2020-01-01T00:00:00+00:00'}]:
            c=catalog();c.update(changes);r=row();process_payload({'opportunities':[r]},[c])
            self.assertTrue(all(x['status']=='catalog_unavailable' for x in r['technical_comparison']['scopes'][0]['models'][0]['clause_results']))

    def test_model_fact_cannot_be_borrowed_from_other_variant(self):
        self.assertEqual(parse(PROFILES[0], 'MODEL First FCLLI MAX. TOTAL WEIGHT 7 200 kg OVERAL LENGHT 8040 mm'), [])
        facts=parse(PROFILES[0], 'MODEL First FCLEI MAX. TOTAL WEIGHT 7 200 kg OVERAL LENGHT 7990 mm OVERAL LENGHT 8040 mm')
        self.assertFalse(any(f['field']=='length_mm' for f in facts))

    def test_bad_numeric_unit_url_or_conflicting_catalog_is_not_supported(self):
        clause=row()['technical_requirement_scopes'][0]['clauses'][0]
        for value in [True, float('nan'), float('inf')]:
            c=catalog();c['facts'][0]['value']=value
            self.assertEqual(compare_clause(clause,c)['status'],'invalid_catalog_evidence')
        for changes in [{'quote':'OVERAL LENGHT 799 cm'}, {'source_url':'https://other.test/model'}]:
            c=catalog();c['facts'][0].update(changes)
            self.assertEqual(compare_clause(clause,c)['status'],'invalid_catalog_evidence')
        c=catalog();other=copy.deepcopy(c['facts'][0]);other['value']=8040;c['facts'].append(other)
        self.assertEqual(compare_clause(clause,c)['status'],'conflicting_catalog_evidence')

    def test_single_catalog_refresh_serves_all_rows_and_no_private_evidence_is_public(self):
        payload={'opportunities':[row(),row(),{'title':'Unstructured goods'}]}
        with patch('src.technical_matcher.refresh',return_value=[catalog()]) as refresh:
            process_payload(payload);refresh.assert_called_once()
        self.assertEqual(payload['technical_comparison_summary']['compared_scopes'],2)
        for r in payload['opportunities']:
            public=project_public_opportunity(r)
            self.assertNotIn('technical_comparison',public)
            self.assertNotIn('technical_requirement_scopes',public)
            self.assertNotIn('example.test',str(public))

    def test_catalog_reader_requires_current_model_path_and_records_fetch_failure(self):
        url=PROFILES[0]['url']
        html=b'<table><tr><td>MODEL</td><td>First FCLEI</td></tr><tr><td>MAX. TOTAL WEIGHT</td><td>7 200 kg</td></tr><tr><td>OVERAL LENGHT</td><td>7 990 mm</td></tr></table><h2>Optional equipment:</h2><p>CNG or electric motor drive</p>'
        with patch('src.manufacturer_catalog.document_parser._download',return_value=(html,'text/html',url)):
            result=_read(PROFILES[0])
        self.assertEqual(result['facts'][0]['value'],7990)
        self.assertEqual(result['status'],'read')
        for response in [(html,'text/html','https://other.test/model'),(html,'application/pdf',url)]:
            with patch('src.manufacturer_catalog.document_parser._download',return_value=response):
                self.assertEqual(_read(PROFILES[0])['facts'],[])
        with patch('src.manufacturer_catalog.document_parser._download',side_effect=TimeoutError('timeout')):
            failed=_read(PROFILES[0])
        self.assertEqual(failed['status'],'unavailable')
        self.assertEqual(failed['facts'],[])
        payload=process_payload({'opportunities':[row()]},[failed])
        self.assertEqual(payload['technical_comparison_summary']['structured_scopes'],1)
        self.assertEqual(payload['technical_comparison_summary']['compared_scopes'],0)
        self.assertEqual(payload['opportunities'][0]['technical_comparison']['status'],'catalog_refresh_required')

    def test_no_requirement_scope_means_no_catalog_network(self):
        with patch('src.technical_matcher.refresh') as network:
            p=process_payload({'opportunities':[{}]});network.assert_not_called()
        self.assertEqual(p['technical_comparison_summary']['compared_scopes'],0)
