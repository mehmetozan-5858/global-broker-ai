import unittest
from urllib.request import Request
from unittest.mock import patch
from src.ted_search_fields import apply_search_fields
from src.enrichment import enrich_opportunity
from src.public_opportunity_projection import project_public_opportunity
from src import document_parser

class OfficialDocumentLinkTests(unittest.TestCase):
    def test_source_document_link_is_private_and_prioritized_for_reader(self):
        row={'source':'TED','publication-number':'123456-2026','identifier-lot':['LOT-0001'],
             'document-url-lot':['https://buyer.example.test/document?id=1','https://buyer.example.test/document?id=1']}
        apply_search_fields(row);enrich_opportunity(row)
        self.assertNotIn('document-url-lot',row)
        self.assertEqual(row['document_url'],'https://buyer.example.test/document?id=1')
        self.assertEqual(document_parser._source_page_urls(row),[row['document_url']])
        self.assertNotIn('buyer.example.test',str(project_public_opportunity(row)))
        self.assertEqual(row['ted_document_link_count'],1)

    def test_invalid_notice_cannot_leave_unknown_raw_url_key(self):
        row={'source':'TED','publication-number':'invalid','document-url-lot':'https://buyer.example.test/private'}
        apply_search_fields(row)
        self.assertNotIn('document-url-lot',row)
        self.assertNotIn('document_url',row)

    def test_credentialed_insecure_or_malformed_links_are_not_promoted(self):
        for url in ['http://example.test/doc','https://user:secret@example.test/doc','javascript:bad','https://example.test/a https://example.test/b']:
            row={'source':'TED','publication-number':'123456-2026','document-url-lot':url}
            apply_search_fields(row)
            self.assertNotIn('document_url',row)
            self.assertNotIn('document-url-lot',row)

    def test_dynamic_document_endpoint_is_parsed_as_pdf_not_html(self):
        url='https://buyer.example.test/download?id=12'
        row={'document_url':url}
        text='Source technical specification. '+('The buyer requires source-backed delivery and product requirements. '*4)
        with patch.object(document_parser,'_download',return_value=(b'%PDF-fixture','application/octet-stream',url)),patch.object(document_parser,'_parse_pdf',return_value=text):
            document_parser.enrich_opportunity(row)
        info=row['document_extraction']
        self.assertEqual(info['parsed_count'],1)
        self.assertEqual(info['attempts'][0]['source'],'linked_document')
        self.assertEqual(info['attempts'][0]['kind'],'pdf')
        self.assertEqual(row['document_extracted_text'],text)
        self.assertNotIn('verified_unit_price',row)

    def test_private_redirect_is_rejected_before_following(self):
        handler=document_parser._PublicRedirectHandler()
        with patch.object(document_parser,'_public_http_url',return_value=False),patch('urllib.request.HTTPRedirectHandler.redirect_request') as follow:
            with self.assertRaisesRegex(ValueError,'redirected_to_non_public_url'):
                handler.redirect_request(Request('https://example.test/doc'),None,302,'Found',{},'http://127.0.0.1/private')
            follow.assert_not_called()

    def test_public_redirect_keeps_standard_redirect_behavior(self):
        handler=document_parser._PublicRedirectHandler()
        with patch.object(document_parser,'_public_http_url',return_value=True):
            request=handler.redirect_request(Request('https://example.test/doc'),None,302,'Found',{},'https://example.test/spec.pdf')
        self.assertEqual(request.full_url,'https://example.test/spec.pdf')

    def test_credentialed_url_is_rejected_before_dns_lookup(self):
        with patch.object(document_parser.socket,'getaddrinfo') as dns:
            self.assertFalse(document_parser._public_http_url('https://user:secret@example.test/doc'))
            dns.assert_not_called()

if __name__=='__main__':unittest.main()
