"""Read-only official TED XML diagnostic; no private ingestion, no publication.

Usage: python -m src.ted_official_notice_probe 775258-2026
Only returns aggregate metadata and a SHA-256 fingerprint, not document text.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from xml.etree import ElementTree

from src.ted_xml_enricher import _verify_ted_redirect, MIN_SOURCE_TEXT_CHARS
from src.ted_xml_parser import parse_ted_xml, extract_ted_lots

NOTICE_ID = re.compile(r"^[0-9]{1,8}-[0-9]{4}$")
LIMIT = 8 * 1024 * 1024


class NoticeSafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _verify_ted_redirect(req.full_url, newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_official_xml(url: str):
    opener = build_opener(NoticeSafeRedirect())
    with opener.open(Request(url, headers={"User-Agent": "GlobalBroker-readonly-probe/1.0"}),
                     timeout=25) as response:
        final_url = response.geturl()
        _verify_ted_redirect(url, final_url)
        data = response.read(LIMIT + 1)
        if len(data) > LIMIT:
            raise ValueError("ted_xml_too_large")
        return data, response.headers.get("Content-Type", ""), final_url


def inspect_notice(number: str, *, fetcher=fetch_official_xml):
    if not isinstance(number, str) or not NOTICE_ID.fullmatch(number):
        raise ValueError("invalid_notice_number")
    url = f"https://ted.europa.eu/en/notice/{number}/xml"
    data, content_type, final_url = fetcher(url)
    _verify_ted_redirect(url, final_url)
    if not isinstance(data, bytes) or len(data) > LIMIT:
        raise ValueError("invalid_ted_source_bytes")
    if not isinstance(content_type, str) or "xml" not in content_type.lower():
        # Some official endpoints use application/octet-stream for XML files.
        if not data.lstrip().startswith(b"<?xml"):
            raise ValueError("ted_source_not_xml")
    root = ElementTree.fromstring(data)
    text = " ".join(t.strip() for t in root.itertext() if t and t.strip())
    # An official host and a parsed XML file do not by themselves establish
    # that the notice has the exact publication identity requested.
    has_identity = number in text or number in data.decode("utf-8", errors="replace")
    parsed_text, _ = parse_ted_xml(data, final_url)
    lots = extract_ted_lots(data)
    return {
        "requested_notice": number,
        "source_host": urlsplit(final_url).hostname,
        "downloaded_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "xml_readable": bool(len(parsed_text) >= MIN_SOURCE_TEXT_CHARS),
        "notice_identity_found": bool(has_identity),
        "structured_lot_count": len(lots),
        "annex_completeness_verified": False,
        "commercial_acceptance": False,
        "official_notice_gate_ready": bool(has_identity and len(parsed_text) >= MIN_SOURCE_TEXT_CHARS),
    }


def main():
    try:
        print(json.dumps(inspect_notice(sys.argv[1]), sort_keys=True))
    except (IndexError, ValueError, OSError, ElementTree.ParseError) as exc:
        # Never print downloaded content or third-party URL query parameters.
        raise SystemExit("TED_OFFICIAL_PROBE_BLOCKED " + type(exc).__name__)


if __name__ == "__main__":
    main()
