from __future__ import annotations

import html
import json
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urljoin

SOURCE_URL = "https://mof.gov.ae/en/public-finance/government-procurement/current-business-opportunities/"


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


def _fetch(page: int = 1) -> str:
    query = urlencode({"mof-dpp-page": page})
    req = urllib.request.Request(
        f"{SOURCE_URL}?{query}",
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; GlobalBrokerAI/1.0; +https://github.com/mehmetozan-5858/global-broker-ai)",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=35) as response:
        return response.read().decode("utf-8", "replace")


def parse(markup: str) -> list[dict[str, Any]]:
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
                href = urljoin(SOURCE_URL, html.unescape(cell["href"]))
                break
        if not title:
            continue
        results.append({
            "id": f"uae-mof-{rfq}",
            "source": "UAE Ministry of Finance - Current Business Opportunities",
            "source_url": href or SOURCE_URL,
            "official_links": [href or SOURCE_URL],
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
                "source": SOURCE_URL,
                "rfq_number": rfq,
                "parsed_from_public_listing": True,
            },
        })
    return results


def collect(max_pages: int = 4) -> tuple[list[dict[str, Any]], list[str]]:
    combined: list[dict[str, Any]] = []
    seen: set[str] = set()
    errors: list[str] = []
    for page in range(1, max_pages + 1):
        try:
            rows = parse(_fetch(page))
        except Exception as exc:
            errors.append(f"page={page}:{type(exc).__name__}")
            if page == 1:
                break
            continue
        new_rows = [row for row in rows if row["id"] not in seen]
        if not new_rows:
            if page > 1:
                break
        for row in new_rows:
            seen.add(row["id"])
            combined.append(row)
    return combined, errors


def merge_payload(payload: dict[str, Any], rows: list[dict[str, Any]], errors: list[str] | None = None) -> dict[str, Any]:
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
        "status": "ok" if rows else ("source_unavailable" if errors else "no_rows_found"),
        "parsed_opportunities": len(rows),
        "added": added,
        "live_ingestion": bool(rows),
        "foreign_supplier_eligibility_assumed": False,
        "errors": errors or [],
    }
    return payload


def main(path: str) -> None:
    p = Path(path)
    payload = json.loads(p.read_text(encoding="utf-8"))
    rows, errors = collect()
    merge_payload(payload, rows, errors)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("UAE_MOF_FEED", json.dumps(payload["uae_mof_feed"], ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.uae_mof_feed <payload.json>")
    main(sys.argv[1])
