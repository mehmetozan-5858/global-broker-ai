from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


NUMERIC_ONLY = re.compile(r"^[\d\s,;/.-]+$")


def is_readable_product(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text) and not bool(NUMERIC_ONLY.fullmatch(text))


def validate(payload: dict[str, Any]) -> dict[str, int]:
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        raise AssertionError("opportunities must be a list")

    enrichment = payload.get("enrichment") or {}
    if enrichment.get("mode") != "source_only_no_hallucination":
        raise AssertionError("source-only enrichment marker missing")

    dossier_count = 0
    readable_product_count = 0
    source_link_count = 0
    supplier_query_count = 0
    raw_numeric_supplier_query_count = 0
    china_queue_count = 0

    for item in opportunities:
        if not isinstance(item, dict):
            continue
        dossier = item.get("dossier")
        if isinstance(dossier, dict):
            dossier_count += 1
            if is_readable_product(dossier.get("product_name")):
                readable_product_count += 1
            links = dossier.get("official_links")
            if isinstance(links, list) and links:
                source_link_count += 1

        supplier = item.get("supplier_research")
        if isinstance(supplier, dict):
            query = supplier.get("product_query")
            if query:
                supplier_query_count += 1
                if not is_readable_product(query):
                    raw_numeric_supplier_query_count += 1

        workflow = item.get("workflow")
        if isinstance(workflow, dict) and isinstance(workflow.get("china_market_research"), dict):
            china_queue_count += 1

    if opportunities and dossier_count != len(opportunities):
        raise AssertionError(f"dossier missing: {dossier_count}/{len(opportunities)}")
    if opportunities and readable_product_count == 0:
        raise AssertionError("no readable product names were produced")
    if raw_numeric_supplier_query_count:
        raise AssertionError(
            f"{raw_numeric_supplier_query_count} supplier queries are still numeric-only"
        )

    return {
        "opportunities": len(opportunities),
        "dossiers": dossier_count,
        "readable_products": readable_product_count,
        "with_official_links": source_link_count,
        "supplier_queries": supplier_query_count,
        "numeric_only_supplier_queries": raw_numeric_supplier_query_count,
        "china_research_queue": china_queue_count,
    }


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.validate_live_output <json-file>")
    path = Path(sys.argv[1])
    payload = json.loads(path.read_text(encoding="utf-8"))
    summary = validate(payload)
    print("LIVE_OUTPUT_VALIDATION " + json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
