from __future__ import annotations

from collections import Counter
from typing import Any


_BLOCKER_AGENT = {
    "unit_price": "price_agent",
    "verified_supplier_quote": "price_agent",
    "freight": "logistics_agent",
    "destination": "logistics_agent",
    "quantity": "source_terms_agent",
    "currency": "source_terms_agent",
}


def _next_agent(blockers: list[str], missing: list[str]) -> str:
    """Route research to the narrowest agent without inventing missing facts."""
    ordered = blockers + [x for x in missing if x not in blockers]
    for key in ("unit_price", "verified_supplier_quote", "freight", "destination", "quantity", "currency"):
        if key in ordered:
            return _BLOCKER_AGENT[key]
    return "commercial_research_agent"


def _priority_score(verified_supplier_count: int, blockers: list[str], source: str | None) -> int:
    """Prioritize cases closest to a real commercial calculation.

    A verified supplier is the strongest signal. Official source availability is
    useful, while every unresolved blocker reduces closability. The score is a
    queueing aid only; it is never presented as deal probability or margin.
    """
    score = 0
    if verified_supplier_count > 0:
        score += 100
    score += min(verified_supplier_count, 3) * 10
    if source:
        score += 15
    score += max(0, 30 - 6 * len(blockers))
    return score


def build(payload: dict[str, Any]) -> dict[str, Any]:
    """Summarize actual blockers without inventing quotes, prices or eligibility."""
    rows = [row for row in (payload.get("opportunities") or []) if isinstance(row, dict)]
    blockers: Counter[str] = Counter()
    missing: Counter[str] = Counter()
    queue: list[dict[str, Any]] = []
    supplier_ready_count = 0
    for row in rows:
        feasibility = row.get("commercial_feasibility") or {}
        supplier = row.get("supplier_research") or {}
        field = row.get("field_evidence") or {}
        row_blockers = list(feasibility.get("blockers") or [])
        row_missing = list(feasibility.get("missing_inputs") or [])
        blockers.update(row_blockers)
        missing.update(row_missing)
        if feasibility.get("calculation_ready") is True:
            continue
        source = next(
            (row.get(k) for k in ("source_url", "source-url", "notice_url", "detail_url", "tender_url", "url")
             if isinstance(row.get(k), str) and row.get(k).startswith("https://")),
            None,
        )
        product = (field.get("product") or {}).get("value")
        verified_supplier_count = int(supplier.get("verified_supplier_count") or 0)
        supplier_ready = verified_supplier_count > 0
        if supplier_ready:
            supplier_ready_count += 1
        priority_score = _priority_score(verified_supplier_count, row_blockers, source)
        # Source-backed research instructions, not a permission to contact anyone.
        queue.append({
            "opportunity_id": row.get("id") or row.get("opportunity_id") or row.get("publication-number") or row.get("notice_id"),
            "product": product,
            "source_url": source,
            "missing_commercial_inputs": row_missing,
            "blocking_commercial_inputs": row_blockers,
            "verified_supplier_count": verified_supplier_count,
            "supplier_ready": supplier_ready,
            "priority_score": priority_score,
            "next_agent": _next_agent(row_blockers, row_missing),
            "research_only": True,
            "human_approval_required": True,
        })
    queue.sort(key=lambda item: (
        -int(item["supplier_ready"]),
        -int(item["priority_score"]),
        -len(item["blocking_commercial_inputs"]),
        str(item["product"] or ""),
    ))
    result = {
        "opportunities_reviewed": len(rows),
        "calculation_ready": sum(
            (row.get("commercial_feasibility") or {}).get("calculation_ready") is True
            for row in rows
        ),
        "supplier_ready_blocked": supplier_ready_count,
        "blocker_counts": dict(sorted(blockers.items(), key=lambda pair: (-pair[1], pair[0]))),
        "missing_input_counts": dict(sorted(missing.items(), key=lambda pair: (-pair[1], pair[0]))),
        "research_queue_count": len(queue),
        "research_queue": queue[:50],
        "queue_truncated": len(queue) > 50,
        "queue_rule": "Verified-supplier opportunities are researched first; scores are workflow priority only, never probability or profit claims.",
        "no_fabricated_prices_or_quotes": True,
        "external_outreach_enabled": False,
    }
    payload["commercial_blocker_triage"] = result
    return result
