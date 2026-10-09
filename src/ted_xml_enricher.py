from __future__ import annotations

import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from src import document_parser
from src.ted_xml_parser import is_xml_source, parse_ted_xml

MIN_SOURCE_TEXT_CHARS = 160
MAX_EXTRACTED_CHARS = document_parser.MAX_EXTRACTED_CHARS


def _ted_xml_url(item: dict[str, Any]) -> str | None:
    source = str(item.get("source") or item.get("source_name") or "").upper()
    urls = document_parser._all_urls(item)
    for url in urls:
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.lower().rstrip("/")
        host = (parsed.hostname or "").lower()
        if host == "ted.europa.eu" and (path.endswith("/xml") or path.endswith(".xml")):
            return url
    if source == "TED":
        return next((u for u in urls if (urllib.parse.urlparse(u).hostname or "").lower() == "ted.europa.eu"), None)
    return None


def enrich_opportunity(item: dict[str, Any]) -> bool:
    url = _ted_xml_url(item)
    if not url:
        return False

    info = item.get("document_extraction")
    if not isinstance(info, dict):
        info = {}
    attempts = list(info.get("attempts") or [])
    attempt: dict[str, Any] = {"url": url, "status": "pending", "source": "ted_xml"}

    try:
        data, content_type, final_url = document_parser._download(url, document_parser.MAX_SOURCE_PAGE_BYTES)
        if not is_xml_source(data, content_type, final_url):
            raise ValueError("ted_source_not_xml")
        text, attachments = parse_ted_xml(data, final_url)
        if len(text) < MIN_SOURCE_TEXT_CHARS:
            raise ValueError("insufficient_ted_xml_text")

        existing = item.get("document_extracted_text")
        parts = [existing] if isinstance(existing, str) and existing.strip() else []
        parts.append(text)
        merged = "\n\n".join(parts)[:MAX_EXTRACTED_CHARS]
        item["document_extracted_text"] = merged
        attempt.update({
            "status": "parsed",
            "kind": "ted_xml",
            "final_url": final_url,
            "content_type": content_type,
            "bytes": len(data),
            "extracted_chars": len(text),
            "discovered_attachments": len(attachments),
        })
        attempts.append(attempt)
        info.update({
            "status": "parsed",
            "source_backed_only": True,
            "parsed_count": sum(1 for x in attempts if isinstance(x, dict) and x.get("status") == "parsed"),
            "attempts": attempts,
            "text_chars": len(merged),
            "ted_xml_parsed": True,
        })
        item["document_extraction"] = info
        return True
    except Exception as exc:
        attempt.update({"status": "failed", "error": type(exc).__name__ + ":" + str(exc)[:180]})
        attempts.append(attempt)
        info["attempts"] = attempts
        if not item.get("document_extracted_text"):
            info["status"] = "attempted_no_text"
        info["ted_xml_parsed"] = False
        item["document_extraction"] = info
        return False


def enrich_payload(payload: dict[str, Any]) -> dict[str, Any]:
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        return payload

    attempted = 0
    parsed = 0
    for item in opportunities:
        if not isinstance(item, dict) or not _ted_xml_url(item):
            continue
        attempted += 1
        if enrich_opportunity(item):
            parsed += 1

    summary = payload.get("document_extraction")
    if not isinstance(summary, dict):
        summary = {}
    summary.update({
        "version": max(int(summary.get("version") or 0), 3),
        "mode": "public_source_pages_documents_and_ted_xml",
        "ted_xml_attempted": attempted,
        "ted_xml_parsed": parsed,
        "parsed_opportunities": sum(
            1
            for item in opportunities
            if isinstance(item, dict)
            and int(((item.get("document_extraction") or {}).get("parsed_count") or 0)) > 0
        ),
    })
    payload["document_extraction"] = summary
    return payload


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.ted_xml_enricher <json-file>")
    path = Path(sys.argv[1])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload = enrich_payload(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = payload.get("document_extraction") or {}
    print(
        "TED_XML_SUMMARY "
        f"attempted={summary.get('ted_xml_attempted', 0)} "
        f"parsed={summary.get('ted_xml_parsed', 0)}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
