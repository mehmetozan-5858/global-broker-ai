from __future__ import annotations

from collections import Counter
from typing import Any

AGENTS = (
    "source",
    "goods_gate",
    "field_evidence",
    "specification",
    "supplier",
    "feasibility",
    "risk",
    "sales_priority",
)


def build(payload: dict[str, Any]) -> dict[str, Any]:
    rows = [x for x in (payload.get("opportunities") or []) if isinstance(x, dict)]
    stage_counts: dict[str, Counter] = {name: Counter() for name in AGENTS}

    for item in rows:
        stage_counts["source"]["has_official_link" if item.get("official_links") or item.get("source_url") else "missing_link"] += 1
        goods = (item.get("export_goods_review") or {}).get("status") or "unknown"
        stage_counts["goods_gate"][goods] += 1
        coverage = item.get("core_field_coverage") or {}
        stage_counts["field_evidence"]["complete" if coverage.get("complete") else "incomplete"] += 1
        spec = item.get("specification_analysis") or {}
        stage_counts["specification"][spec.get("status") or "not_run"] += 1
        supplier = item.get("supplier_research") or {}
        stage_counts["supplier"][supplier.get("status") or "not_run"] += 1
        feasibility = item.get("commercial_feasibility") or {}
        stage_counts["feasibility"][feasibility.get("status") or "not_run"] += 1
        verification = item.get("buyer_verification") or item.get("verification") or {}
        stage_counts["risk"][verification.get("status") or "pending"] += 1
        priority = item.get("sales_priority") or {}
        stage_counts["sales_priority"][priority.get("grade") or priority.get("status") or "ungraded"] += 1

    center = {
        "mode": "shadow",
        "external_actions_enabled": False,
        "opportunity_count": len(rows),
        "agents": {name: dict(counter) for name, counter in stage_counts.items()},
        "policy": {
            "email_send": False,
            "bid_submit": False,
            "payment": False,
            "order": False,
            "human_approval_required": True,
        },
    }
    payload["agent_center"] = center
    return center
