from __future__ import annotations

import json
import sys

from .gulf_endpoint_discovery import _fetch_text, discover


SOURCES = {
    "saudi_etimad": "https://tenders.etimad.sa/Tender/AllTendersForVisitor?PageNumber=1&PageSize=20&PublishDateId=5&Sort=SubmitionDate&SortDirection=DESC",
    "uae_mof_en": "https://mof.gov.ae/en/public-finance/government-procurement/current-business-opportunities/",
    "uae_mof_ar": "https://mof.gov.ae/ar/public-finance/government-procurement/current-business-opportunities/",
}


def probe() -> dict[str, object]:
    results: dict[str, object] = {}
    for name, url in SOURCES.items():
        try:
            markup = _fetch_text(url, timeout=20)
            finding = discover(markup, url, max_scripts=10)
            finding["html_bytes"] = len(markup.encode("utf-8"))
            finding["page_fetch"] = "ok"
        except Exception as exc:
            finding = {
                "page_fetch": "error",
                "error": type(exc).__name__,
                "same_origin_scripts_seen": 0,
                "same_origin_scripts_fetched": 0,
                "endpoint_hints": [],
            }
        results[name] = finding
    return results


def main() -> None:
    # Diagnostics are ephemeral CI logs only. No raw HTML, cookies or headers are stored.
    print("GULF_ENDPOINT_PROBE", json.dumps(probe(), ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    main()
