from __future__ import annotations

from typing import Any


def evaluate(item: dict[str, Any]) -> dict[str, Any]:
    goods_ok = (item.get("export_goods_review") or {}).get("status") == "goods_candidate"
    buyer = item.get("buyer_verification") or item.get("verification") or {}
    buyer_ok = buyer.get("verified") is True or buyer.get("status") in {"verified", "source_verified"}
    spec_ok = bool((item.get("specification_analysis") or {}).get("supplier_sourcing_ready"))
    feas_ok = bool((item.get("commercial_feasibility") or {}).get("calculation_ready"))
    supplier = item.get("supplier_research") or {}
    supplier_ok = int(supplier.get("verified_supplier_count") or 0) > 0
    blockers = []
    if not goods_ok: blockers.append("physical_goods")
    if not buyer_ok: blockers.append("buyer_verification")
    if not spec_ok: blockers.append("specification")
    if not supplier_ok: blockers.append("verified_supplier")
    if not feas_ok: blockers.append("commercial_feasibility")
    result = {
        "draft_offer_ready": not blockers,
        "external_action_authorized": False,
        "human_approval_required": True,
        "blockers": blockers,
        "allowed_actions": ["internal_review", "draft_only"],
        "forbidden_actions": ["send_email", "submit_bid", "place_order", "take_payment"],
        "rule": "Even a complete dossier stays in Shadow Mode until explicit human authorization and production legal/payment gates exist.",
    }
    item["offer_risk_gate"] = result
    return result


def process_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("opportunities") or []
    ready = 0
    for item in rows:
        if isinstance(item, dict) and evaluate(item)["draft_offer_ready"]:
            ready += 1
    payload["offer_risk_summary"] = {
        "opportunities": len(rows),
        "internal_draft_ready": ready,
        "external_action_authorized": 0,
        "mode": "shadow",
    }
    return payload
