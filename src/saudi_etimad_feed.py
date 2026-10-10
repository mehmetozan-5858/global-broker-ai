from __future__ import annotations

import html
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urljoin

from .browser_render import dump_dom

LIST_URL = "https://tenders.etimad.sa/Tender/AllTendersForVisitor?PageNumber=1&PageSize=20&PublishDateId=5&Sort=SubmitionDate&SortDirection=DESC"
API_URL = "https://tenders.etimad.sa/Tender/AllSupplierTendersForVisitorAsync"
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


def _request(url: str, *, accept: str = "text/html,*/*") -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36",
            "Accept": accept,
            "Accept-Language": "ar,en;q=0.8",
            "Referer": LIST_URL,
        },
    )
    with urllib.request.urlopen(req, timeout=35) as response:
        return response.read()


def _fetch(url: str) -> str:
    return _request(url).decode("utf-8", "replace")


def _api_page(page: int = 1, page_size: int = 24) -> tuple[list[dict[str, Any]], str]:
    params = {
        "PageSize": page_size,
        "PageNumber": page,
        "TenderCategory": 2,
        "PublishDateId": 1,
        "SortDirection": "DESC",
        "Sort": "SubmitionDate",
        "IsSearch": "true",
    }
    url = f"{API_URL}?{urlencode(params)}"
    payload = json.loads(_request(url, accept="application/json,text/plain,*/*").decode("utf-8", "replace"))
    rows = payload.get("data") if isinstance(payload, dict) else None
    return ([x for x in (rows or []) if isinstance(x, dict)], url)


def _api_record(item: dict[str, Any], source_url: str) -> dict[str, Any] | None:
    title = str(item.get("tenderName") or "").strip()
    reference = str(item.get("referenceNumber") or "").strip()
    tender_number = str(item.get("tenderNumber") or "").strip()
    if not title or not (reference or tender_number):
        return None
    stable_id = reference or tender_number
    deadline = item.get("lastOfferPresentationDate")
    published = item.get("submitionDate")
    buyer = str(item.get("agencyName") or "").strip() or None
    tender_type = str(item.get("tenderTypeName") or "").strip() or None
    return {
        "id": f"saudi-etimad-{stable_id}",
        "source": "Saudi Etimad official visitor API",
        "source_url": source_url,
        "official_links": [source_url, LIST_URL],
        "title_original": title,
        "title_tr": title,
        "buyer-name": buyer,
        "buyer-country": "Saudi Arabia",
        "country": "Saudi Arabia",
        "publication-date": published or None,
        "deadline-receipt-tender-date-lot": deadline or None,
        "tender_number": tender_number or None,
        "reference_number": reference or None,
        "tender_type": tender_type,
        "branch_name": str(item.get("branchName") or "").strip() or None,
        "gulf_live_source": True,
        "foreign_supplier_eligibility_assumed": False,
        "source_provenance": {
            "source": source_url,
            "reference_number": reference or None,
            "parsed_from_official_json_endpoint": True,
        },
    }


def collect_api(max_pages: int = 2) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    meta: dict[str, Any] = {"api_endpoint": API_URL, "api_pages_fetched": 0, "api_errors": []}
    for page in range(1, max_pages + 1):
        try:
            raw, source_url = _api_page(page)
            meta["api_pages_fetched"] += 1
        except Exception as exc:
            meta["api_errors"].append(f"page={page}:{type(exc).__name__}")
            break
        if not raw:
            break
        for item in raw:
            row = _api_record(item, source_url)
            if row and row["id"] not in seen:
                seen.add(row["id"])
                rows.append(row)
    meta["api_records"] = len(rows)
    return rows, meta


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
            return links
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
        if re.sub(r"\s+", " ", part).strip() in labels:
            for candidate in parts[idx + 1: idx + 5]:
                value = re.sub(r"\s+", " ", candidate).strip()
                if value and value not in labels:
                    return value
    return ""


