import io
import unittest
from unittest.mock import patch
from src.ted_response_probe import inspect_official_response,response_shape,LIMIT


class Response(io.BytesIO):
    def __init__(self,data,status=200,mime='application/xml',url='https://ted.europa.eu/en/notice/123-2026/xml'):
        super().__init__(data);self.status=status;self.headers={'Content-Type':mime};self.url=url
    def geturl(self):return self.url


class Opener:
    def __init__(self,response):self.response=response;self.requests=[]
    def open(self,request,timeout):self.requests.append(request);return self.response


class OfficialResponseProbeTests(unittest.TestCase):
    def test_empty_202_is_not_an_xml_document(self):
        opener=Opener(Response(b'',status=202,mime='text/html'))
        with patch('src.ted_response_probe.document_parser._public_http_url',return_value=True):
            result=inspect_official_response('123-2026','xml',opener)
        self.assertEqual(result['http_status'],202);self.assertEqual(result['body_kind'],'empty')
        self.assertFalse(result['accepted_as_notice']);self.assertIn('application/xml',opener.requests[0].get_header('Accept'))

    def test_xml_root_is_classified_without_logging_customer_text(self):
        opener=Opener(Response(b'<ContractNotice><Name>PRIVATE-NAME</Name></ContractNotice>'))
        with patch('src.ted_response_probe.document_parser._public_http_url',return_value=True):
            result=inspect_official_response('123-2026','xml',opener)
        self.assertEqual(result['root_kind'],'contractnotice');self.assertNotIn('PRIVATE',str(result))
        self.assertFalse(result['accepted_as_notice'])

    def test_challenge_and_large_response_are_bounded_metadata_only(self):
        self.assertTrue(response_shape(b'<html>captcha challenge.js</html>','text/html')['challenge_indicator'])
        opener=Opener(Response(b'X'*(LIMIT+100)))
        with patch('src.ted_response_probe.document_parser._public_http_url',return_value=True):
            result=inspect_official_response('123-2026','xml',opener)
        self.assertTrue(result['sample_truncated']);self.assertEqual(result['sample_bytes'],LIMIT)

    def test_private_wrong_origin_and_wrong_notice_cannot_be_diagnostics_sources(self):
        for url in ['https://example.org/en/notice/123-2026/xml','http://ted.europa.eu/en/notice/123-2026/xml',
                    'https://ted.europa.eu/en/notice/124-2026/xml']:
            with patch('src.ted_response_probe.document_parser._public_http_url',return_value=True):
                result=inspect_official_response('123-2026','xml',Opener(Response(b'<Notice/>',url=url)))
            self.assertIn('error',result)
        with self.assertRaises(ValueError):inspect_official_response('../private','xml')
        with patch('src.ted_response_probe.document_parser._public_http_url',return_value=False):
            self.assertEqual(inspect_official_response('123-2026','xml')['error'],'public-address-validation-failed')
