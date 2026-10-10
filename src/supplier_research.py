from __future__ import annotations

from typing import Any


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return " ".join(_text(v) for v in value if _text(v)).strip()
    if isinstance(value, dict):
        return " ".join(_text(v) for v in value.values() if _text(v)).strip()
    return str(value).strip()


def prepare(item: dict[str, Any]) -> dict[str, Any]:
    spec = item.get("specification_analysis") or {}
    product = _text(((item.get("field_evidence") or {}).get("product") or {}).get("value")) or _text(item.get("product_name") or item.get("title_tr") or item.get("title_original"))
    country = _text(((item.get("field_evidence") or {}).get("country") or {}).get("value")) or _text(item.get("country") or item.get("buyer-country"))
    ready = bool(product) and bool(spec.get("supplier_sourcing_ready"))
    result = {
        "status": "research_ready" if ready else "specification_review_pending",
        "dossier_ready": ready,
        "product": product or None,
        "buyer_country": country or None,
        "search_query": f'"{product}" manufacturer exporter' if ready else None,
        "candidate_suppliers": [],
        "verified_supplier_count": 0,
        "verification_required": True,
        "blocked_by_missing_fields": [] if ready else ["specification_evidence"],
        "rule": "A supplier name is never treated as verified without a source URL, product match and explicit verification evidence.",
    }
    item["supplier_research"] = result
    return result


def process_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("opportunities") or []
    ready = 0
    for item in rows:
        if isinstance(item, dict) and prepare(item)["dossier_ready"]:
            ready += 1
    payload["supplier_research_summary"] = {
        "opportunities": len(rows),
        "research_ready": ready,
        "blocked": max(0, len(rows) - ready),
        "verified_suppliers": 0,
        "mode": "research_queue_only",
    }
    return payload
