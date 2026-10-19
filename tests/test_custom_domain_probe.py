import unittest
import io
from urllib.error import URLError, HTTPError
from src.custom_domain_probe import verify, DOMAIN

class Response:
    def __init__(self,url,status,body):self.url=url;self.status=status;self.body=body
    def geturl(self):return self.url
    def read(self,limit):return self.body[:limit]
    def __enter__(self):return self
    def __exit__(self,*args):pass

def opener(request,timeout):
    url=request.full_url
    if url.endswith('/healthz'):return Response(url,204,b'')
    if url.endswith('/api/admin_opportunities'):return Response(url,401,b'{"status":"AUTHENTICATION_REQUIRED"}')
    return Response(url,200,b'<button id="menuBtn">Menu</button>')

class CustomDomainProbeTests(unittest.TestCase):
    def test_urllib_401_error_is_the_expected_protected_response(self):
        def protected(request,timeout):
            if request.full_url.endswith('/api/admin_opportunities'):
                raise HTTPError(request.full_url,401,'Unauthorized',{},io.BytesIO(b'{"status":"AUTHENTICATION_REQUIRED"}'))
            return opener(request,timeout)
        self.assertTrue(verify(protected)['verified'])
    def test_https_home_health_and_private_boundary_are_all_required(self):
        self.assertTrue(verify(opener)['verified'])
        for path in ('/healthz','/api/admin_opportunities','/'):
            def bad(request,timeout):
                if request.full_url=='https://'+DOMAIN+path:return Response(request.full_url,200,b'unexpected')
                return opener(request,timeout)
            self.assertFalse(verify(bad)['verified'])
    def test_cross_domain_redirect_and_tls_errors_never_verify(self):
        def redirected(request,timeout):
            r=opener(request,timeout);r.url='https://other.example/';return r
        self.assertFalse(verify(redirected)['verified'])
        def unavailable(request,timeout):raise URLError('TLS unavailable')
        self.assertFalse(verify(unavailable)['verified'])
