"""Read-only official TED Search API check of a single publication number.

Never returns counterparty data or claims the XML, annex or revision is verified.
"""
import json
import re
import sys
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlsplit

ENDPOINT = "https://api.ted.europa.eu/v3/notices/search"
NOTICE = re.compile(r"^[0-9]{1,8}-[0-9]{4}$")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("ted_search_redirect_blocked")


def official_xml_links(notice, number):
    """Inspect TED-advertised links only; never dereference or accept bytes."""
    found=set()
    stack=[notice]
    for _ in range(150):
        if not stack:
            break
        node=stack.pop()
        if isinstance(node,dict):
            stack.extend(list(node.values())[:40])
        elif isinstance(node,list):
            stack.extend(node[:40])
        elif isinstance(node,str) and len(node)<=1000:
            url=urlsplit(node)
            if (url.scheme=="https" and url.hostname=="ted.europa.eu"
                and url.username is None and url.password is None
                and url.port in (None,443)
                and url.path.endswith("/notice/"+number+"/xml")):
                found.add(node)
    return len(found)


def search(number: str, fetcher=None):
    if not isinstance(number,str) or not NOTICE.fullmatch(number):
        raise ValueError("invalid_notice_number")
    body={"query":f"publication-number = ({number})",
          "fields":["publication-number","publication-date"],"page":1,"limit":5}
    if fetcher is None:
        def fetcher(payload):
            data=json.dumps(payload,separators=(",",":")).encode("utf-8")
            req=Request(ENDPOINT,data=data,method="POST",
                headers={"Content-Type":"application/json","Accept":"application/json"})
            with build_opener(NoRedirect()).open(req,timeout=25) as response:
                if response.geturl()!=ENDPOINT:
                    raise ValueError("ted_search_origin_changed")
                raw=response.read(512*1024+1)
            if len(raw)>512*1024:
                raise ValueError("ted_search_response_too_large")
            return json.loads(raw)
    result=fetcher(body)
    if not isinstance(result,dict) or result.get("timedOut") is True:
        raise ValueError("ted_search_response_unverified")
    notices=result.get("notices")
    if not isinstance(notices,list) or len(notices)>5:
        raise ValueError("ted_search_response_unverified")
    exact=[x for x in notices if isinstance(x,dict) and x.get("publication-number")==number]
    if len(exact)>1:
        raise ValueError("ted_search_duplicate_notice")
    advertised=official_xml_links(exact[0],number) if exact else 0
    return {"queried_publication":number,"official_search_endpoint":ENDPOINT,
            "matching_records":len(exact),
            "metadata_match_only":bool(exact),
            "official_xml_download_links_advertised":advertised,
            "official_xml_bytes_verified":False,
            "annexes_verified":False,
            "commercial_acceptance":False}


def main():
    from urllib.error import HTTPError, URLError
    try:
        print(json.dumps(search(sys.argv[1]),sort_keys=True))
    except (ValueError,IndexError,HTTPError,URLError,TimeoutError) as exc:
        if isinstance(exc,HTTPError):
            code=f"http_{exc.code}"
        elif isinstance(exc,URLError):
            code="network_unreachable"
        elif isinstance(exc,ValueError) and str(exc) in {
            "ted_search_redirect_blocked","ted_search_origin_changed",
            "ted_search_response_too_large","ted_search_response_unverified",
            "ted_search_duplicate_notice","invalid_notice_number"}:
            code=str(exc)
        else:
            code=type(exc).__name__
        raise SystemExit("TED_SEARCH_PROBE_BLOCKED "+code)


if __name__=="__main__":
    main()
