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


def validate(payload: dict[str, Any]) -> dict[str, Any]:
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        raise AssertionError("opportunities must be a list")

    enrichment = payload.get("enrichment") or {}
    if enrichment.get("mode") != "source_only_no_hallucination":
        raise AssertionError("source-only enrichment marker missing")

    specification_meta = payload.get("specification_analysis") or {}
    if opportunities and specification_meta.get("mode") != "source_evidence_only":
        raise AssertionError("source-backed specification analysis marker missing")

    dossier_count = 0
    readable_product_count = 0
    source_link_count = 0
    supplier_query_count = 0
    raw_numeric_supplier_query_count = 0
    china_queue_count = 0
    specification_count = 0
    specification_structured = 0
    specification_narrative_ready = 0
    specification_document_pending = 0
    specification_insufficient = 0
    specification_detail_missing = 0
    specification_attachment_pending = 0
    specification_sourcing_ready = 0

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

        spec = item.get("specification_analysis")
        if isinstance(spec, dict):
            specification_count += 1
            status = spec.get("status")
            if status == "structured_specification_analyzed":
                specification_structured += 1
            elif status == "source_description_analyzed":
                specification_narrative_ready += 1
            elif status == "document_analysis_pending":
                specification_document_pending += 1
            elif status == "source_description_insufficient":
                specification_insufficient += 1
            elif status == "source_detail_missing":
                specification_detail_missing += 1
            if spec.get("attachment_requires_parsing"):
                specification_attachment_pending += 1
            if spec.get("supplier_sourcing_ready"):
                specification_sourcing_ready += 1

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
    if opportunities and specification_count != len(opportunities):
        raise AssertionError(f"specification analysis missing: {specification_count}/{len(opportunities)}")
    if opportunities and readable_product_count == 0:
        raise AssertionError("no readable product names were produced")
    if raw_numeric_supplier_query_count:
        raise AssertionError(
            f"{raw_numeric_supplier_query_count} supplier queries are still numeric-only"
        )

    ccgp = payload.get("china_feed") or {}
    ggzy = payload.get("china_ggzy_feed") or {}
    radar = payload.get("china_import_radar") or {}
    radar_meta = radar.get("meta") if isinstance(radar, dict) else {}
    radar_items = radar.get("items") if isinstance(radar, dict) else []
    if not isinstance(radar_meta, dict):
        radar_meta = {}
    if not isinstance(radar_items, list):
        radar_items = []

    return {
        "opportunities": len(opportunities),
        "dossiers": dossier_count,
        "readable_products": readable_product_count,
        "with_official_links": source_link_count,
        "supplier_queries": supplier_query_count,
        "numeric_only_supplier_queries": raw_numeric_supplier_query_count,
        "specification_analyzed": specification_count,
        "specification_sourcing_ready": specification_sourcing_ready,
        "specification_structured": specification_structured,
        "specification_narrative_ready": specification_narrative_ready,
        "specification_document_pending": specification_document_pending,
        "specification_insufficient": specification_insufficient,
        "specification_detail_missing": specification_detail_missing,
        "specification_attachment_pending": specification_attachment_pending,
        "china_research_queue": china_queue_count,
        "china_ccgp_status": ccgp.get("status", "not_configured"),
        "china_ccgp_goods_added": int(ccgp.get("goods_opportunities_added") or 0),
        "china_ggzy_status": ggzy.get("status", "not_configured"),
        "china_ggzy_candidates": int(ggzy.get("candidate_goods_links") or 0),
        "china_ggzy_goods_added": int(ggzy.get("goods_opportunities_added") or 0),
        "china_import_radar_status": radar_meta.get("status", "not_configured"),
        "china_import_products_monitored": int(radar_meta.get("products_monitored") or 0),
        "china_import_products_with_data": int(radar_meta.get("products_with_data") or 0),
        "china_import_radar_items": len(radar_items),
        "china_import_radar_year": radar_meta.get("current_year"),
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
