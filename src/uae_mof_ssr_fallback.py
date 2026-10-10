from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

from .browser_render import dump_dom
from .uae_mof_feed import BROWSER_USER_AGENT, SOURCE_URL, parse

# The MOF page intermittently returns an empty shell for the default route on
# hosted runners while server-rendered tender rows are available when the
# official page is requested with a ministry filter. This fallback deliberately
# treats the result as PARTIAL coverage, never as a complete UAE tender feed.
BOOTSTRAP_MINISTRY = "The General Authority for Islamic Affairs and Endowments - (296/16880)"
BOOTSTRAP_URL = f"{SOURCE_URL}?{urlencode({'mof-dpp-ministry': BOOTSTRAP_MINISTRY, 'mof-dpp-page': 1})}"
TIMEOUT_SECONDS = 20
BROWSER_TIMEOUT_SECONDS = 16
BROWSER_VIRTUAL_TIME_MS = 4000


def _fetch(url: str = BOOTSTRAP_URL) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
        return response.read().decode("utf-8", "replace")


def apply(payload: dict) -> dict:
    current = payload.get("uae_mof_feed") or {}
    if current.get("live_ingestion"):
        current["ssr_fallback_attempted"] = False
        payload["uae_mof_feed"] = current
        return payload

    # Try the official filtered route over HTTP first, then a bounded public
    # browser render if the page is empty or the HTTP request fails.
    # Neither path bypasses login, CAPTCHA, cookies or private APIs.
    rows = []
    errors = []
    successful_transport = None
    try:
        rows = parse(_fetch(), SOURCE_URL)
        if rows:
            successful_transport = "official_filtered_http"
    except Exception as exc:
        errors.append(f"http:{type(exc).__name__}")

    if not rows:
        try:
            rendered = dump_dom(
                BOOTSTRAP_URL,
                virtual_time_ms=BROWSER_VIRTUAL_TIME_MS,
                timeout_seconds=BROWSER_TIMEOUT_SECONDS,
            )
            rows = parse(rendered, SOURCE_URL)
            if rows:
                successful_transport = "official_filtered_browser"
        except Exception as exc:
            errors.append(f"browser:{type(exc).__name__}")

    current["ssr_fallback_attempted"] = True
    current["ssr_browser_fallback_attempted"] = successful_transport != "official_filtered_http"
    current["ssr_fallback_transport"] = successful_transport
    if errors:
        current["ssr_fallback_errors"] = errors

    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        opportunities = []
        payload["opportunities"] = opportunities
    seen = {str(x.get("id")) for x in opportunities if isinstance(x, dict)}
    added = 0
    for row in rows:
        if row.get("id") not in seen:
            opportunities.append(row)
            seen.add(str(row.get("id")))
            added += 1

    if rows:
        current.update({
            "status": "ok",
            "parsed_opportunities": len(rows),
            "added": int(current.get("added") or 0) + added,
            "live_ingestion": True,
            "successful_route": successful_transport,
            "ssr_fallback_attempted": True,
            "ssr_fallback_status": "ok",
            "ssr_fallback_source": BOOTSTRAP_URL,
            "coverage_scope": "partial_official_listing",
            "coverage_complete": False,
            "foreign_supplier_eligibility_assumed": False,
        })
    else:
        current.update({
            "ssr_fallback_attempted": True,
            "ssr_fallback_status": "source_unavailable" if len(errors) == 2 else "no_rows_found",
            "coverage_scope": "not_verified",
        })
    payload["uae_mof_feed"] = current
    return payload


def main(path: str) -> None:
    p = Path(path)
    payload = json.loads(p.read_text(encoding="utf-8"))
    apply(payload)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("UAE_MOF_SSR_FALLBACK", json.dumps(payload.get("uae_mof_feed") or {}, ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.uae_mof_ssr_fallback <payload.json>")
    main(sys.argv[1])
