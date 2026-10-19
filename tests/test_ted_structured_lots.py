import unittest
from unittest.mock import patch

from src.ted_xml_parser import extract_ted_lots, apply_ted_lots, is_xml_source
from src.ted_xml_enricher import enrich_opportunity, _ted_xml_url
from src.public_opportunity_projection import project_public_opportunity


def lot(identifier='LOT-0001', quantity='12', budget='34000', deadline='2026-12-15'):
    return f'''<cac:ProcurementProjectLot><cbc:ID schemeName="Lot">{identifier}</cbc:ID>
    <cac:ProcurementProject><cbc:Name>Industrial pumps</cbc:Name>
    <cbc:Description>Source tender description for corrosion-resistant industrial pumps with documented technical requirements and delivery conditions.</cbc:Description>
    <cbc:EstimatedOverallContractQuantity unitCode="C62">{quantity}</cbc:EstimatedOverallContractQuantity>
    <cac:RequestedTenderTotal><cbc:EstimatedOverallContractAmount currencyID="EUR">{budget}</cbc:EstimatedOverallContractAmount></cac:RequestedTenderTotal>
    <cac:RealizedLocation><cac:Address><cbc:CityName>Berlin</cbc:CityName><cac:Country><cbc:IdentificationCode>DEU</cbc:IdentificationCode></cac:Country></cac:Address></cac:RealizedLocation>
    </cac:ProcurementProject><cac:TenderingProcess><cac:TenderSubmissionDeadlinePeriod><cbc:EndDate>{deadline}</cbc:EndDate></cac:TenderSubmissionDeadlinePeriod></cac:TenderingProcess>
    </cac:ProcurementProjectLot>'''


def document(*lots):
    return ('<ContractNotice xmlns:cac="urn:aggregate" xmlns:cbc="urn:basic">'+''.join(lots)+'</ContractNotice>').encode()


