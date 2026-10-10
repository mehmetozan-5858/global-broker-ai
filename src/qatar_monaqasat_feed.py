from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from .browser_render import dump_dom

SOURCE_URL = "https://monaqasat.mof.gov.qa/TendersOnlineServices/AvailableMinistriesTenders/2"
ALT_SOURCE_URL = "https://monaqasat.mof.gov.qa/TendersOnlineServices/AvailableMinistriesTenders/1"
SOURCE_URLS = (SOURCE_URL, ALT_SOURCE_URL)
TENDER_NO = re.compile(r"\b\d{3,5}/20\d{2}\b")
DATE = re.compile(r"\b\d{2}/\d{2}/20\d{2}\b")
GOODS_WORDS = ("supply", "supplies", "medical consumables", "equipment", "items", "توريد", "شراء")
SERVICE_WORDS = ("service", "services", "maintenance", "consult", "campaign", "event", "خدمات", "صيانة", "استشار")
WORKS_WORDS = ("works", "construction", "renovation", "أعمال", "مقاولات")


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._anchor_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._anchor_parts = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        self.parts.append(text)
        if self._href is not None:
            self._anchor_parts.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            label = " ".join(self._anchor_parts).strip()
            if label:
                self.links.append((label, self._href))
            self._href = None
            self._anchor_parts = []


def _fetch(url: str, timeout: int = 14) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ar,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def _segment_text(markup: str) -> tuple[str, list[tuple[str, str]]]:
    parser = _TextParser()
    parser.feed(markup)
    return " \n ".join(parser.parts), parser.links


def _field(segment: str, start_terms: tuple[str, ...], end_terms: tuple[str, ...]) -> str:
    low = segment.lower()
    positions = [(low.find(term.lower()), term) for term in start_terms if low.find(term.lower()) >= 0]
    if not positions:
        return ""
    start, term = min(positions, key=lambda x: x[0])
    start += len(term)
    end_candidates = [low.find(end.lower(), start) for end in end_terms]
    end_candidates = [x for x in end_candidates if x >= 0]
    end = min(end_candidates) if end_candidates else len(segment)
    return " ".join(segment[start:end].split()).strip(" :-")


def _detail_url(number: str, subject: str, links: list[tuple[str, str]], source_url: str) -> str:
    needles = {number.lower(), subject[:40].lower()}
    for label, href in links:
        ll = label.lower()
        if any(n and n in ll for n in needles):
            return urljoin(source_url, html.unescape(href))
    return source_url


def _physical_goods_subject(subject: str) -> bool:
    low = subject.lower()
    goods = sum(word in low for word in GOODS_WORDS)
    services = sum(word in low for word in SERVICE_WORDS)
    works = sum(word in low for word in WORKS_WORDS)
    return goods > 0 and goods > services and goods > works


def parse(markup: str, source_url: str = SOURCE_URL) -> list[dict[str, Any]]:
    flat, links = _segment_text(markup)
    matches = list(TENDER_NO.finditer(flat))
    rows: list[dict[str, Any]] = []
    for i, match in enumerate(matches):
        number = match.group(0)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(flat)
        segment = flat[match.end():end]
        marker_positions = [x for x in (segment.lower().find("publish date"), segment.find("تاريخ الطرح")) if x >= 0]
        subject = " ".join(segment[:min(marker_positions)].split()).strip(" :-") if marker_positions else ""
        if not subject or not _physical_goods_subject(subject):
            continue
        publish = _field(segment, ("Publish date", "تاريخ الطرح"), ("Requested Sector Type", "نوع القطاع المطلوب", "Tender Bond", "التأمين المؤقت"))
        close = _field(segment, ("Close date", "تاريخ الإغلاق"), ("Purchase", "شراء", "Company size", "حجم الشركة"))
        buyer = _field(segment, ("Ministry", "الجهة"), ("Type", "النوع"))
        bond = _field(segment, ("Tender Bond (QAR)", "Tender Bond", "التأمين المؤقت"), ("Documents value", "قيمة الوثائق", "Ministry", "الجهة"))
        dates = DATE.findall(segment)
        if not publish and dates:
            publish = dates[0]
        if not close and len(dates) > 1:
            close = dates[-1]
        url = _detail_url(number, subject, links, source_url)
        rows.append({
            "id": f"qatar-monaqasat-{number.replace('/','-')}",
            "source": "Qatar Monaqasat",
            "source_url": url,
            "official_links": [url],
            "title_original": subject,
            "title_tr": subject,
            "buyer-name": buyer or None,
            "buyer-country": "Qatar",
            "country": "Qatar",
            "publication-date": publish or None,
            "deadline-receipt-tender-date-lot": close or None,
            "bid_bond": f"QAR {bond}" if bond else None,
            "contract-nature": "supplies",
            "procurement_category": "goods",
            "gulf_live_source": True,
            "foreign_supplier_eligibility_assumed": False,
            "source_provenance": {"source": source_url, "tender_number": number, "parsed_from_public_listing": True},
        })
    return rows


