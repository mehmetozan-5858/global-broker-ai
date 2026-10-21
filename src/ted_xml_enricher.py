from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from src import document_parser
from src.ted_search_fields import notice_context
from src.notice_fact_cache import process as process_fact_cache
from src.ted_xml_parser import extract_ted_contacts, is_xml_source, parse_ted_xml, extract_ted_lots, apply_ted_lots

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
        publication = str(item.get("publication-number") or "")
        if not re.fullmatch(r"[0-9]{1,8}-[0-9]{4}", publication):
            for candidate in urls:
                parsed = urllib.parse.urlparse(candidate)
                match = re.search(r"/notice/(?:-/detail/)?([0-9]{1,8}-[0-9]{4})(?:/|$)", parsed.path)
                if parsed.hostname == "ted.europa.eu" and match:
                    publication = match.group(1)
                    break
        if re.fullmatch(r"[0-9]{1,8}-[0-9]{4}", publication):
            return "https://ted.europa.eu/en/notice/" + publication + "/xml"
    return None


def _fallback_document(xml_url: str, item: dict, attempts: list):
    parsed = urllib.parse.urlparse(xml_url)
    match = re.search(r"/notice/([0-9]{1,8}-[0-9]{4})/xml$", parsed.path)
    if parsed.hostname != "ted.europa.eu" or not match:
        raise ValueError("ted_fallback_notice_identity_missing")
    publication = match.group(1)
    formats = [("html", "ted_html_download")]
    if (notice_context(item) or {}).get("call_for_tenders") is True:
        formats.append(("pdf", "ted_pdf_download"))
    last_error = None
    for suffix, kind in formats:
        url = urllib.parse.urlunparse(parsed._replace(path=parsed.path[:-3] + suffix, query="", fragment=""))
        attempt = {"url": url, "status": "pending", "source": kind}
        try:
            limit = document_parser.MAX_DOCUMENT_BYTES if suffix == "pdf" else document_parser.MAX_SOURCE_PAGE_BYTES
            data, content_type, final_url = document_parser._download(url, limit)
            if urllib.parse.urlparse(final_url).hostname != "ted.europa.eu":
                raise ValueError("ted_document_origin_changed")
            if suffix == "pdf":
                if not data.startswith(b"%PDF"):
                    raise ValueError("ted_pdf_download_not_pdf")
                if not re.search(r"/notice/(?:-/detail/)?" + re.escape(publication) + r"(?:/|$)", urllib.parse.urlparse(final_url).path):
                    raise ValueError("ted_pdf_notice_url_changed")
                text = document_parser._parse_pdf(data)
                attachments = []
            else:
                if "html" not in content_type and not data.lstrip().lower().startswith((b"<!doctype html", b"<html")):
                    raise ValueError("ted_html_download_not_html")
                text, attachments = document_parser._parse_html_page(data, final_url)
            identity_text = text[:1000] if suffix == "pdf" else text
            if not re.search(r"(?<![0-9])" + re.escape(publication) + r"(?![0-9])", identity_text) or len(text) < MIN_SOURCE_TEXT_CHARS:
                raise ValueError("ted_document_notice_identity_or_text_missing")
            return data, content_type, final_url, text, attachments, kind, attempt
        except Exception as error:
            last_error = error
            attempt.update({"status": "failed", "error": type(error).__name__ + ":" + str(error)[:180]})
            attempts.append(attempt)
    raise last_error or ValueError("ted_fallback_unavailable")


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
        try:
            data, content_type, final_url = document_parser._download(url, document_parser.MAX_SOURCE_PAGE_BYTES)
            if not is_xml_source(data, content_type, final_url):
                raise ValueError("ted_source_not_xml")
            text, attachments = parse_ted_xml(data, final_url)
            contacts = extract_ted_contacts(data)
            lots = extract_ted_lots(data)
            if len(text) < MIN_SOURCE_TEXT_CHARS:
                raise ValueError("insufficient_ted_xml_text")
            kind = "ted_xml"
        except Exception as xml_error:
            attempt.update({"status": "failed", "error": type(xml_error).__name__ + ":" + str(xml_error)[:180]})
            attempts.append(attempt)
            data, content_type, final_url, text, attachments, kind, attempt = _fallback_document(url, item, attempts)
            contacts, lots = {}, []

        if lots:
            apply_ted_lots(item, lots, final_url)
        existing = item.get("document_extracted_text")
        # A long generic page must not consume the entire extraction budget
        # before the identity-checked official document is included.
        parts = [text]
        if isinstance(existing, str) and existing.strip() and existing != text:
            parsed_attachment = any(
                isinstance(entry, dict) and entry.get("status") == "parsed"
                and entry.get("kind") in {"pdf", "docx"}
                and entry.get("source") in {"linked_document", "attachment"}
                for entry in attempts
            )
            parts = [existing, text] if parsed_attachment else [text, existing]
        existing_urls = {
            a.get("url") for a in attempts if isinstance(a, dict) and a.get("status") == "parsed"
        }
        attachment_parts: list[str] = []
        for attachment_url in attachments[:document_parser.MAX_DISCOVERED_ATTACHMENTS]:
            if attachment_url in existing_urls:
                continue
            document_parser._try_attachment(
                attachment_url, attempts, attachment_parts, discovered_from=final_url
            )
        # Newly discovered specifications have their own budget while being read.
        # Merge them before notice/page context so a full notice cannot hide them.
        merged = "\n\n".join(attachment_parts + parts)[:MAX_EXTRACTED_CHARS]
        item["document_extracted_text"] = merged

        # Structured TED touchpoint fields are stronger evidence than generic text
        # matching. Preserve an existing source-backed value and only fill gaps.
        for key in ("contact_email", "contact_phone", "contact_person", "buyer_website"):
            if contacts.get(key) and not item.get(key):
                item[key] = contacts[key]
        if contacts:
            item["ted_touchpoint_contact"] = {
                "source": "ted_xml_touchpoint",
                "email_present": bool(contacts.get("contact_email")),
                "phone_present": bool(contacts.get("contact_phone")),
                "person_present": bool(contacts.get("contact_person")),
                "website_present": bool(contacts.get("buyer_website")),
                "source_backed_only": True,
            }

        attempt.update({
            "status": "parsed",
            "kind": kind,
            "final_url": final_url,
            "content_type": content_type,
            "bytes": len(data),
            "extracted_chars": len(text),
            "discovered_attachments": len(attachments),
            "structured_contact_found": bool(contacts),
        })
        attempts.append(attempt)
        info.update({
            "status": "parsed",
            "source_backed_only": True,
            "parsed_count": sum(1 for x in attempts if isinstance(x, dict) and x.get("status") == "parsed"),
            "attempts": attempts,
            "text_chars": len(merged),
            "ted_xml_parsed": kind == "ted_xml",
            "ted_html_parsed": kind == "ted_html_download",
            "ted_pdf_parsed": kind == "ted_pdf_download",
            "ted_structured_contact_found": bool(contacts),
        })
        item["document_extraction"] = info
        return True
    except Exception as exc:
        if attempt not in attempts:
            attempt.update({"status": "failed", "error": type(exc).__name__ + ":" + str(exc)[:180]})
            attempts.append(attempt)
        info["attempts"] = attempts
        if not item.get("document_extracted_text"):
            info["status"] = "attempted_no_text"
        info["ted_xml_parsed"] = False
        info["ted_pdf_parsed"] = False
        item["document_extraction"] = info
        return False


