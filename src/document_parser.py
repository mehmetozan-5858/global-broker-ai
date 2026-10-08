from __future__ import annotations

import io
import ipaddress
import json
import re
import socket
import sys
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
MAX_SOURCE_PAGE_BYTES = 2 * 1024 * 1024
MAX_EXTRACTED_CHARS = 40000
MAX_PDF_PAGES = 80
MAX_SOURCE_PAGES_PER_OPPORTUNITY = 1
MAX_DISCOVERED_ATTACHMENTS = 3
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
ATTACHMENT_EXTENSIONS = (".pdf", ".docx", ".txt")


def _collect_urls(value: Any) -> list[str]:
    out: list[str] = []
    if isinstance(value, str):
        if value.startswith(("http://", "https://")):
            out.append(value)
        else:
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
    return urllib.parse.urlparse(url).path.lower().endswith(ATTACHMENT_EXTENSIONS)


def _candidate_urls(item: dict[str, Any]) -> list[str]:
    return [url for url in _all_urls(item) if _is_attachment_url(url)][:6]


def _source_page_urls(item: dict[str, Any]) -> list[str]:
    return [url for url in _all_urls(item) if not _is_attachment_url(url)][:MAX_SOURCE_PAGES_PER_OPPORTUNITY]


def _public_http_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
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
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
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
        text = " ".join(raw.split())
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
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    texts = [node.text or "" for node in root.iter() if node.tag.endswith("}t")]
    return " ".join(" ".join(texts).split())[:MAX_EXTRACTED_CHARS]


def _parse_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return " ".join(data.decode(encoding).split())[:MAX_EXTRACTED_CHARS]
        except UnicodeDecodeError:
            continue
    return ""


class _TenderHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.hrefs: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            return
        if tag == "a":
            for key, value in attrs:
                if key.lower() == "href" and value:
                    self.hrefs.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            cleaned = " ".join(data.split())
            if cleaned:
                self.text_parts.append(cleaned)


def _decode_html(data: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "gb18030", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def _parse_html_page(data: bytes, base_url: str) -> tuple[str, list[str]]:
    parser = _TenderHTMLParser()
    parser.feed(_decode_html(data))
    visible = " ".join(parser.text_parts)
    visible = " ".join(visible.split())[:MAX_EXTRACTED_CHARS]
    attachments: list[str] = []
    seen: set[str] = set()
    for href in parser.hrefs:
        absolute = urllib.parse.urljoin(base_url, href)
        if absolute in seen or not _is_attachment_url(absolute):
            continue
        seen.add(absolute)
        attachments.append(absolute)
        if len(attachments) >= MAX_DISCOVERED_ATTACHMENTS:
            break
    return visible, attachments


def _parse(data: bytes, content_type: str, url: str) -> tuple[str, str]:
    path = urllib.parse.urlparse(url).path.lower()
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
            "extracted_chars": len(document_text),
        })
    except Exception as exc:
        attempt.update({"status": "failed", "error": type(exc).__name__ + ":" + str(exc)[:180]})
    attempts.append(attempt)


def enrich_opportunity(item: dict[str, Any]) -> dict[str, Any]:
    attachments = _candidate_urls(item)
    source_pages = _source_page_urls(item)
    attempts: list[dict[str, Any]] = []
    extracted_parts: list[str] = []
    discovered_attachments: list[str] = []

    for url in attachments:
        _try_attachment(url, attempts, extracted_parts)

    for url in source_pages:
        page_attempt: dict[str, Any] = {"url": url, "status": "pending", "source": "source_page"}
        try:
            data, content_type, final_url = _download(url, MAX_SOURCE_PAGE_BYTES)
            if "html" not in content_type and not content_type.startswith("text/"):
                raise ValueError("source_page_not_html")
            page_text, found = _parse_html_page(data, final_url)
            if len(page_text) >= 160:
                _append_text(extracted_parts, page_text)
                page_attempt.update({
                    "status": "parsed",
                    "kind": "source_page",
                    "final_url": final_url,
                    "content_type": content_type,
                    "bytes": len(data),
                    "extracted_chars": len(page_text),
                    "discovered_attachments": len(found),
                })
            else:
                page_attempt.update({"status": "failed", "error": "insufficient_source_page_text"})
            for found_url in found:
                if found_url not in attachments and found_url not in discovered_attachments:
                    discovered_attachments.append(found_url)
        except Exception as exc:
            page_attempt.update({"status": "failed", "error": type(exc).__name__ + ":" + str(exc)[:180]})
        attempts.append(page_attempt)

    for url in discovered_attachments[:MAX_DISCOVERED_ATTACHMENTS]:
        origin = next((x["url"] for x in attempts if x.get("source") == "source_page" and x.get("status") == "parsed"), None)
        _try_attachment(url, attempts, extracted_parts, origin)

    merged = "\n\n".join(extracted_parts)[:MAX_EXTRACTED_CHARS]
    candidate_count = len(attachments) + len(source_pages)
    parsed_count = sum(1 for x in attempts if x.get("status") == "parsed")
    item["document_extraction"] = {
        "status": "parsed" if merged else ("attempted_no_text" if candidate_count else "no_supported_document"),
        "source_backed_only": True,
        "candidate_count": candidate_count,
        "source_page_count": len(source_pages),
        "discovered_attachment_count": len(discovered_attachments),
        "parsed_count": parsed_count,
        "attempts": attempts,
        "text_chars": len(merged),
    }
    if merged:
        item["document_extracted_text"] = merged
    else:
        item.pop("document_extracted_text", None)
    return item


def _opportunity_key(item: dict[str, Any]) -> str:
    for key in ("id", "notice-id", "notice_id", "source_url", "url"):
        value = item.get(key)
        if value:
            return str(value)
    return ""


def _reuse_last_good(item: dict[str, Any], previous_map: dict[str, dict[str, Any]]) -> bool:
    key = _opportunity_key(item)
    old = previous_map.get(key) if key else None
    if not isinstance(old, dict):
        return False
    old_text = old.get("document_extracted_text")
    old_info = old.get("document_extraction")
    if not isinstance(old_text, str) or len(old_text) < 80 or not isinstance(old_info, dict) or old_info.get("status") != "parsed":
        return False
    item["document_extracted_text"] = old_text[:MAX_EXTRACTED_CHARS]
    info = dict(old_info)
    info["reused_from_last_known_good"] = True
    item["document_extraction"] = info
    return True


def enrich_payload(payload: dict[str, Any], fallback_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        return payload

    previous_map: dict[str, dict[str, Any]] = {}
    if isinstance(fallback_payload, dict):
        old_items = fallback_payload.get("opportunities")
        if isinstance(old_items, list):
            for old in old_items:
                if isinstance(old, dict):
                    key = _opportunity_key(old)
                    if key:
                        previous_map[key] = old

    to_fetch: list[dict[str, Any]] = []
    reused = 0
    for item in opportunities:
        if not isinstance(item, dict):
            continue
        if _reuse_last_good(item, previous_map):
            reused += 1
        elif _all_urls(item):
            to_fetch.append(item)
        else:
            enrich_opportunity(item)

    if to_fetch:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(enrich_opportunity, item) for item in to_fetch]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass

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
        "version": 2,
        "mode": "public_source_pages_and_documents",
        "attempted_opportunities": attempted,
        "parsed_opportunities": parsed,
        "source_pages_parsed": pages_parsed,
        "discovered_attachments": discovered,
        "reused_last_known_good": reused,
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