def collect(budget_seconds: int = 55) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    started = time.monotonic()
    errors: list[str] = []
    attempts = 0
    browser_routes: list[str] = []

    # First try normal HTTPS against both official public routes.
    for source_url in SOURCE_URLS:
        attempts += 1
        try:
            markup = _fetch(source_url)
            rows = parse(markup, source_url)
            if rows:
                return rows, {
                    "successful_route": source_url,
                    "attempts": attempts,
                    "errors": errors,
                    "browser_fallback_used": False,
                    "browser_routes": browser_routes,
                    "elapsed_seconds": round(time.monotonic() - started, 2),
                    "budget_seconds": budget_seconds,
                }
            errors.append(f"{source_url}:no_tradeable_goods_found")
        except Exception as exc:
            errors.append(f"{source_url}:http:{type(exc).__name__}")

    # Monaqasat can reject datacenter urllib traffic while still rendering in a real browser.
    # Keep this fallback bounded so Qatar can never stall the whole Shadow Scan.
    for source_url in SOURCE_URLS:
        if time.monotonic() - started >= budget_seconds:
            break
        attempts += 1
        try:
            rendered = dump_dom(source_url, virtual_time_ms=9000, timeout_seconds=18)
            browser_routes.append(source_url)
            rows = parse(rendered, source_url)
            if rows:
                return rows, {
                    "successful_route": source_url,
                    "attempts": attempts,
                    "errors": errors,
                    "browser_fallback_used": True,
                    "browser_routes": browser_routes,
                    "elapsed_seconds": round(time.monotonic() - started, 2),
                    "budget_seconds": budget_seconds,
                }
            errors.append(f"{source_url}:browser:no_tradeable_goods_found")
        except Exception as exc:
            errors.append(f"{source_url}:browser:{type(exc).__name__}:{exc}")

    return [], {
        "successful_route": None,
        "attempts": attempts,
        "errors": errors,
        "browser_fallback_used": bool(browser_routes),
        "browser_routes": browser_routes,
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "budget_seconds": budget_seconds,
        "budget_exhausted": time.monotonic() - started >= budget_seconds,
    }


def merge_payload(payload: dict[str, Any], rows: list[dict[str, Any]], meta: dict[str, Any] | None = None) -> dict[str, Any]:
    meta = meta or {}
    existing = payload.get("opportunities")
    if not isinstance(existing, list):
        existing = []
        payload["opportunities"] = existing
    seen = {str(x.get("id")) for x in existing if isinstance(x, dict)}
    added = 0
    for row in rows:
        if row["id"] not in seen:
            existing.append(row)
            seen.add(row["id"])
            added += 1
    errors = list(meta.get("errors") or [])
    payload["qatar_monaqasat_feed"] = {
        "source": meta.get("successful_route") or SOURCE_URL,
        "alternate_official_source": ALT_SOURCE_URL,
        "status": "ok" if rows else ("source_unavailable" if errors and all("no_tradeable_goods_found" not in x for x in errors) else "no_tradeable_goods_found"),
        "parsed_goods": len(rows),
        "added": added,
        "live_ingestion": bool(rows),
        "foreign_supplier_eligibility_assumed": False,
        "successful_route": meta.get("successful_route"),
        "attempts": int(meta.get("attempts") or 0),
        "errors": errors,
        "browser_fallback_used": bool(meta.get("browser_fallback_used")),
        "browser_routes": meta.get("browser_routes") or [],
        "elapsed_seconds": meta.get("elapsed_seconds"),
        "budget_seconds": meta.get("budget_seconds"),
        "budget_exhausted": bool(meta.get("budget_exhausted")),
    }
    return payload


def main(path: str) -> None:
    p = Path(path)
    payload = json.loads(p.read_text(encoding="utf-8"))
    rows, meta = collect()
    merge_payload(payload, rows, meta)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("QATAR_MONAQASAT", json.dumps(payload["qatar_monaqasat_feed"], ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.qatar_monaqasat_feed <payload.json>")
    main(sys.argv[1])