def parse_detail(markup: str, url: str) -> dict[str, Any] | None:
    parser = _LinkTextParser(); parser.feed(markup); parts = parser.parts
    title = _value_after(parts, ("اسم المنافسة",))
    tender_number = _value_after(parts, ("رقم المنافسة",))
    reference = _value_after(parts, ("الرقم المرجعي",))
    purpose = _value_after(parts, ("الغرض من المنافسة",))
    buyer = _value_after(parts, ("الجهة الحكوميه", "الجهة الحكومية"))
    status = _value_after(parts, ("حالة المنافسة",))
    remaining = _value_after(parts, ("الوقت المتبقى",))
    booklet = _value_after(parts, ("قيمة وثائق المنافسة",))
    deadline = _value_after(parts, ("آخر موعد لتقديم العروض", "تاريخ انتهاء تقديم العروض"))
    if not title or any(token in f"{status} {remaining}" for token in ("إنتهى", "انتهى", "تم اعتماد الترسية", "تم اعلان الترسية", "مرحلة الترسية")):
        return None
    stable_id = reference or tender_number or re.sub(r"\W+", "-", title)[:60]
    return {
        "id": f"saudi-etimad-{stable_id}", "source": "Saudi Etimad", "source_url": url,
        "official_links": [url], "title_original": title, "title_tr": title, "description": purpose or None,
        "buyer-name": buyer or None, "buyer-country": "Saudi Arabia", "country": "Saudi Arabia",
        "deadline-receipt-tender-date-lot": deadline or None, "tender_number": tender_number or None,
        "reference_number": reference or None, "competition_status": status or None, "time_remaining": remaining or None,
        "tender_documents_value": booklet or None, "gulf_live_source": True,
        "foreign_supplier_eligibility_assumed": False,
        "source_provenance": {"source": url, "reference_number": reference or None, "parsed_from_official_detail_page": True},
    }


def collect_html() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    meta: dict[str, Any] = {"listing_url": LIST_URL, "listing_accessible": False, "detail_links": 0, "detail_failures": 0, "browser_fallback_used": False}
    try:
        listing = _fetch(LIST_URL); meta["listing_accessible"] = True
    except Exception as exc:
        meta["error"] = type(exc).__name__; listing = ""
    links = discover_detail_links(listing)
    if not links:
        try:
            listing = dump_dom(LIST_URL, virtual_time_ms=18000, timeout_seconds=45); meta["browser_fallback_used"] = True
            links = discover_detail_links(listing)
        except Exception as exc:
            meta["browser_fallback_error"] = f"{type(exc).__name__}:{exc}"
    meta["detail_links"] = len(links)
    rows: list[dict[str, Any]] = []
    for url in links:
        try:
            row = parse_detail(_fetch(url), url)
            if row: rows.append(row)
        except Exception:
            meta["detail_failures"] += 1
    return rows, meta


def collect() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    api_rows, api_meta = collect_api()
    if api_rows:
        return api_rows, {**api_meta, "collection_path": "official_json_api"}
    html_rows, html_meta = collect_html()
    return html_rows, {**api_meta, **html_meta, "collection_path": "html_fallback"}


def merge_payload(payload: dict[str, Any], rows: list[dict[str, Any]], meta: dict[str, Any]) -> dict[str, Any]:
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list): opportunities = []; payload["opportunities"] = opportunities
    seen = {str(x.get("id")) for x in opportunities if isinstance(x, dict)}; added = 0
    for row in rows:
        if row["id"] not in seen: opportunities.append(row); seen.add(row["id"]); added += 1
    status = "ok" if rows else ("source_unavailable" if meta.get("api_errors") and not meta.get("listing_accessible") else "no_active_parseable_tenders")
    payload["saudi_etimad_feed"] = {
        "source": API_URL, "status": status, "parsed_opportunities": len(rows), "added": added,
        "live_ingestion": bool(rows), "foreign_supplier_eligibility_assumed": False, **meta,
    }
    return payload


def main(path: str) -> None:
    p = Path(path); payload = json.loads(p.read_text(encoding="utf-8")); rows, meta = collect(); merge_payload(payload, rows, meta)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SAUDI_ETIMAD_FEED", json.dumps(payload["saudi_etimad_feed"], ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2: raise SystemExit("usage: python -m src.saudi_etimad_feed <payload.json>")
    main(sys.argv[1])
