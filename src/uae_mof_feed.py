from __future__ import annotations

import html
import json
import sys
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urljoin

from .browser_render import dump_dom

SOURCE_URL = "https://mof.gov.ae/en/public-finance/government-procurement/current-business-opportunities/"
AR_SOURCE_URL = "https://mof.gov.ae/ar/public-finance/government-procurement/current-business-opportunities/"
SOURCE_URLS = (SOURCE_URL, AR_SOURCE_URL)
HTTP_TIMEOUT_SECONDS = 12
BROWSER_TIMEOUT_SECONDS = 18
BROWSER_VIRTUAL_TIME_MS = 7000
COLLECT_BUDGET_SECONDS = 70
BROWSER_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_tr = False
        self.in_td = False
        self.rows: list[list[dict[str, str]]] = []
        self.row: list[dict[str, str]] = []
        self.text: list[str] = []
        self.href = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.in_tr = True
            self.row = []
        elif tag in {"td", "th"} and self.in_tr:
            self.in_td = True
            self.text = []
            self.href = ""
        elif tag == "a" and self.in_td:
            self.href = dict(attrs).get("href") or self.href

    def handle_data(self, data: str) -> None:
        if self.in_td:
            text = " ".join(data.split())
            if text:
                self.text.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.in_td:
            self.row.append({"text": " ".join(self.text).strip(), "href": self.href})
            self.in_td = False
        elif tag == "tr" and self.in_tr:
            if self.row:
                self.rows.append(self.row)
            self.in_tr = False


def _fetch_url(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as response:
        return response.read().decode("utf-8", "replace")


def page_url(page: int = 1, source_url: str = SOURCE_URL) -> str:
    return f"{source_url}?{urlencode({'mof-dpp-page': page})}"


def parse(markup: str, source_url: str = SOURCE_URL) -> list[dict[str, Any]]:
    parser = _TableParser()
    parser.feed(markup)
    results: list[dict[str, Any]] = []
    for cells in parser.rows:
        if len(cells) < 5:
            continue
        first = cells[0]["text"].strip()
        if not first.isdigit():
            continue
        rfq = first
        entity = cells[1]["text"].strip() if len(cells) > 1 else ""
        title = cells[2]["text"].strip() if len(cells) > 2 else ""
        open_date = cells[3]["text"].strip() if len(cells) > 3 else ""
        close_date = cells[4]["text"].strip() if len(cells) > 4 else ""
        href = ""
        for cell in cells[5:]:
            if cell.get("href"):
                href = urljoin(source_url, html.unescape(cell["href"]))
                break
        if not title:
            continue
        results.append({
            "id": f"uae-mof-{rfq}",
            "source": "UAE Ministry of Finance - Current Business Opportunities",
            "source_url": href or source_url,
            "official_links": [href or source_url],
            "title_original": title,
            "title_tr": title,
            "buyer-name": entity or None,
            "buyer-country": "United Arab Emirates",
            "country": "United Arab Emirates",
            "publication-date": open_date or None,
            "deadline-receipt-tender-date-lot": close_date or None,
            "rfq_number": rfq,
            "gulf_live_source": True,
            "foreign_supplier_eligibility_assumed": False,
            "source_provenance": {
                "source": source_url,
                "rfq_number": rfq,
                "parsed_from_public_listing": True,
            },
        })
    return results


def _collect_page(page: int, source_url: str, meta: dict[str, Any], *, allow_browser: bool) -> list[dict[str, Any]]:
    url = page_url(page, source_url)
    route = "ar" if source_url == AR_SOURCE_URL else "en"
    try:
        markup = _fetch_url(url)
        rows = parse(markup, source_url)
    except Exception as exc:
        meta["errors"].append(f"route={route}:page={page}:http:{type(exc).__name__}")
        rows = []
    if not rows and allow_browser:
        try:
            rendered = dump_dom(
                url,
                virtual_time_ms=BROWSER_VIRTUAL_TIME_MS,
                timeout_seconds=BROWSER_TIMEOUT_SECONDS,
            )
            rows = parse(rendered, source_url)
            meta["browser_fallback_pages"].append(f"{route}:{page}")
        except Exception as exc:
            meta["errors"].append(f"route={route}:page={page}:browser:{type(exc).__name__}:{exc}")
    if rows:
        meta["successful_route"] = route
    return rows


def collect(max_pages: int = 2) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    combined: list[dict[str, Any]] = []
    seen: set[str] = set()
    started = time.monotonic()
    meta: dict[str, Any] = {
        "errors": [],
        "browser_fallback_pages": [],
        "successful_route": None,
        "budget_seconds": COLLECT_BUDGET_SECONDS,
        "budget_exhausted": False,
    }
    for page in range(1, max_pages + 1):
        rows: list[dict[str, Any]] = []
        for source_url in SOURCE_URLS:
            if time.monotonic() - started >= COLLECT_BUDGET_SECONDS:
                meta["budget_exhausted"] = True
                break
            rows = _collect_page(page, source_url, meta, allow_browser=(page == 1))
            if rows:
                break
        new_rows = [row for row in rows if row["id"] not in seen]
        if not new_rows:
            break
        for row in new_rows:
            seen.add(row["id"])
            combined.append(row)
        if meta["budget_exhausted"]:
            break
    meta["rendered_fallback_used"] = bool(meta["browser_fallback_pages"])
    meta["elapsed_seconds"] = round(time.monotonic() - started, 2)
    return combined, meta


def merge_payload(payload: dict[str, Any], rows: list[dict[str, Any]], meta: dict[str, Any] | None = None) -> dict[str, Any]:
    meta = meta or {}
    errors = list(meta.get("errors") or [])
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
    payload["uae_mof_feed"] = {
        "source": SOURCE_URL,
        "alternate_official_source": AR_SOURCE_URL,
        "status": "ok" if rows else ("source_unavailable" if errors else "no_rows_found"),
        "parsed_opportunities": len(rows),
        "added": added,
        "live_ingestion": bool(rows),
        "foreign_supplier_eligibility_assumed": False,
        "errors": errors,
        "successful_route": meta.get("successful_route"),
        "rendered_fallback_used": bool(meta.get("rendered_fallback_used")),
        "browser_fallback_pages": meta.get("browser_fallback_pages") or [],
        "budget_seconds": meta.get("budget_seconds"),
        "budget_exhausted": bool(meta.get("budget_exhausted")),
        "elapsed_seconds": meta.get("elapsed_seconds"),
    }
    return payload


def main(path: str) -> None:
    p = Path(path)
    payload = json.loads(p.read_text(encoding="utf-8"))
    rows, meta = collect()
    merge_payload(payload, rows, meta)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("UAE_MOF_FEED", json.dumps(payload["uae_mof_feed"], ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.uae_mof_feed <payload.json>")
    main(sys.argv[1])
