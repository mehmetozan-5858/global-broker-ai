"""Bounded official response diagnostics. Never log notice text, keys or cookies."""
import hashlib
import re
import urllib.error
import urllib.parse
import urllib.request
from xml.etree import ElementTree
from src import document_parser
from src.ted_xml_enricher import _verify_ted_redirect

LIMIT=262144
ACCEPT={'xml':'application/xml,text/xml;q=0.9,*/*;q=0.1','html':'text/html,application/xhtml+xml;q=0.9',
        'pdf':'application/pdf,*/*;q=0.1'}
ROOTS={'notice','contractnotice','contractawardnotice','priorinformationnotice','ted_export','html'}


def response_shape(data,content_type):
    prefix=data.lstrip()[:1024].lower()
    if not data:kind='empty'
    elif prefix.startswith(b'%pdf'):kind='pdf'
    elif prefix.startswith((b'<!doctype html',b'<html')):kind='html'
    elif prefix.startswith((b'{',b'[')):kind='json'
    elif prefix.startswith(b'<'):kind='xml'
    else:kind='other'
    root=None
    if kind in {'xml','html'}:
        try:
            tag=str(ElementTree.fromstring(data).tag).rsplit('}',1)[-1].lower()
            root=tag if tag in ROOTS else 'other-root'
        except ElementTree.ParseError:root='not-fully-parsed'
    challenge=any(marker in data[:65536].lower() for marker in (b'awswaf',b'captcha',b'challenge.js',b'verify you are human'))
    return {'body_kind':kind,'root_kind':root,'challenge_indicator':challenge,
            'sample_sha256':hashlib.sha256(data).hexdigest()}


def inspect_official_response(publication,fmt,opener=None):
    if not isinstance(publication,str) or not re.fullmatch(r'[0-9]{1,8}-[0-9]{4}',publication) or fmt not in ACCEPT:
        raise ValueError('invalid-official-probe-scope')
    url=f'https://ted.europa.eu/en/notice/{publication}/{fmt}'
    result={'publication':publication,'format':fmt,'accepted_as_notice':False}
    if not document_parser._public_http_url(url):
        return {**result,'error':'public-address-validation-failed'}
    try:
        request=urllib.request.Request(url,headers={'User-Agent':document_parser.USER_AGENT,'Accept':ACCEPT[fmt]})
        opener=opener or urllib.request.build_opener(document_parser._PublicRedirectHandler())
        with opener.open(request,timeout=document_parser.TIMEOUT_SECONDS) as response:
            final=response.geturl();parsed=urllib.parse.urlparse(final)
            if parsed.scheme!='https' or parsed.username or parsed.password or parsed.port not in (None,443):
                return {**result,'error':'invalid-final-origin'}
            try:_verify_ted_redirect(url,final)
            except ValueError:return {**result,'error':'notice-redirect-mismatch'}
            data=response.read(LIMIT+1);truncated=len(data)>LIMIT;sample=data[:LIMIT]
            mime=(response.headers.get('Content-Type') or '').split(';')[0].strip().lower()
            safe_mime=mime if mime in {'application/xml','text/xml','application/pdf','text/html','application/xhtml+xml','application/json','application/octet-stream'} else 'other'
            status=getattr(response,'status',None)
            return {**result,'http_status':status if type(status) is int and 100<=status<=599 else None,
                    'content_type':safe_mime,'sample_bytes':len(sample),'sample_truncated':truncated,
                    **response_shape(sample,safe_mime)}
    except urllib.error.HTTPError as error:return {**result,'http_status':error.code,'error':'http-error'}
    except Exception:return {**result,'error':'network-or-response-error'}
