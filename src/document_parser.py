from __future__ import annotations

import io
import hashlib
import ipaddress
import json
import re
import socket
import sys
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from src.document_links import is_attachment_url, select as select_attachments, filename as attachment_filename, priority as attachment_priority, EXTENSIONS
from src.source_navigation import document_indexes, same_origin
from src.technical_requirements import extract_document as extract_requirements
from xml.etree import ElementTree

MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
MAX_SOURCE_PAGE_BYTES = 2 * 1024 * 1024
MAX_EXTRACTED_CHARS = 40000
MAX_PDF_PAGES = 80
MAX_SOURCE_PAGES_PER_OPPORTUNITY = 1
MAX_DISCOVERED_ATTACHMENTS = 3
MAX_DOCUMENT_INDEX_PAGES = 1
MAX_WORKERS = 8
TIMEOUT_SECONDS = 12
USER_AGENT = "GlobalBrokerAI/1.0 tender-document-reader"

URL_KEYS = [
    "document_url",
    "documents_url",
    "tender_url",
    "notice_url",
    "source_url",
    "official_url",
    "official_links",
    "links",
]
ATTACHMENT_EXTENSIONS = EXTENSIONS


def _collect_urls(value: Any) -> list[str]:
    out: list[str] = []
    if isinstance(value, str):
        out.extend(re.findall(r"https?://[^\s\]\[\)\(\"'<>]+", value))
    elif isinstance(value, list):
        for entry in value:
            out.extend(_collect_urls(entry))
    elif isinstance(value, dict):
        for entry in value.values():
            out.extend(_collect_urls(entry))
    seen: set[str] = set()
    clean: list[str] = []
    for url in out:
        url = url.rstrip(".,;)")
        if url not in seen:
            seen.add(url)
            clean.append(url)
    return clean


