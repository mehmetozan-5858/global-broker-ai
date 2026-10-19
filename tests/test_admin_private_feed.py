import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch

from api.admin_opportunities import handler

class AdminPrivateFeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}/api/admin_opportunities'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def request(self,token='fixture-only'):
        return urlopen(Request(self.url,headers={'Authorization':'Bearer '+token}))
    def test_admin_gets_private_rows_without_masked_file(self):
        full={'opportunities':[{'opportunity_id':'example','buyer-name':'PRIVATE FIXTURE BUYER','document_extracted_text':'PRIVATE FIXTURE SPEC'}]}
        with patch('api.admin_opportunities._supabase_json',side_effect=[{'id':'fixture-user'},[{'role':'admin'}]]),patch('api.admin_opportunities._private_feed',return_value=full),patch('api.admin_opportunities._data_path',return_value=None):
            with self.request() as response:
                self.assertEqual(response.headers['Cache-Control'],'private, no-store, max-age=0')
                result=json.load(response)
        self.assertEqual(result['opportunities'][0]['buyer-name'],'PRIVATE FIXTURE BUYER')
        self.assertEqual(result['opportunities'][0]['document_extracted_text'],'PRIVATE FIXTURE SPEC')
        self.assertEqual(result['mode'],'admin_authenticated_private_feed')
    def test_private_outage_never_falls_back_to_masked_file_as_full(self):
        with patch('api.admin_opportunities._supabase_json',side_effect=[{'id':'fixture-user'},[{'role':'admin'}]]),patch('api.admin_opportunities._private_feed',return_value=None),patch('api.admin_opportunities._data_path') as masked:
            with self.assertRaises(HTTPError) as error:self.request()
            self.assertEqual(error.exception.code,503)
            self.assertEqual(json.load(error.exception)['status'],'PRIVATE_OPPORTUNITY_FEED_UNAVAILABLE')
            masked.assert_not_called()
    def test_nonadmin_never_calls_private_feed(self):
        with patch('api.admin_opportunities._supabase_json',side_effect=[{'id':'fixture-user'},[{'role':'customer'}]]),patch('api.admin_opportunities._private_feed') as feed:
            with self.assertRaises(HTTPError) as error:self.request()
            self.assertEqual(error.exception.code,403);feed.assert_not_called()
    def test_invalid_session_never_calls_private_feed(self):
        with patch('api.admin_opportunities._supabase_json',return_value=None),patch('api.admin_opportunities._private_feed') as feed:
            with self.assertRaises(HTTPError) as error:self.request()
            self.assertEqual(error.exception.code,401);feed.assert_not_called()
