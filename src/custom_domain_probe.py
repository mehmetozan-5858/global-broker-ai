"""Current HTTPS and auth-boundary proof for the existing Broker subdomain."""
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DOMAIN = 'broker.aivisibilityworks.com'


def verify(opener=urlopen):
    result={'domain':DOMAIN,'https_home_ok':False,'health_ok':False,'admin_auth_guard_ok':False}
    checks=(('/',200,b'menuBtn','https_home_ok'),('/healthz',204,b'','health_ok'),
            ('/api/admin_opportunities',401,b'AUTHENTICATION_REQUIRED','admin_auth_guard_ok'))
    for path,status,marker,key in checks:
        try:
            try:
                response=opener(Request('https://'+DOMAIN+path,headers={'User-Agent':'GlobalBroker-DomainVerification/1.0'}),timeout=8)
            except HTTPError as error:
                response=error
            with response:
                final=urlparse(response.geturl())
                body=response.read(262144)
                result[key]=(response.status==status and final.scheme=='https'
                             and final.hostname==DOMAIN and marker in body)
        except (URLError,TimeoutError,OSError,ValueError):
            result[key]=False
    result['verified']=all(result[key] for *_,key in checks)
    return result
