from __future__ import annotations

from typing import Any


def build(payload: dict[str, Any]) -> dict[str, Any]:
    """Build an internal-only offer review queue from A8 evidence gates.

    No item can enter this queue unless the existing offer risk gate marks it
    draft-ready. The queue never authorizes sending, bidding, ordering,
    contracting or payment activity.
    """
    rows = [r for r in (payload.get("opportunities") or []) if isinstance(r, dict)]
    queue: list[dict[str, Any]] = []

    for row in rows:
        gate = row.get("offer_risk_gate") if isinstance(row.get("offer_risk_gate"), dict) else {}
        if gate.get("draft_offer_ready") is not True:
            continue

        risk_flags = [str(x) for x in (gate.get("risk_flags") or []) if x]
        oid = row.get("id") or row.get("opportunity_id") or row.get("publication-number") or row.get("notice_id")
        queue.append({
            "opportunity_id": oid,
            "status": "human_review_required",
            "priority": 90 if risk_flags else 100,
            "risk_flags": risk_flags,
            "allowed_actions": ["review_evidence", "prepare_internal_draft"],
            "forbidden_actions": ["send_email", "submit_bid", "place_order", "take_payment", "sign_contract"],
            "human_final_approval_required": True,
            "external_action_authorized": False,
        })

    queue.sort(key=lambda x: (-int(x["priority"]), str(x.get("opportunity_id") or "")))
    result = {
        "candidate_count": len(queue),
        "risk_review_required": sum(1 for x in queue if x["risk_flags"]),
        "clean_internal_drafts": sum(1 for x in queue if not x["risk_flags"]),
        "queue": queue[:100],
        "queue_truncated": len(queue) > 100,
        "external_action_authorized": False,
        "human_final_approval_required": True,
        "rule": "Only A8 draft-ready opportunities enter the internal offer queue; external action remains disabled until explicit human approval and launch gates permit it.",
    }
    payload["offer_candidate_queue"] = result
    return result
