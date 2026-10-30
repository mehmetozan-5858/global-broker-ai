from __future__ import annotations

import json
import os
import time
import threading
import urllib.error
from collections import Counter
import re
from concurrent.futures import ThreadPoolExecutor
import sys
import urllib.parse
from pathlib import Path
from xml.etree import ElementTree
from typing import Any

from src import document_parser
from src.specification import _safe_omitted_attachment_count as _safe_previous_omissions
from src.ted_search_fields import notice_context
from src.notice_fact_cache import process as process_fact_cache
from src.ted_xml_parser import extract_ted_contacts, is_xml_source, parse_ted_xml, extract_ted_lots, apply_ted_lots

MIN_SOURCE_TEXT_CHARS = 160
MAX_EXTRACTED_CHARS = document_parser.MAX_EXTRACTED_CHARS


# A single gate shares pacing across all TED document workers.
_TED_RATE_LOCK = threading.Lock()
_TED_NEXT_REQUEST = 0.0
_TED_MIN_INTERVAL = 1.0


def _download_ted(url: str, limit: int):
    global _TED_NEXT_REQUEST
    for retry in range(3):
        try:
            with _TED_RATE_LOCK:
                delay = max(0.0, _TED_NEXT_REQUEST - time.monotonic())
                if delay:
                    time.sleep(delay)
                _TED_NEXT_REQUEST = time.monotonic() + _TED_MIN_INTERVAL
                # Hold the gate through the response: no overlapping TED
                # document fetches, even when the pipeline has four workers.
                return document_parser._download(url, limit)
        except urllib.error.HTTPError as error:
            if error.code != 429 or retry == 2:
                raise
            raw = (error.headers.get("Retry-After") if error.headers else "") or ""
            # Cap untrusted server delays and total retry budget; never log body.
            wait = min(8.0, max(float(2 ** retry), float(raw))) if raw.isdecimal() else float(2 ** retry)
            time.sleep(wait)
    raise ValueError("ted_retry_exhausted")


def _api_xml_link(item: dict[str, Any]) -> str | None:
    links = item.get("links")
    if not isinstance(links, dict):
        return None
    xml = links.get("xml")
    if not isinstance(xml, dict):
        return None
    url = xml.get("MUL")
    if not isinstance(url, str):
        return None
    parsed = urllib.parse.urlparse(url)
    expected = str(item.get("publication-number") or "")
    if parsed.scheme != "https" or parsed.hostname != "ted.europa.eu":
        return None
    identity = _ted_notice_id(url)
    if not identity or (expected and identity != expected):
        return None
    if not parsed.path.lower().endswith("/xml"):
        return None
    return url


TED_NOTICE_ID_RE = re.compile(r"/notice/(?:-/detail/)?([0-9]{1,8}-[0-9]{4})(?:/|$)")


def _ted_notice_id(url: str) -> str | None:
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname != "ted.europa.eu":
        return None
    match = TED_NOTICE_ID_RE.search(parsed.path)
    return match.group(1) if match else None


def _verify_ted_redirect(requested_url: str, final_url: str) -> None:
    """Reject off-site or cross-notice redirects before trusting any document."""
    if urllib.parse.urlparse(final_url).hostname != "ted.europa.eu":
        raise ValueError("ted_document_origin_changed")
    requested_id = _ted_notice_id(requested_url)
    final_id = _ted_notice_id(final_url)
    if requested_id and final_id != requested_id:
        # A generic TED landing page (no notice ID) is not evidence of
        # the requested notice, even when the redirect stays on TED.
        raise ValueError("ted_document_notice_redirect_mismatch")


def _api_pdf_link(item: dict[str, Any], publication: str) -> str | None:
    links = item.get("links")
    pdfs = links.get("pdf") if isinstance(links, dict) else None
    if not isinstance(pdfs, dict):
        return None
    for lang in ("ENG", "MUL"):
        url = pdfs.get(lang)
        if not isinstance(url, str):
            continue
        parsed = urllib.parse.urlparse(url)
        if (parsed.scheme == "https" and parsed.hostname == "ted.europa.eu"
                and parsed.path.lower().endswith("/pdf")
                and _ted_notice_id(url) == publication):
            return url
    return None


