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
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
MAX_EXTRACTED_CHARS = 40000
MAX_PDF_PAGES = 80
TIMEOUT_SECONDS = 15
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


def _candidate_urls(item: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for key in URL_KEYS:
        urls.extend(_collect_urls(item.get(key)))
    seen: set[str] = set()
    candidates: list[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        path = urllib.parse.urlparse(url).path.lower()
        if path.endswith((".pdf", ".docx", ".txt")):
            candidates.append(url)
    return candidates[:6]


def _download(url: str) -> tuple[bytes, str, str]:
    if not _public_http_url(url):
        raise ValueError("non_public_or_unresolvable_url")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,*/*;q=0.5"},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        final_url = response.geturl()
        if not _public_http_url(final_url):
            raise ValueError("redirected_to_non_public_url")
        content_type = (response.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_DOCUMENT_BYTES:
            raise ValueError("document_too_large")
        data = response.read(MAX_DOCUMENT_BYTES + 1)
        if len(data) > MAX_DOCUMENT_BYTES:
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


def _parse(data: bytes, content_type: str, url: str) -> tuple[str, str]:
    path = urllib.parse.urlparse(url).path.lower()
    if content_type == "application/pdf" or path.endswith(".pdf") or data.startswith(b"%PDF"):
        return _parse_pdf(data), "pdf"
    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or path.endswith(".docx"):
        return _parse_docx(data), "docx"
    if content_type.startswith("text/") or path.endswith(".txt"):
        return _parse_text(data), "text"
    raise ValueError("unsupported_document_type")


def enrich_opportunity(item: dict[str, Any]) -> dict[str, Any]:
    candidates = _candidate_urls(item)
    attempts: list[dict[str, Any]] = []
    extracted_parts: list[str] = []
    for url in candidates:
        attempt: dict[str, Any] = {"url": url, "status": "pending"}
        try:
            data, content_type, final_url = _download(url)
            document_text, kind = _parse(data, content_type, final_url)
            if len(document_text) < 80:
                raise ValueError("insufficient_extractable_text")
            remaining = MAX_EXTRACTED_CHARS - sum(len(x) for x in extracted_parts)
            if remaining > 0:
                extracted_parts.append(document_text[:remaining])
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
        if sum(len(x) for x in extracted_parts) >= MAX_EXTRACTED_CHARS:
            break
    merged = "\n\n".join(extracted_parts)[:MAX_EXTRACTED_CHARS]
    item["document_extraction"] = {
        "status": "parsed" if merged else ("attempted_no_text" if candidates else "no_supported_document"),
        "source_backed_only": True,
        "candidate_count": len(candidates),
        "parsed_count": sum(1 for x in attempts if x.get("status") == "parsed"),
        "attempts": attempts,
        "text_chars": len(merged),
    }
    if merged:
        item["document_extracted_text"] = merged
    else:
        item.pop("document_extracted_text", None)
    return item


def enrich_payload(payload: dict[str, Any]) -> dict[str, Any]:
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        return payload
    attempted = 0
    parsed = 0
    for item in opportunities:
        if not isinstance(item, dict):
            continue
        enrich_opportunity(item)
        info = item.get("document_extraction") or {}
        if info.get("candidate_count"):
            attempted += 1
        if info.get("parsed_count"):
            parsed += 1
    payload["document_extraction"] = {
        "version": 1,
        "mode": "public_source_documents_only",
        "attempted_opportunities": attempted,
        "parsed_opportunities": parsed,
    }
    return payload


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.document_parser <json-file>")
    path = Path(sys.argv[1])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload = enrich_payload(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = payload.get("document_extraction") or {}
    print(
        "DOCUMENT_EXTRACTION_SUMMARY "
        f"attempted={summary.get('attempted_opportunities', 0)} "
        f"parsed={summary.get('parsed_opportunities', 0)}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