def enrich_payload(payload: dict[str, Any]) -> dict[str, Any]:
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        return payload

    attempted = 0
    parsed = 0
    structured_contacts = 0
    html_parsed = 0
    pdf_parsed = 0
    lot_count = 0
    candidates = [item for item in opportunities if isinstance(item, dict) and _ted_xml_url(item)]
    attempted = len(candidates)
    with ThreadPoolExecutor(max_workers=min(4, document_parser.MAX_WORKERS)) as executor:
        results = list(executor.map(enrich_opportunity, candidates))
    for item, success in zip(candidates, results):
        if success:
            parsed += int(bool((item.get("document_extraction") or {}).get("ted_xml_parsed")))
            html_parsed += int(bool((item.get("document_extraction") or {}).get("ted_html_parsed")))
            pdf_parsed += int(bool((item.get("document_extraction") or {}).get("ted_pdf_parsed")))
            lot_count += len(item.get("ted_lots") or [])
            structured_contacts += int(bool((item.get("document_extraction") or {}).get("ted_structured_contact_found")))

    summary = payload.get("document_extraction")
    if not isinstance(summary, dict):
        summary = {}
    summary.update({
        "version": max(int(summary.get("version") or 0), 5),
        "mode": "public_source_pages_documents_ted_xml_html_pdf_and_touchpoints",
        "ted_xml_attempted": attempted,
        "ted_xml_parsed": parsed,
        "ted_html_parsed": html_parsed,
        "ted_pdf_parsed": pdf_parsed,
        "ted_structured_lots": lot_count,
        "ted_structured_contacts": structured_contacts,
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
    cache_path = path.parent / "notice-facts-cache.json"
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        cache = {}
    updated = process_fact_cache(payload.get("opportunities") or [], cache)
    temporary = cache_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(cache_path)
    payload["notice_fact_cache"] = updated["last_scan"]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = payload.get("document_extraction") or {}
    print(
        "TED_XML_SUMMARY "
        f"attempted={summary.get('ted_xml_attempted', 0)} "
        f"parsed={summary.get('ted_xml_parsed', 0)} "
        f"structured_contacts={summary.get('ted_structured_contacts', 0)}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
