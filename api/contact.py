"""Public contact intake; owner destination and relay credentials stay server-only."""
from http.server import BaseHTTPRequestHandler
import hashlib
import hmac
import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ORIGINS={'https://broker.aivisibilityworks.com','https://global-broker-opal.vercel.app'}
RELAY='https://www.aivisibilityworks.com/api/broker-contact'


def validate(raw):
    if not isinstance(raw,dict) or str(raw.get('website') or '').strip():raise ValueError('invalid-contact')
    if not all(isinstance(raw.get(k),str) for k in ('id','name','email','topic','message')):raise ValueError('invalid-contact')
    row={k:raw[k].strip() for k in ('id','name','email','topic','message')}
    if not re.fullmatch(r'[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-4[a-fA-F0-9]{3}-[89abAB][a-fA-F0-9]{3}-[a-fA-F0-9]{12}',row['id']):raise ValueError('invalid-contact')
    if not 2<=len(row['name'])<=100 or not 3<=len(row['topic'])<=120 or not 10<=len(row['message'])<=5000:raise ValueError('invalid-contact')
    if len(row['email'])>254 or not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+',row['email']):raise ValueError('invalid-contact')
    if re.search(r'[\x00-\x1f\x7f]',row['name']+row['email']+row['topic']) or re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]',row['message']):raise ValueError('invalid-contact')
    return row


def relay(row,ip,secret):
    row=dict(row,ipHash=hmac.new(secret.encode(),('ip:'+ip).encode(),hashlib.sha256).hexdigest())
    raw=json.dumps(row,ensure_ascii=False,separators=(',',':')).encode()
    timestamp=str(int(time.time()))
    signature=hmac.new(secret.encode(),timestamp.encode()+b'\n'+raw,hashlib.sha256).hexdigest()
    request=Request(RELAY,data=raw,method='POST',headers={'Content-Type':'application/json','X-Broker-Timestamp':timestamp,'X-Broker-Signature':signature})
    try:response=urlopen(request,timeout=45)
    except HTTPError as error:response=error
    with response:
        result=json.loads(response.read(16000))
        if response.status in (200,202) and result.get('id')==row['id'] and result.get('state') in ('email_accepted','queued'):
            return response.status,{'ok':True,'id':row['id'],'state':result['state']}
        if response.status in (400,409,429):return response.status,{'error':{400:'invalid-contact',409:'contact-conflict',429:'contact-rate-limit'}[response.status]}
        return 503,{'error':'contact-unavailable'}


class handler(BaseHTTPRequestHandler):
    def _contact_json(self,status,body):
        raw=json.dumps(body,ensure_ascii=False).encode()
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers();self.wfile.write(raw)
    def do_POST(self):
        if self.headers.get('Origin','') not in ORIGINS:
            return self._contact_json(403,{'error':'invalid-origin'})
        if self.headers.get('Content-Type','').split(';')[0].strip().lower()!='application/json':
            return self._contact_json(415,{'error':'json-required'})
        try:size=int(self.headers.get('Content-Length','0'))
        except ValueError:size=0
        if size<=0 or size>16000:return self._contact_json(413,{'error':'invalid-size'})
        try:row=validate(json.loads(self.rfile.read(size)))
        except (ValueError,UnicodeDecodeError):return self._contact_json(400,{'error':'invalid-contact'})
        secret=os.getenv('BROKER_CONTACT_RELAY_SECRET','')
        if len(secret)<32:return self._contact_json(503,{'error':'contact-unavailable'})
        ip=(self.headers.get('x-vercel-forwarded-for') or self.headers.get('x-forwarded-for') or self.client_address[0]).split(',')[0].strip()[:120]
        try:status,result=relay(row,ip,secret)
        except (URLError,TimeoutError,OSError,ValueError,TypeError):status,result=503,{'error':'contact-unavailable'}
        return self._contact_json(status,result)
