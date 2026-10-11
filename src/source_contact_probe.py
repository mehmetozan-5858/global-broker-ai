from __future__ import annotations

import json
import re
import socket
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from src.contact_enrichment import CONTACT_HINT_RE, EMAIL_RE, PHONE_RE, _clean_phone

USER_AGENT = "GlobalBrokerContactProbe/1.0 (+source-verification)"
MAX_BYTES = 900_000
MAX_ROWS = 35
CONTACT_PATH_HINTS = ("contact", "procurement", "purchas", "tender", "supplier", "vendor", "ihale", "iletisim", "satinalma")


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.mailtos: list[str] = []
        self.tels: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._href = ""
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href") or ""
        self._href = href.strip()
        self._link_text = []
        if self._href.lower().startswith("mailto:"):
            self.mailtos.append(self._href[7:].split("?", 1)[0].strip())
        elif self._href.lower().startswith("tel:"):
            self.tels.append(self._href[4:].strip())

    def handle_data(self, data: str) -> None:
        clean = " ".join(data.split())
        if not clean:
            return
        self.text_parts.append(clean)
        if self._href:
            self._link_text.append(clean)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            self.links.append((self._href, " ".join(self._link_text)))
            self._href = ""
            self._link_text = []

    @property
    def text(self) -> str:
        return "\n".join(self.text_parts)


def _is_public_https(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            return False
        host = parsed.hostname.lower()
        if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
            return False
        try:
            infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
        except OSError:
            return False
        for info in infos:
            ip = info[4][0]
            if ip.startswith(("10.", "127.", "169.254.", "192.168.")) or ip.startswith("172.") and 16 <= int(ip.split('.')[1]) <= 31:
                return False
        return True
    except Exception:
        return False


def _fetch(url: str) -> PageParser | None:
    if not _is_public_https(url):
        return None
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    try:
        with urlopen(req, timeout=8) as response:
            ctype = (response.headers.get("Content-Type") or "").lower()
            if "html" not in ctype:
                return None
            raw = response.read(MAX_BYTES)
    except Exception:
        return None
    parser = PageParser()
    try:
        parser.feed(raw.decode("utf-8", errors="ignore"))
    except Exception:
        return None
    return parser


def _same_origin(base: str, candidate: str) -> bool:
    try:
        a, b = urlparse(base), urlparse(candidate)
        return a.scheme == b.scheme == "https" and a.hostname and a.hostname == b.hostname
    except Exception:
        return False


def _best_contact(parser: PageParser) -> tuple[str, str, str]:
    text = parser.text
    email = ""
    phone = ""
    for value in parser.mailtos:
        if EMAIL_RE.fullmatch(value):
            email = value.lower()
            break
    for value in parser.tels:
        phone = _clean_phone(value)
        if phone:
            break
    if not email:
        for match in EMAIL_RE.finditer(text):
            start, end = max(0, match.start() - 180), min(len(text), match.end() + 180)
            if CONTACT_HINT_RE.search(text[start:end]):
                email = match.group(1).lower()
                break
    if not phone:
        for match in PHONE_RE.finditer(text):
            candidate = _clean_phone(match.group(1))
            if not candidate:
                continue
            start, end = max(0, match.start() - 180), min(len(text), match.end() + 180)
            if CONTACT_HINT_RE.search(text[start:end]):
                phone = candidate
                break
    return email, phone, text[:700]


def _source_url(row: dict[str, Any]) -> str:
    for key in ("source_url", "notice_url", "detail_url", "official_url", "url"):
        value = str(row.get(key) or "").strip()
        if value.startswith("https://"):
            return value
    links = row.get("official_links")
    if isinstance(links, list):
        for value in links:
            value = str(value or "").strip()
            if value.startswith("https://"):
                return value
    return ""


def probe_row(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("direct_contact_available") or row.get("contact_email") or row.get("contact_phone"):
        return row
    base = _source_url(row)
    if not base:
        return row
    parser = _fetch(base)
    if not parser:
        return row
    email, phone, _ = _best_contact(parser)
    checked = [base]
    source_page = base

    if not (email or phone):
        candidates: list[str] = []
        for href, label in parser.links:
            absolute = urljoin(base, href)
            hint = (absolute + " " + label).lower()
            if _same_origin(base, absolute) and any(x in hint for x in CONTACT_PATH_HINTS):
                candidates.append(absolute)
        for contact_url in list(dict.fromkeys(candidates))[:2]:
            page = _fetch(contact_url)
            checked.append(contact_url)
            if not page:
                continue
            email, phone, _ = _best_contact(page)
            if email or phone:
                source_page = contact_url
                break

    row["contact_probe"] = {
        "version": 1,
        "status": "found" if (email or phone) else "checked_no_direct_contact",
        "checked_pages": checked,
        "source_page": source_page if (email or phone) else None,
    }
    if email:
        row["contact_email"] = email
    if phone:
        row["contact_phone"] = phone
    if email or phone:
        row["contact_source_backed"] = True
        row["direct_contact_available"] = True
        row["contact_route_available"] = True
    return row


def probe_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("opportunities")
    if not isinstance(rows, list):
        return payload
    attempted = found = 0
    for row in rows:
        if attempted >= MAX_ROWS:
            break
        if not isinstance(row, dict) or row.get("direct_contact_available"):
            continue
        if not _source_url(row):
            continue
        attempted += 1
        before = bool(row.get("contact_email") or row.get("contact_phone"))
        probe_row(row)
        after = bool(row.get("contact_email") or row.get("contact_phone"))
        found += int(after and not before)
    payload["contact_probe_summary"] = {
        "version": 1,
        "mode": "official_source_same_origin_only",
        "attempted": attempted,
        "direct_contacts_found": found,
        "max_rows_per_run": MAX_ROWS,
    }
    return payload


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.source_contact_probe <json-file>")
    path = Path(sys.argv[1])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload = probe_payload(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