def _ted_xml_url(item: dict[str, Any]) -> str | None:
    source = str(item.get("source") or item.get("source_name") or "").upper()
    api_link = _api_xml_link(item)
    if api_link:
        return api_link
    urls = document_parser._all_urls(item)
    expected_id = str(item.get("publication-number") or "")
    if not re.fullmatch(r"[0-9]{1,8}-[0-9]{4}", expected_id):
        expected_id = ""
    for url in urls:
        try:
            parsed = urllib.parse.urlparse(url)
            path = parsed.path.lower().rstrip("/")
            host = (parsed.hostname or "").lower()
        except (TypeError, ValueError):
            continue
        if host == "ted.europa.eu" and (path.endswith("/xml") or path.endswith(".xml")):
            link_id = _ted_notice_id(url)
            # Never select an unidentifiable XML URL or a different notice.
            # Otherwise the document could be attributed to the wrong tender.
            if not link_id or (expected_id and link_id != expected_id):
                continue
            return url
    if source == "TED":
        publication = str(item.get("publication-number") or "")
        if not re.fullmatch(r"[0-9]{1,8}-[0-9]{4}", publication):
            for candidate in urls:
                try:
                    parsed = urllib.parse.urlparse(candidate)
                    host = parsed.hostname
                except (TypeError, ValueError):
                    continue
                match = re.search(r"/notice/(?:-/detail/)?([0-9]{1,8}-[0-9]{4})(?:/|$)", parsed.path)
                if host == "ted.europa.eu" and match:
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
    formats = []  # HTML shells are not accepted as official notice evidence.
    if (notice_context(item) or {}).get("call_for_tenders") is True:
        formats.append(("pdf", "ted_pdf_download"))
    last_error = None
    for suffix, kind in formats:
        url = (_api_pdf_link(item, publication) if suffix == "pdf" else None) or urllib.parse.urlunparse(parsed._replace(path=parsed.path[:-3] + suffix, query="", fragment=""))
        attempt = {"url": url, "status": "pending", "source": kind}
        try:
            limit = document_parser.MAX_DOCUMENT_BYTES if suffix == "pdf" else document_parser.MAX_SOURCE_PAGE_BYTES
            data, content_type, final_url = document_parser._download(url, limit)
            _verify_ted_redirect(url, final_url)
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


