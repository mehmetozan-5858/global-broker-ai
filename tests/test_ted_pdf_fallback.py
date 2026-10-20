import unittest
from unittest.mock import patch
from src import document_parser, ted_xml_enricher

PUBLICATION='123456-2026'
TEXT=PUBLICATION+' - Competition. '+('Source technical specification and procurement requirements. '*7)

class TedPdfFallbackTests(unittest.TestCase):
    def item(self,form='competition'):
        return {'source':'TED','publication-number':PUBLICATION,'form-type':form}

    def download(self,url,*args):
        if url.endswith('/pdf'):return b'%PDF-test', 'application/pdf',url
        raise ValueError('source-unavailable')

    def test_pdf_after_xml_html_failure_preserves_provenance_and_no_structured_claim(self):
        row=self.item()
        with patch.object(document_parser,'_download',side_effect=self.download) as fetch,patch.object(document_parser,'_parse_pdf',return_value=TEXT):
            self.assertTrue(ted_xml_enricher.enrich_opportunity(row))
        info=row['document_extraction']
        self.assertEqual(fetch.call_count,3)
        self.assertTrue(info['ted_pdf_parsed'])
        self.assertFalse(info['ted_xml_parsed'])
        self.assertEqual(info['parsed_count'],1)
        self.assertEqual([x['source'] for x in info['attempts']],['ted_xml','ted_html_download','ted_pdf_download'])
        self.assertNotIn('ted_lots',row)
        self.assertNotIn('verified_unit_price',row)
        self.assertNotIn('contact_email',row)

    def test_wrong_notice_or_only_late_reference_is_rejected(self):
        for text in ['999999-2026 '+('Wrong notice. '*30),('Unrelated text '*100)+TEXT]:
            with patch.object(document_parser,'_download',side_effect=self.download),patch.object(document_parser,'_parse_pdf',return_value=text):
                row=self.item();self.assertFalse(ted_xml_enricher.enrich_opportunity(row))
                self.assertNotIn('document_extracted_text',row)
                self.assertFalse(row['document_extraction']['ted_pdf_parsed'])

    def test_html_challenge_is_not_pdf_even_when_mime_claims_pdf(self):
        def download(url,*args):
            if url.endswith('/pdf'):return b'<html>verify browser</html>','application/pdf',url
            raise ValueError('source-unavailable')
        with patch.object(document_parser,'_download',side_effect=download),patch.object(document_parser,'_parse_pdf') as parse:
            self.assertFalse(ted_xml_enricher.enrich_opportunity(self.item()))
            parse.assert_not_called()

    def test_origin_or_notice_redirect_cannot_be_accepted(self):
        for target in ['https://example.test/notice/'+PUBLICATION+'/pdf','https://ted.europa.eu/en/notice/999999-2026/pdf']:
            def download(url,*args):
                if url.endswith('/pdf'):return b'%PDF-test','application/pdf',target
                raise ValueError('source-unavailable')
            with patch.object(document_parser,'_download',side_effect=download),patch.object(document_parser,'_parse_pdf',return_value=TEXT):
                self.assertFalse(ted_xml_enricher.enrich_opportunity(self.item()))

    def test_no_pdf_probe_for_result_or_unknown_context(self):
        for form in ['result',None]:
            with patch.object(document_parser,'_download',side_effect=ValueError('offline')) as fetch:
                self.assertFalse(ted_xml_enricher.enrich_opportunity(self.item(form)))
                self.assertEqual(fetch.call_count,2)

    def test_official_text_is_not_truncated_behind_a_long_generic_page(self):
        row=self.item();row['document_extracted_text']='generic '*10000
        with patch.object(document_parser,'_download',side_effect=self.download),patch.object(document_parser,'_parse_pdf',return_value=TEXT):
            self.assertTrue(ted_xml_enricher.enrich_opportunity(row))
        self.assertTrue(row['document_extracted_text'].startswith(TEXT))
        self.assertLessEqual(len(row['document_extracted_text']),document_parser.MAX_EXTRACTED_CHARS)

    def test_combined_source_urls_remain_separate_download_candidates(self):
        urls=document_parser._collect_urls('https://example.test/a.pdf https://example.test/b.pdf')
        self.assertEqual(urls,['https://example.test/a.pdf','https://example.test/b.pdf'])

    def test_already_parsed_technical_attachment_keeps_its_text_priority(self):
        row=self.item()
        row['document_extracted_text']='Technical attachment specification. '*2000
        row['document_extraction']={'attempts':[{'source':'linked_document','kind':'pdf','status':'parsed'}]}
        with patch.object(document_parser,'_download',side_effect=self.download),patch.object(document_parser,'_parse_pdf',return_value=TEXT):
            self.assertTrue(ted_xml_enricher.enrich_opportunity(row))
        self.assertTrue(row['document_extracted_text'].startswith('Technical attachment specification.'))
        self.assertEqual(row['document_extraction']['parsed_count'],2)

if __name__=='__main__':unittest.main()
