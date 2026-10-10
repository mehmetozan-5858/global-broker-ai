from __future__ import annotations

import html
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from .browser_render import dump_dom

LIST_URL = "https://tenders.etimad.sa/Tender/AllTendersForVisitor?PageNumber=1&PageSize=20&PublishDateId=5&Sort=SubmitionDate&SortDirection=DESC"
BASE_URL = "https://tenders.etimad.sa/"
DETAIL_PATH_TOKEN = "DetailsForVisitor?STenderId="


class _LinkTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._anchor: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._anchor = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        self.parts.append(text)
        if self._href is not None:
            self._anchor.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.links.append((" ".join(self._anchor).strip(), self._href))
            self._href = None
            self._anchor = []


def _fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; GlobalBrokerAI/1.0; +https://github.com/mehmetozan-5858/global-broker-ai)",
            "Accept-Language": "ar,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=35) as response:
        return response.read().decode("utf-8", "replace")


def discover_detail_links(markup: str, limit: int = 15) -> list[str]:
    parser = _LinkTextParser()
    parser.feed(markup)
    links: list[str] = []
    seen: set[str] = set()
    for _, href in parser.links:
        if DETAIL_PATH_TOKEN.lower() not in href.lower():
            continue
        url = urljoin(BASE_URL, html.unescape(href))
        if url not in seen:
            seen.add(url)
            links.append(url)
        if len(links) >= limit:
            break
    if links:
        return links
    # Some client-side builds assign the detail URL outside an anchor. Recover only
    # exact official Etimad visitor-detail URLs from the rendered DOM; do not invent IDs.
    pattern = re.compile(r"(?:https?://tenders\.etimad\.sa)?/Tender/DetailsForVisitor\?STenderId=([^\"'<>\s]+)", re.I)
    for match in pattern.finditer(html.unescape(markup)):
        url = urljoin(BASE_URL, f"/Tender/DetailsForVisitor?STenderId={match.group(1)}")
        if url not in seen:
            seen.add(url)
            links.append(url)
        if len(links) >= limit:
            break
    return links


def _value_after(parts: list[str], labels: tuple[str, ...]) -> str:
    for idx, part in enumerate(parts):
        normalized = re.sub(r"\s+", " ", part).strip()
        if normalized in labels:
            for candidate in parts[idx + 1: idx + 5]:
                value = re.sub(r"\s+", " ", candidate).strip()
                if value and value not in labels:
                    return value
    return ""


def parse_detail(markup: str, url: str) -> dict[str, Any] | None:
    parser = _LinkTextParser()
    parser.feed(markup)
    parts = parser.parts
    title = _value_after(parts, ("اسم المنافسة",))
    tender_number = _value_after(parts, ("رقم المنافسة",))
    reference = _value_after(parts, ("الرقم المرجعي",))
    purpose = _value_after(parts, ("الغرض من المنافسة",))
    buyer = _value_after(parts, ("الجهة الحكوميه", "الجهة الحكومية"))
    status = _value_after(parts, ("حالة المنافسة",))
    remaining = _value_after(parts, ("الوقت المتبقى",))
    booklet = _value_after(parts, ("قيمة وثائق المنافسة",))
    deadline = _value_after(parts, ("آخر موعد لتقديم العروض", "تاريخ انتهاء تقديم العروض"))

    if not title:
        return None
    ended_tokens = ("إنتهى", "انتهى", "تم اعتماد الترسية", "تم اعلان الترسية", "مرحلة الترسية")
    status_text = f"{status} {remaining}"
    if any(token in status_text for token in ended_tokens):
        return None

    stable_id = reference or tender_number or re.sub(r"\W+", "-", title)[:60]
    return {
        "id": f"saudi-etimad-{stable_id}",
        "source": "Saudi Etimad",
        "source_url": url,
        "official_links": [url],
        "title_original": title,
        "title_tr": title,
        "description": purpose or None,
        "buyer-name": buyer or None,
        "buyer-country": "Saudi Arabia",
        "country": "Saudi Arabia",
        "deadline-receipt-tender-date-lot": deadline or None,
        "tender_number": tender_number or None,
        "reference_number": reference or None,
        "competition_status": status or None,
        "time_remaining": remaining or None,
        "tender_documents_value": booklet or None,
        "gulf_live_source": True,
        "foreign_supplier_eligibility_assumed": False,
        "source_provenance": {
            "source": url,
            "reference_number": reference or None,
            "parsed_from_official_detail_page": True,
        },
    }


def _render_if_needed(markup: str, meta: dict[str, Any]) -> str:
    links = discover_detail_links(markup)
    if links:
        return markup
    # Etimad's visitor board is Angular/client-rendered. The GitHub Ubuntu runner
    # already ships a browser; use it as a zero-subscription fallback rather than
    # paying for an external scraping service.
    try:
        rendered = dump_dom(LIST_URL, virtual_time_ms=18000, timeout_seconds=45)
        meta["browser_fallback_used"] = True
        return rendered
    except Exception as exc:
        meta["browser_fallback_error"] = f"{type(exc).__name__}:{exc}"
        return markup


def collect() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    meta: dict[str, Any] = {
        "listing_url": LIST_URL,
        "listing_accessible": False,
        "detail_links": 0,
        "detail_failures": 0,
        "browser_fallback_used": False,
    }
    try:
        listing = _fetch(LIST_URL)
        meta["listing_accessible"] = True
    except Exception as exc:
        meta["error"] = type(exc).__name__
        listing = ""
    listing = _render_if_needed(listing, meta)
    links = discover_detail_links(listing)
    meta["detail_links"] = len(links)
    rows: list[dict[str, Any]] = []
    for url in links:
        try:
            detail = _fetch(url)
            row = parse_detail(detail, url)
            if not row:
                # Detail pages can also be client-rendered.
                detail = dump_dom(url, virtual_time_ms=12000, timeout_seconds=35)
                row = parse_detail(detail, url)
                if row:
                    meta["browser_detail_fallbacks"] = int(meta.get("browser_detail_fallbacks") or 0) + 1
            if row:
                rows.append(row)
        except Exception:
            meta["detail_failures"] += 1
    return rows, meta


def merge_payload(payload: dict[str, Any], rows: list[dict[str, Any]], meta: dict[str, Any]) -> dict[str, Any]:
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        opportunities = []
        payload["opportunities"] = opportunities
    seen = {str(x.get("id")) for x in opportunities if isinstance(x, dict)}
    added = 0
    for row in rows:
        if row["id"] not in seen:
            opportunities.append(row)
            seen.add(row["id"])
            added += 1
    if not meta.get("listing_accessible") and not meta.get("browser_fallback_used"):
        status = "source_unavailable"
    elif not meta.get("detail_links"):
        status = "listing_accessible_no_detail_links"
    elif rows:
        status = "ok"
    else:
        status = "no_active_parseable_tenders"
    payload["saudi_etimad_feed"] = {
        "source": LIST_URL,
        "status": status,
        "parsed_opportunities": len(rows),
        "added": added,
        "live_ingestion": bool(rows),
        "foreign_supplier_eligibility_assumed": False,
        **meta,
    }
    return payload


def main(path: str) -> None:
    p = Path(path)
    payload = json.loads(p.read_text(encoding="utf-8"))
    rows, meta = collect()
    merge_payload(payload, rows, meta)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SAUDI_ETIMAD_FEED", json.dumps(payload["saudi_etimad_feed"], ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.saudi_etimad_feed <payload.json>")
    main(sys.argv[1])
