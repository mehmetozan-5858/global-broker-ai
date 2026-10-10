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


def _identifier(item: dict[str, Any], index: int) -> str:
    for key in ("id", "opportunity_id", "tender_id", "reference_number", "rfq_number"):
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return f"row-{index + 1}"


def _blockers(item: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not (item.get("official_links") or item.get("source_url")):
        blockers.append("official_source")
    if (item.get("export_goods_review") or {}).get("status") != "goods_candidate":
        blockers.append("physical_goods")
    if not (item.get("core_field_coverage") or {}).get("complete"):
        blockers.append("field_evidence")
    if not (item.get("specification_analysis") or {}).get("supplier_sourcing_ready"):
        blockers.append("specification")
    if int((item.get("supplier_research") or {}).get("verified_supplier_count") or 0) < 1:
        blockers.append("verified_supplier")
    if not (item.get("commercial_feasibility") or {}).get("calculation_ready"):
        blockers.append("commercial_feasibility")
    if not (item.get("offer_risk_gate") or {}).get("draft_offer_ready"):
        blockers.append("offer_risk_gate")
    return blockers


def build(payload: dict[str, Any]) -> dict[str, Any]:
    rows = [x for x in (payload.get("opportunities") or []) if isinstance(x, dict)]
    stage_counts: dict[str, Counter] = {name: Counter() for name in AGENTS}
    work_queue: list[dict[str, Any]] = []
    blocker_counts: Counter = Counter()

    for index, item in enumerate(rows):
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

        blockers = _blockers(item)
        blocker_counts.update(blockers)
        work_queue.append({
            "opportunity_id": _identifier(item, index),
            "title": item.get("title_tr") or item.get("title_original") or item.get("title") or "Untitled opportunity",
            "blockers": blockers,
            "next_agent": blockers[0] if blockers else "human_review",
            "draft_offer_ready": bool((item.get("offer_risk_gate") or {}).get("draft_offer_ready")),
            "external_action_authorized": False,
        })

    center = {
        "mode": "shadow",
        "external_actions_enabled": False,
        "opportunity_count": len(rows),
        "agents": {name: dict(counter) for name, counter in stage_counts.items()},
        "blocker_counts": dict(blocker_counts),
        "work_queue": work_queue,
        "summary": {
            "ready_for_human_review": sum(1 for row in work_queue if not row["blockers"]),
            "blocked": sum(1 for row in work_queue if row["blockers"]),
        },
        "policy": {
            "email_send": False,
            "bid_submit": False,
            "payment": False,
            "order": False,
            "contract_sign": False,
            "human_approval_required": True,
        },
    }
    payload["agent_center"] = center
    return center
