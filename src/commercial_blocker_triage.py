from __future__ import annotations

from collections import Counter
from typing import Any


def build(payload: dict[str, Any]) -> dict[str, Any]:
    """Summarize actual blockers without inventing quotes, prices or eligibility."""
    rows = [row for row in (payload.get("opportunities") or []) if isinstance(row, dict)]
    blockers: Counter[str] = Counter()
    missing: Counter[str] = Counter()
    queue: list[dict[str, Any]] = []
    for row in rows:
        feasibility = row.get("commercial_feasibility") or {}
        supplier = row.get("supplier_research") or {}
        field = row.get("field_evidence") or {}
        row_blockers = list(feasibility.get("blockers") or [])
        blockers.update(row_blockers)
        missing.update(feasibility.get("missing_inputs") or [])
        if feasibility.get("calculation_ready") is True:
            continue
        source = next(
            (row.get(k) for k in ("source_url", "source-url", "notice_url", "detail_url", "tender_url", "url")
             if isinstance(row.get(k), str) and row.get(k).startswith("https://")),
            None,
        )
        product = (field.get("product") or {}).get("value")
        # Source-backed research instructions, not a permission to contact anyone.
        queue.append({
            "opportunity_id": row.get("id") or row.get("publication-number") or row.get("notice_id"),
            "product": product,
            "source_url": source,
            "missing_commercial_inputs": list(feasibility.get("missing_inputs") or []),
            "blocking_commercial_inputs": row_blockers,
            "verified_supplier_count": int(supplier.get("verified_supplier_count") or 0),
            "research_only": True,
            "human_approval_required": True,
        })
    queue.sort(key=lambda item: (
        -len(item["blocking_commercial_inputs"]),
        str(item["product"] or ""),
    ))
    result = {
        "opportunities_reviewed": len(rows),
        "calculation_ready": sum(
            (row.get("commercial_feasibility") or {}).get("calculation_ready") is True
            for row in rows
        ),
        "blocker_counts": dict(sorted(blockers.items(), key=lambda pair: (-pair[1], pair[0]))),
        "missing_input_counts": dict(sorted(missing.items(), key=lambda pair: (-pair[1], pair[0]))),
        "research_queue_count": len(queue),
        "research_queue": queue[:50],
        "queue_truncated": len(queue) > 50,
        "no_fabricated_prices_or_quotes": True,
        "external_outreach_enabled": False,
    }
    payload["commercial_blocker_triage"] = result
    return result