class TedStructuredLotTests(unittest.TestCase):
    def test_namespace_paths_extract_source_values_with_units_and_currency(self):
        lots = extract_ted_lots(document(lot()))
        self.assertEqual(lots[0]['fields']['quantity']['unit'], 'C62')
        row = {}
        apply_ted_lots(row,lots,'https://ted.europa.eu/en/notice/12345-2026/xml')
        self.assertEqual(row['quantity'],'12 C62')
        self.assertEqual(row['estimated_value'],'34000')
        self.assertEqual(row['budget_currency'],'EUR')
        self.assertEqual(row['submission_deadline_date'],'2026-12-15')
        self.assertNotIn('unit_price',row)
        self.assertNotIn('verified_supplier_quote',row)
        public = project_public_opportunity(row)
        self.assertEqual(public['estimated_budget'],'34000')
        self.assertEqual(public['budget_currency'],'EUR')
        self.assertNotIn('structured_source_evidence',public)
        self.assertNotIn('ted_lots',public)
        self.assertNotIn('https://',str(public))

    def test_multiple_lots_are_never_merged_or_implicitly_selected(self):
        lots=extract_ted_lots(document(lot(),lot('LOT-0002','5','16000','2026-12-20')))
        row={};apply_ted_lots(row,lots,'https://ted.europa.eu/x')
        self.assertTrue(row['ted_lot_selection_required'])
        self.assertNotIn('quantity',row)
        self.assertNotIn('estimated_value',row)
        public=project_public_opportunity(row)
        self.assertEqual(public['lot_count'],2)
        self.assertTrue(public['lot_selection_required'])
        row['selected_lot_id']='LOT-0002'
        apply_ted_lots(row,lots,'https://ted.europa.eu/x')
        self.assertEqual(row['quantity'],'5 C62')
        self.assertEqual(row['estimated_value'],'16000')

    def test_multilot_ambiguity_blocks_core_and_financial_readiness(self):
        from src.data_completion_queue import build
        from src.commercial_feasibility import assess
        row={'buyer_name':'Buyer','product_name':'Pumps','quantity':'10','deadline':'2026-12-15','country':'DE','source_url':'https://example.gov/tender',
             'currency':'EUR','verified_unit_price':'10','verified_freight':'50','delivery_location':'Berlin',
             'supplier_research':{'verified_supplier_count':1},'ted_lot_selection_required':True,'ted_lot_count':2}
        result=build({'opportunities':[row]})
        self.assertEqual(result['core_complete'],0)
        self.assertEqual(result['queue'][0]['next_agent'],'specification_agent')
        self.assertFalse(assess(row)['calculation_ready'])
        self.assertNotIn('approx_quantity',project_public_opportunity(row))

    def test_invalid_numeric_and_date_values_stay_unknown(self):
        fields=extract_ted_lots(document(lot(quantity='NaN',budget='-4',deadline='2026-99-99')))[0]['fields']
        self.assertNotIn('quantity',fields)
        self.assertNotIn('estimated_budget',fields)
        self.assertNotIn('deadline',fields)

    def test_xml_date_timezone_is_preserved_as_source_without_guessing_a_time(self):
        for raw in ['2026-12-15+02:00','2026-12-15Z']:
            fact=extract_ted_lots(document(lot(deadline=raw)))[0]['fields']['deadline']
            self.assertEqual(fact['value'],'2026-12-15')
            self.assertEqual(fact['source_value'],raw)
        fields=extract_ted_lots(document(lot(deadline='2026-12-15+99:99')))[0]['fields']
        self.assertNotIn('deadline',fields)

    def test_existing_source_value_and_unproven_budget_are_not_overridden(self):
        row={'quantity':'20 units','estimated_value':'9000','budget_currency':'USD'}
        apply_ted_lots(row,extract_ted_lots(document(lot())),'https://ted.europa.eu/x')
        self.assertEqual(row['quantity'],'20 units')
        self.assertEqual(row['estimated_value'],'9000')
        self.assertNotIn('estimated_budget',project_public_opportunity(row))

    def test_spa_detail_link_is_replaced_with_official_document_url(self):
        row={'source':'TED','links':{'html':{'ENG':'https://ted.europa.eu/en/notice/-/detail/12345-2026'}}}
        self.assertEqual(_ted_xml_url(row),'https://ted.europa.eu/en/notice/12345-2026/xml')
        self.assertEqual(_ted_xml_url({'source':'TED','publication-number':'12345-2026'}),'https://ted.europa.eu/en/notice/12345-2026/xml')

    def test_html_response_to_xml_uses_identity_checked_html_download(self):
        row={'source':'TED','publication-number':'12345-2026'}
        html=('<html><body><h1>Notice 12345-2026</h1><p>'+('Procurement of industrial pumps, source-backed technical and participation conditions. '*5)+'</p></body></html>').encode()
        calls=[]
        def download(url,*args):
            calls.append(url)
            return html,'text/html',url
        with patch('src.document_parser._download',side_effect=download):
            self.assertTrue(enrich_opportunity(row))
        self.assertEqual(calls,['https://ted.europa.eu/en/notice/12345-2026/xml','https://ted.europa.eu/en/notice/12345-2026/html'])
        self.assertTrue(row['document_extraction']['ted_html_parsed'])
        self.assertFalse(row['document_extraction']['ted_xml_parsed'])
        self.assertFalse(is_xml_source(html,'text/html',calls[0]))

    def test_unrelated_html_cannot_count_as_notice_evidence(self):
        row={'source':'TED','publication-number':'12345-2026'}
        unrelated=b'<html><body>'+b'Welcome to the procurement portal. '*20+b'</body></html>'
        with patch('src.document_parser._download',side_effect=lambda url,*a:(unrelated,'text/html',url)):
            self.assertFalse(enrich_opportunity(row))
        self.assertNotIn('document_extracted_text',row)