def enrich_opportunity(item: dict[str, Any], *, bulk_notice=None) -> bool:
    url = _ted_xml_url(item)
    if not url:
        return False

    info = item.get("document_extraction")
    if not isinstance(info, dict):
        info = {}
    # Imported or cached extraction metadata is untrusted. A string/dict
    # must never become an iterable of bogus attempts or crash enrichment.
    previous_attempts = info.get("attempts")
    attempts = [entry for entry in previous_attempts if isinstance(entry, dict)] if isinstance(previous_attempts, list) else []
    attempt: dict[str, Any] = {"url": url, "status": "pending", "source": "ted_xml"}

    try:
        try:
            if bulk_notice is None:
                data, content_type, final_url = _download_ted(url, document_parser.MAX_SOURCE_PAGE_BYTES)
            else:
                data, content_type, final_url = bulk_notice.verified_payload(item.get('publication-number'))
                from src.ted_bulk import daily_url
                attempt.update({'source_package_url': daily_url(bulk_notice.edition),
                                'source_package_sha256': bulk_notice.package_sha256,
                                'source_channel': 'official_daily_xml_package'})
            _verify_ted_redirect(url, final_url)
            if not is_xml_source(data, content_type, final_url):
                raise ValueError("ted_source_not_xml")
            text, attachments = parse_ted_xml(data, final_url)
            # The XML parser itself caps text before the final merge.
            xml_parts = [" ".join(part.split()) for part in ElementTree.fromstring(data).itertext() if part]
            xml_length = len(" ".join(part for part in xml_parts if part))
            xml_omitted_chars = max(0, xml_length - MAX_EXTRACTED_CHARS)
            contacts = extract_ted_contacts(data)
            lots = extract_ted_lots(data)
            if len(text) < MIN_SOURCE_TEXT_CHARS:
                raise ValueError("insufficient_ted_xml_text")
            kind = "ted_xml"
        except Exception as xml_error:
            if bulk_notice is not None:
                # A wrong/corrupt package must never become a successful fallback.
                raise
            attempt.update({"status": "failed", "error": type(xml_error).__name__ + ":" + str(xml_error)[:180]})
            attempts.append(attempt)
            data, content_type, final_url, text, attachments, kind, attempt = _fallback_document(url, item, attempts)
            contacts, lots = {}, []
            xml_omitted_chars = 0

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
        selected_attachments = attachments[:document_parser.MAX_DISCOVERED_ATTACHMENTS]
        for attachment_url in selected_attachments:
            if attachment_url in existing_urls:
                continue
            document_parser._try_attachment(
                attachment_url, attempts, attachment_parts, discovered_from=final_url
            )
        # Newly discovered specifications have their own budget while being read.
        # Merge them before notice/page context so a full notice cannot hide them.
        full_text = "\n\n".join(attachment_parts + parts)
        merged = full_text[:MAX_EXTRACTED_CHARS]
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
            "attachment_candidates_omitted": max(0, len(attachments) - len(selected_attachments)),
            "structured_contact_found": bool(contacts),
        })
        attempts.append(attempt)
        info.update({
            "status": "parsed",
            "source_backed_only": True,
            "parsed_count": sum(1 for x in attempts if isinstance(x, dict) and x.get("status") == "parsed" and x.get("source") != "document_index"),
            "attempts": attempts,
            "text_chars": len(merged),
            "text_truncated": info.get('text_truncated') is True or len(full_text) > MAX_EXTRACTED_CHARS or xml_omitted_chars > 0,
            "omitted_chars": (_safe_previous_omissions(info.get('omitted_chars'))
                              + max(0, len(full_text) - MAX_EXTRACTED_CHARS) + xml_omitted_chars),
            "attachment_candidates_omitted": max(
                _safe_previous_omissions(info.get('attachment_candidates_omitted')),
                len(attachments) - len(selected_attachments)),
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


# Fixed classification avoids storing exception text, arbitrary URLs or tokens in
# aggregate scan diagnostics. An unrecognized error stays explicitly unknown.
TED_FAILURE_MARKERS = (
    "ted_waf_challenge",
    "ted_source_not_xml",
    "ted_xml_notice_root_missing",
    "ted_document_notice_redirect_mismatch",
    "ted_document_origin_changed",
    "insufficient_ted_xml_text",
    "ted_document_notice_identity_or_text_missing",
    "ted_pdf_download_not_pdf",
    "ted_html_download_not_html",
    "unexpected_world_bank_api_origin",
)


def _failure_category(attempt: dict[str, Any]) -> str:
    error = attempt.get("error")
    if not isinstance(error, str):
        return "unknown"
    for marker in TED_FAILURE_MARKERS:
        if marker in error:
            return marker
    return "other"


def enrich_payload(payload: dict[str, Any], *, bulk_enabled: bool = False) -> dict[str, Any]:
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        return payload

    attempted = 0
    parsed = 0
    structured_contacts = 0
    html_parsed = 0
    pdf_parsed = 0
    lot_count = 0
    failure_counts: Counter[str] = Counter()
    failure_stages: dict[str, Counter[str]] = {
        "ted_xml": Counter(),
        "ted_html_download": Counter(),
        "ted_pdf_download": Counter(),
    }
    candidates = [item for item in opportunities if isinstance(item, dict) and _ted_xml_url(item)]
    attempted = len(candidates)
    with ThreadPoolExecutor(max_workers=min(4, document_parser.MAX_WORKERS)) as executor:
        results = list(executor.map(enrich_opportunity, candidates))
    bulk_summary = None
    if bulk_enabled is True:
        from src.ted_bulk_fallback import apply_bulk_fallback
        bulk_summary = apply_bulk_fallback(candidates, results)
    for item, success in zip(candidates, results):
        extraction = item.get("document_extraction")
        attempts = extraction.get("attempts") if isinstance(extraction, dict) else []
        if not isinstance(attempts, list):
            attempts = []
        if not success:
            failed = [entry for entry in attempts if isinstance(entry, dict)
                      and entry.get("status") == "failed"
                      and entry.get("source") in {"ted_xml", "ted_html_download", "ted_pdf_download"}]
            category = _failure_category(failed[-1]) if failed else "unknown"
            failure_counts[category] += 1
            # Preserve all attempted formats: a PDF fallback failure must not
            # hide the XML or HTML error that preceded it.
            for entry in failed:
                failure_stages[entry["source"]][_failure_category(entry)] += 1
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
        "ted_document_failures": dict(sorted(failure_counts.items())),
        "ted_document_failure_stages": {
            key: dict(sorted(counter.items()))
            for key, counter in failure_stages.items()
        },
        "ted_document_failed_notices": sum(failure_counts.values()),
        "parsed_opportunities": sum(
            1
            for item in opportunities
            if isinstance(item, dict)
            and int(((item.get("document_extraction") or {}).get("parsed_count") or 0)) > 0
        ),
    })
    payload["document_extraction"] = summary
    if bulk_summary is not None:
        summary['ted_bulk_fallback'] = bulk_summary
    else:
        summary.pop('ted_bulk_fallback', None)
    return payload


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.ted_xml_enricher <json-file>")
    path = Path(sys.argv[1])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload = enrich_payload(payload, bulk_enabled=os.environ.get('GB_TED_BULK_FALLBACK') == '1')
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
        f"structured_contacts={summary.get('ted_structured_contacts', 0)} "
        f"failed={summary.get('ted_document_failed_notices', 0)} "
        f"reasons={json.dumps(summary.get('ted_document_failures', {}), sort_keys=True)} "
        f"stages={json.dumps(summary.get('ted_document_failure_stages', {}), sort_keys=True)}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
