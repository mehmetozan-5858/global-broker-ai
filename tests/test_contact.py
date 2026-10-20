import io,json,os,threading,unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from unittest.mock import patch
from api.contact import handler,validate,relay

DATA={'id':'3fb7b761-2ea9-4a10-a49e-c5f37e730d40','name':'Fixture Customer','email':'customer@example.com','topic':'Fixture enquiry','message':'A customer initiated message.'}
class ContactTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=ThreadingHTTPServer(('127.0.0.1',0),handler);cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start();cls.url=f'http://127.0.0.1:{cls.server.server_port}/api/contact'
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
 def send(self,body=None,origin='https://broker.aivisibilityworks.com'):
  return urlopen(Request(self.url,data=json.dumps(body or DATA).encode(),headers={'Content-Type':'application/json','Origin':origin},method='POST'))
 def test_valid_contact_filters_customer_supplied_recipient(self):
  self.assertNotIn('to',validate(dict(DATA,to='attacker@example.com')))
  for patcher in ({'email':'a@b@c.com'},{'topic':'a\r\nBcc: attacker@example.com'},{'message':'short'},{'website':'bot-filled'},{'name':{}}):
   with self.assertRaises(ValueError):validate(dict(DATA,**patcher))
 def test_wrong_origin_and_invalid_body_never_relay(self):
  with patch('api.contact.relay') as target:
   for body,origin,code in [(DATA,'https://evil.example',403),(dict(DATA,message='short'),'https://broker.aivisibilityworks.com',400)]:
    with self.assertRaises(HTTPError) as e:self.send(body,origin)
    self.assertEqual(e.exception.code,code)
   target.assert_not_called()
 def test_no_configuration_is_not_a_success(self):
  with patch.dict(os.environ,{'BROKER_CONTACT_RELAY_SECRET':''}):
   with self.assertRaises(HTTPError) as e:self.send()
   self.assertEqual(e.exception.code,503)
 def test_public_response_contains_only_receipt_not_private_relay_fields(self):
  with patch.dict(os.environ,{'BROKER_CONTACT_RELAY_SECRET':'fixture-secret-at-least-32-characters'}),patch('api.contact.relay',return_value=(202,{'ok':True,'id':DATA['id'],'state':'queued'})):
   with self.send() as response:
    self.assertEqual(response.status,202);self.assertEqual(response.headers['Cache-Control'],'no-store');result=json.load(response)
   self.assertEqual(set(result),{'ok','id','state'})
 def test_provider_fields_are_not_exposed_and_relay_signature_covers_payload(self):
  class Response:
   status=200
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self,limit):return json.dumps({'id':DATA['id'],'state':'email_accepted','to':'private@example.com','provider_id':'private-provider-id'}).encode()
  with patch('api.contact.urlopen',return_value=Response()) as request:
   status,result=relay(DATA,'127.0.0.1','fixture-secret')
   sent=request.call_args.args[0];self.assertNotIn('127.0.0.1',sent.data.decode());self.assertNotIn('to',result);self.assertNotIn('provider_id',result)
   import hmac,hashlib
   stamp=sent.headers['X-broker-timestamp'];expected=hmac.new(b'fixture-secret',stamp.encode()+b'\n'+sent.data,hashlib.sha256).hexdigest();self.assertEqual(sent.headers['X-broker-signature'],expected)