def _all_urls(item: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for key in URL_KEYS:
        urls.extend(_collect_urls(item.get(key)))
    seen: set[str] = set()
    out: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def _is_attachment_url(url: str) -> bool:
    return is_attachment_url(url)


def _candidate_urls(item: dict[str, Any]) -> list[str]:
    return select_attachments([(url, "") for url in _all_urls(item) if _is_attachment_url(url)], 6)


def _source_page_urls(item: dict[str, Any]) -> list[str]:
    return [url for url in _all_urls(item) if not _is_attachment_url(url)][:MAX_SOURCE_PAGES_PER_OPPORTUNITY]


def _public_http_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return False
        host = parsed.hostname.lower()
        if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
            return False
        try:
            addresses = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
        except OSError:
            return False
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                return False
        return True
    except Exception:
        return False


class _PublicRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _public_http_url(newurl):
            raise ValueError("redirected_to_non_public_url")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _download(url: str, max_bytes: int = MAX_DOCUMENT_BYTES) -> tuple[bytes, str, str]:
    if not _public_http_url(url):
        raise ValueError("non_public_or_unresolvable_url")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,*/*;q=0.5",
        },
    )
    with urllib.request.build_opener(_PublicRedirectHandler()).open(request, timeout=TIMEOUT_SECONDS) as response:
        final_url = response.geturl()
        if not _public_http_url(final_url):
            raise ValueError("redirected_to_non_public_url")
        content_type = (response.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > max_bytes:
            raise ValueError("document_too_large")
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError("document_too_large")
        return data, content_type, final_url


def _normalize_lines(text: str) -> str:
    # Preserve source field boundaries; flattening them can turn multiple
    # labelled values into one apparently unambiguous commercial fact.
    return "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())


def _parse_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise RuntimeError("pypdf_unavailable") from exc
    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    total = 0
    for page in reader.pages[:MAX_PDF_PAGES]:
        raw = page.extract_text() or ""
        text = _normalize_lines(raw)
        if not text:
            continue
        remaining = MAX_EXTRACTED_CHARS - total
        if remaining <= 0:
            break
        parts.append(text[:remaining])
        total += min(len(text), remaining)
    return "\n".join(parts).strip()


def _parse_docx(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
        matches = [m for m in members if m.filename == 'word/document.xml']
        if len(members) > 1024 or len(matches) != 1 or matches[0].file_size > MAX_DOCUMENT_BYTES or matches[0].flag_bits & 1:
            raise ValueError('invalid_docx_xml_or_archive_limit')
        with archive.open(matches[0]) as stream:
            xml = stream.read(MAX_DOCUMENT_BYTES + 1)
        if len(xml) > MAX_DOCUMENT_BYTES or re.search(br'<!\s*(?:DOCTYPE|ENTITY)', xml, re.I):
            raise ValueError('invalid_docx_xml_or_archive_limit')
    root = ElementTree.fromstring(xml)
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs = []
    for paragraph in root.iter(namespace + "p"):
        parts = []
        for node in paragraph.iter():
            if node.tag == namespace + "t":
                parts.append(node.text or "")
            elif node.tag in {namespace + "br", namespace + "cr"}:
                parts.append("\n")
            elif node.tag == namespace + "tab":
                parts.append(" ")
        paragraphs.append("".join(parts))
    return _normalize_lines("\n".join(paragraphs))[:MAX_EXTRACTED_CHARS]


def _parse_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return _normalize_lines(data.decode(encoding))[:MAX_EXTRACTED_CHARS]
        except UnicodeDecodeError:
            continue
    return ""


class _TenderHTMLParser(HTMLParser):
    BLOCK_TAGS = {"p", "div", "section", "article", "header", "footer", "main",
                  "h1", "h2", "h3", "h4", "h5", "h6", "li", "ul", "ol",
                  "table", "tr", "td", "th", "dl", "dt", "dd", "blockquote",
                  "pre", "br", "hr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.hrefs: list[str] = []
        self.links: list[dict[str, str]] = []
        self._active_link: dict[str, str] | None = None
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            return
        if not self._skip_depth and tag in self.BLOCK_TAGS:
            self.text_parts.append("\n")
        if tag == "a" and not self._skip_depth:
            attributes = {key.lower(): value for key, value in attrs}
            href = attributes.get("href")
            self._active_link = None
            if href:
                self.hrefs.append(href)
                self._active_link = {"href": href, "label": attributes.get("title") or ""}
                self.links.append(self._active_link)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a":
            self._active_link = None
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if not self._skip_depth and tag.lower() in self.BLOCK_TAGS:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.text_parts.append(data)
            if self._active_link is not None:
                self._active_link["label"] = (self._active_link["label"] + " " + data)[:1000]


def _decode_html(data: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "gb18030", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def _parse_html_page(data: bytes, base_url: str, attachment_labels: dict[str, str] | None = None, indexes: list[str] | None = None, coverage: dict | None = None) -> tuple[str, list[str]]:
    from src.source_access_barrier import html_access_barrier
    barrier = html_access_barrier(data, base_url)
    if barrier:
        raise ValueError(barrier)
    parser = _TenderHTMLParser()
    parser.feed(_decode_html(data))
    if coverage is not None:
        from src.document_coverage import observe
        observe(parser.links, base_url, coverage)
    visible = _normalize_lines("".join(parser.text_parts))[:MAX_EXTRACTED_CHARS]
    if indexes is not None:
        indexes.extend(url for url in document_indexes(parser.links, base_url) if url not in indexes)
    candidates: list[tuple[str, str]] = []
    for link in parser.links:
        try:
            absolute = urllib.parse.urljoin(base_url, link["href"])
        except ValueError:
            continue
        if _is_attachment_url(absolute):
            candidates.append((absolute, link["label"]))
            if attachment_labels is not None and (absolute not in attachment_labels or
                    attachment_priority(absolute, link["label"]) < attachment_priority(absolute, attachment_labels[absolute])):
                attachment_labels[absolute] = link["label"]
    return visible, select_attachments(candidates, MAX_DISCOVERED_ATTACHMENTS)


def _parse(data: bytes, content_type: str, url: str) -> tuple[str, str]:
    path = (attachment_filename(url) or urllib.parse.urlparse(url).path).lower()
    if "html" in content_type or data.lstrip().lower().startswith((b"<!doctype html", b"<html")):
        raise ValueError("attachment_is_html")
    if content_type == "application/pdf" or path.endswith(".pdf") or data.startswith(b"%PDF"):
        return _parse_pdf(data), "pdf"
    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or path.endswith(".docx"):
        return _parse_docx(data), "docx"
    if content_type.startswith("text/") or path.endswith(".txt"):
        return _parse_text(data), "text"
    raise ValueError("unsupported_document_type")


def _append_text(parts: list[str], value: str) -> None:
    if not value:
        return
    used = sum(len(x) for x in parts)
    remaining = MAX_EXTRACTED_CHARS - used
    if remaining > 0:
        parts.append(value[:remaining])


def _try_attachment(url: str, attempts: list[dict[str, Any]], extracted_parts: list[str], discovered_from: str | None = None) -> None:
    attempt: dict[str, Any] = {"url": url, "status": "pending", "source": "attachment"}
    if discovered_from:
        attempt["discovered_from"] = discovered_from
    try:
        data, content_type, final_url = _download(url)
        document_text, kind = _parse(data, content_type, final_url)
        if len(document_text) < 80:
            raise ValueError("insufficient_extractable_text")
        _append_text(extracted_parts, document_text)
        attempt.update({
            "status": "parsed",
            "kind": kind,
            "final_url": final_url,
            "content_type": content_type,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "extracted_chars": len(document_text),
        })
    except Exception as exc:
        attempt.update({"status": "failed", "error": type(exc).__name__ + ":" + str(exc)[:180]})
    attempts.append(attempt)


def _world_bank_notice(item: dict[str, Any], attempts: list[dict[str, Any]], parts: list[str],
                       discovered: list[str] | None = None, attachment_labels: dict[str, str] | None = None) -> bool:
    """Read only an exact-ID official notice, never arbitrary API search hits."""
    identity = item.get("id")
    if item.get("source") != "WORLD_BANK" or not isinstance(identity, str) or not re.fullmatch(r"OP[0-9]{8}", identity):
        return False
    query = urllib.parse.urlencode({"format": "json", "rows": 2, "qterm": identity, "fl": "id,notice_text"})
    url = "https://search.worldbank.org/api/v2/procnotices?" + query
    attempt = {"url": url, "status": "pending", "source": "source_page", "notice_id": identity}
    try:
        data, content_type, final_url = _download(url, MAX_SOURCE_PAGE_BYTES)
        final = urllib.parse.urlsplit(final_url)
        if final.scheme != "https" or final.hostname != "search.worldbank.org" or final.path != "/api/v2/procnotices":
            raise ValueError("unexpected_world_bank_api_origin")
        payload = json.loads(data)
        rows = payload.get("procnotices", {})
        rows = list(rows.values()) if isinstance(rows, dict) else rows
        matches = [row for row in rows if isinstance(row, dict) and row.get("id") == identity] if isinstance(rows, list) else []
        if len(matches) != 1:
            raise ValueError("world_bank_notice_id_not_unique")
        body = matches[0].get("notice_text")
        if not isinstance(body, str) or len(body) > MAX_EXTRACTED_CHARS:
            raise ValueError("world_bank_notice_text_missing_or_too_large")
        text, found = _parse_html_page(body.encode("utf-8"), final_url, attachment_labels)
        if len(text) < 160:
            raise ValueError("insufficient_world_bank_notice_text")
        _append_text(parts, text)
        from src.world_bank_line_items import annotate as annotate_line_items
        annotate_line_items(item, text, final_url)
        # A notice may describe several lots. Keep the text available for review
        # while refusing automatic promotion of a single aggregate scope.
        if re.search(r"\blots?\b", text, re.I):
            item["source_lot_selection_required"] = True
        if discovered is not None:
            for link in found:
                if link not in discovered and link not in _candidate_urls(item):
                    discovered.append(link)
        attempt.update({"status": "parsed", "kind": "source_page", "format": "world_bank_notice_json",
                        "discovered_attachments": len(found),
                        "final_url": final_url, "content_type": content_type, "bytes": len(data), "extracted_chars": len(text)})
    except Exception as exc:
        attempt.update({"status": "failed", "error": type(exc).__name__ + ":" + str(exc)[:180]})
    attempts.append(attempt)
    return attempt["status"] == "parsed"


def enrich_opportunity(item: dict[str, Any]) -> dict[str, Any]:
    attachments = _candidate_urls(item)
    source_pages = _source_page_urls(item)
    attempts: list[dict[str, Any]] = []
    documents: list[tuple[str, str]] = []
    attachment_labels: dict[str, str] = {}
    source_page_parts: list[str] = []
    discovered_attachments: list[str] = []
    attachment_origins: dict[str, str] = {}
    indexes: list[str] = []
    from src.document_coverage import observe, summarize
    coverage: dict = {}
    observe([{'href': url} for url in _all_urls(item)], '', coverage)

    for url in attachments:
        parts: list[str] = []
        _try_attachment(url, attempts, parts)
        documents.extend((url, text) for text in parts)

    world_bank_read = _world_bank_notice(item, attempts, source_page_parts, discovered_attachments, attachment_labels)
    source_requirement_scopes = []
    if world_bank_read:
        notice_url = next(a["url"] for a in attempts if a.get("format") == "world_bank_notice_json")
        source_requirement_scopes = extract_requirements(notice_url, source_page_parts[0])
    for link in discovered_attachments:
        origin = next((a["url"] for a in attempts if a.get("status") == "parsed"), None)
        if origin:
            attachment_origins[link] = origin
    for url in ([] if world_bank_read else source_pages):
        page_attempt: dict[str, Any] = {"url": url, "status": "pending", "source": "source_page"}
        try:
            limit = MAX_DOCUMENT_BYTES if url == item.get("document_url") else MAX_SOURCE_PAGE_BYTES
            data, content_type, final_url = _download(url, limit)
            found = []
            if content_type in {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"} or data.startswith(b"%PDF"):
                document_text, kind = _parse(data, content_type, final_url)
                if len(document_text) < 80:
                    raise ValueError("insufficient_extractable_text")
                documents.append((final_url, document_text))
                page_attempt.update({"status":"parsed", "source":"linked_document", "kind":kind,
                    "final_url":final_url, "content_type":content_type, "bytes":len(data), "extracted_chars":len(document_text)})
            else:
                if "html" not in content_type and not content_type.startswith("text/"):
                    raise ValueError("source_page_not_html")
                page_text, found = _parse_html_page(data, final_url, attachment_labels, indexes, coverage)
                if len(page_text) >= 160:
                    _append_text(source_page_parts, page_text)
                    page_attempt.update({
                        "status": "parsed", "kind": "source_page", "final_url": final_url,
                        "content_type": content_type, "bytes": len(data), "extracted_chars": len(page_text),
                        "discovered_attachments": len(found),
                    })
                else:
                    page_attempt.update({"status": "failed", "error": "insufficient_source_page_text"})
            for found_url in found:
                if found_url not in attachments and found_url not in discovered_attachments:
                    discovered_attachments.append(found_url)
                    attachment_origins[found_url] = final_url
        except Exception as exc:
            page_attempt.update({"status": "failed", "error": type(exc).__name__ + ":" + str(exc)[:180]})
        attempts.append(page_attempt)

    # One explicitly linked parent/index page, one hop only. Its text may
    # describe several lots, so use it for discovery and never merge it as
    # commercial/technical evidence. Successful downloads retain their own URL.
    index_attempts = 0
    visited = {a.get("url") for a in attempts} | {a.get("final_url") for a in attempts}
    for index_url in indexes:
        if index_url in visited or index_attempts >= MAX_DOCUMENT_INDEX_PAGES:
            continue
        index_attempts += 1
        visited.add(index_url)
        attempt = {"url": index_url, "source": "document_index", "status": "pending"}
        try:
            data, content_type, final_url = _download(index_url, MAX_SOURCE_PAGE_BYTES)
            if not same_origin(index_url, final_url):
                raise ValueError("document_index_origin_changed")
            if "html" not in content_type:
                raise ValueError("document_index_not_html")
            _, found = _parse_html_page(data, final_url, attachment_labels, coverage=coverage)
            for link in found:
                if link not in attachments and link not in discovered_attachments:
                    discovered_attachments.append(link)
                    attachment_origins[link] = final_url
            attempt.update({"status": "parsed", "kind": "document_index", "final_url": final_url,
                            "bytes": len(data), "discovered_attachments": len(found)})
        except Exception as exc:
            attempt.update({"status": "failed", "error": type(exc).__name__ + ":" + str(exc)[:180]})
        attempts.append(attempt)

    discovered_attachments = select_attachments(
        [(link, attachment_labels.get(link, "")) for link in discovered_attachments],
        MAX_DISCOVERED_ATTACHMENTS,
    )
    for url in discovered_attachments:
        origin = attachment_origins.get(url)
        parts = []
        _try_attachment(url, attempts, parts, origin)
        documents.extend((url, text) for text in parts)

    # Read each document with its own bounded budget, then rank across direct,
    # linked and discovered documents. A direct generic attachment must not
    # exhaust the shared budget before a later discovered technical annex.
    documents.sort(key=lambda entry: attachment_priority(entry[0], attachment_labels.get(entry[0], "")))
    full_text = "\n\n".join([text for _, text in documents] + source_page_parts)
    merged = full_text[:MAX_EXTRACTED_CHARS]
    # Extract per-document clauses before losing the URL/text association.
    item["technical_requirement_scopes"] = [scope for url, text in documents
        for scope in extract_requirements(url, text)] + source_requirement_scopes
    candidate_count = len(attachments) + len(source_pages)
    parsed_count = sum(1 for x in attempts if x.get("status") == "parsed" and x.get("source") != "document_index")
    item["document_extraction"] = {
        "status": "parsed" if merged else ("attempted_no_text" if candidate_count else "no_supported_document"),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "refresh_policy": "every_scan",
        "source_backed_only": True,
        "candidate_count": candidate_count,
        "source_page_count": len(source_pages),
        "document_index_count": index_attempts,
        "discovered_attachment_count": len(discovered_attachments),
        "parsed_count": parsed_count,
        "attempts": attempts,
        "text_chars": len(merged),
        "text_truncated": len(full_text) > MAX_EXTRACTED_CHARS,
        "omitted_chars": max(0, len(full_text) - MAX_EXTRACTED_CHARS),
        **summarize(coverage, attempts),
    }
    if merged:
        item["document_extracted_text"] = merged
    else:
        item.pop("document_extracted_text", None)
    return item


def enrich_payload(payload: dict[str, Any], fallback_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        return payload

    # Keep the fallback argument for callers, but never treat a previous scan's
    # document as current evidence. Amendments may retain the same ID and URL.
    to_fetch: list[dict[str, Any]] = []
    for item in opportunities:
        if not isinstance(item, dict):
            continue
        # Clear evidence even when a caller supplies already enriched rows.
        item.pop("document_extracted_text", None)
        item.pop("document_extraction", None)
        item.pop("technical_requirement_scopes", None)
        if _all_urls(item):
            to_fetch.append(item)
        else:
            enrich_opportunity(item)

    if to_fetch:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(enrich_opportunity, item): item for item in to_fetch}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    # A worker failure must not silently erase missing-document
                    # evidence or leave partially written text marked as parsed.
                    item = futures[future]
                    item.pop("document_extracted_text", None)
                    item.pop("technical_requirement_scopes", None)
                    item["document_extraction"] = {
                        "status": "attempted_no_text",
                        "checked_at": datetime.now(timezone.utc).isoformat(),
                        "refresh_policy": "every_scan",
                        "source_backed_only": True,
                        "candidate_count": len(_candidate_urls(item)) + len(_source_page_urls(item)),
                        "parsed_count": 0,
                        "attempts": [{"source": "document_worker", "status": "failed",
                                      "error": type(exc).__name__}],
                        "text_chars": 0,
                    }

    attempted = 0
    parsed = 0
    pages_parsed = 0
    discovered = 0
    for item in opportunities:
        if not isinstance(item, dict):
            continue
        info = item.get("document_extraction") or {}
        if info.get("candidate_count"):
            attempted += 1
        if info.get("parsed_count"):
            parsed += 1
        pages_parsed += sum(1 for x in (info.get("attempts") or []) if isinstance(x, dict) and x.get("source") == "source_page" and x.get("status") == "parsed")
        discovered += int(info.get("discovered_attachment_count") or 0)

    payload["document_extraction"] = {
        "version": 3,
        "refresh_policy": "every_scan",
        "mode": "public_source_pages_and_documents",
        "attempted_opportunities": attempted,
        "parsed_opportunities": parsed,
        "source_pages_parsed": pages_parsed,
        "discovered_attachments": discovered,
        "reused_last_known_good": 0,
    }
    return payload


def main() -> None:
    if len(sys.argv) not in {2, 3}:
        raise SystemExit("usage: python -m src.document_parser <json-file> [last-known-good-json]")
    path = Path(sys.argv[1])
    payload = json.loads(path.read_text(encoding="utf-8"))
    fallback_payload = None
    if len(sys.argv) == 3:
        fallback_path = Path(sys.argv[2])
        if fallback_path.exists() and fallback_path.stat().st_size:
            try:
                fallback_payload = json.loads(fallback_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                fallback_payload = None
    payload = enrich_payload(payload, fallback_payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = payload.get("document_extraction") or {}
    print(
        "DOCUMENT_EXTRACTION_SUMMARY "
        f"attempted={summary.get('attempted_opportunities', 0)} "
        f"parsed={summary.get('parsed_opportunities', 0)} "
        f"pages={summary.get('source_pages_parsed', 0)} "
        f"attachments={summary.get('discovered_attachments', 0)} "
        f"reused={summary.get('reused_last_known_good', 0)}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
