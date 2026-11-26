"""Read-only official TED signed PDF transport probe.

Transport-level PDF bytes are NOT a verified notice revision or complete annex.
Never writes to production or stores document content.
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
from urllib.request import Request, build_opener
from urllib.error import HTTPError, URLError

from src.ted_official_notice_probe import NoticeSafeRedirect
from src.ted_xml_enricher import _verify_ted_redirect

LIMIT=16*1024*1024
NOTICE=re.compile(r"^[0-9]{1,8}-[0-9]{4}$")


def fetch_signed_pdf(url):
    with build_opener(NoticeSafeRedirect()).open(
        Request(url,headers={"User-Agent":"GlobalBroker-readonly-probe/1.0"}),
        timeout=25,
    ) as response:
        final=response.geturl()
        _verify_ted_redirect(url,final)
        return response.read(LIMIT+1),final


def probe_pdf(number,fetcher=fetch_signed_pdf):
    if not isinstance(number,str) or not NOTICE.fullmatch(number):
        raise ValueError("invalid_notice_number")
    url=f"https://ted.europa.eu/en/notice/{number}/pdfs"
    data,final=fetcher(url)
    _verify_ted_redirect(url,final)
    if len(data)>LIMIT:
        raise ValueError("ted_signed_pdf_too_large")
    if not data.startswith(b"%PDF-"):
        raise ValueError("ted_signed_pdf_not_pdf")
    if len(data)<64:
        raise ValueError("ted_signed_pdf_too_short")
    return {"requested_notice":number,"signed_pdf_transport":True,
       "downloaded_bytes":len(data),"sha256":hashlib.sha256(data).hexdigest(),
       "notice_identity_verified":False,"pdf_visual_review_verified":False,
       "annexes_verified":False,"revision_verified":False,
       "commercial_acceptance":False}


def main():
    try:
        print(json.dumps(probe_pdf(sys.argv[1]),sort_keys=True))
    except (ValueError,IndexError,HTTPError,URLError,TimeoutError) as e:
        code="ted_http_"+str(e.code) if isinstance(e,HTTPError) else (
            "ted_network_unreachable" if isinstance(e,URLError) else
            str(e) if isinstance(e,ValueError) and str(e) in {
             "invalid_notice_number","ted_signed_pdf_not_pdf",
             "ted_signed_pdf_too_short","ted_signed_pdf_too_large",
             "ted_document_origin_changed","ted_document_notice_redirect_mismatch"
            } else type(e).__name__)
        raise SystemExit("TED_PDF_PROBE_BLOCKED "+code)


if __name__=="__main__":
    main()
