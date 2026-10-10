from __future__ import annotations

from typing import Any


def _bool_status(container: dict[str, Any], truthy_statuses: set[str]) -> bool:
    return container.get("verified") is True or container.get("status") in truthy_statuses


def evaluate(item: dict[str, Any]) -> dict[str, Any]:
    goods_ok = (item.get("export_goods_review") or {}).get("status") == "goods_candidate"

    buyer = item.get("buyer_verification") or item.get("verification") or {}
    buyer_ok = _bool_status(buyer, {"verified", "source_verified"})

    spec = item.get("specification_analysis") or {}
    spec_ok = bool(spec.get("supplier_sourcing_ready"))

    supplier = item.get("supplier_research") or {}
    verified_supplier_count = int(supplier.get("verified_supplier_count") or 0)
    supplier_ok = verified_supplier_count > 0

    feasibility = item.get("commercial_feasibility") or {}
    feasibility_ok = bool(feasibility.get("calculation_ready"))
    landed_cost_ready = bool(feasibility.get("landed_cost_ready"))

    commercial_terms = item.get("commercial_terms") or {}
    term_facts = commercial_terms.get("terms") if isinstance(commercial_terms.get("terms"), dict) else {}
    delivery_known = bool(((term_facts.get("delivery") or {}).get("value"))) or bool(
        ((feasibility.get("facts") or {}).get("destination") or {}).get("value")
    )

    blockers: list[str] = []
    if not goods_ok:
        blockers.append("physical_goods")
    if not buyer_ok:
        blockers.append("buyer_verification")
    if not spec_ok:
        blockers.append("specification")
    if not supplier_ok:
        blockers.append("verified_supplier")
    if not feasibility_ok:
        blockers.append("commercial_feasibility")
    if not delivery_known:
        blockers.append("delivery_evidence")

    risk_flags: list[str] = []
    if supplier_ok and verified_supplier_count < 2:
        risk_flags.append("single_verified_supplier")
    if feasibility_ok and not landed_cost_ready:
        risk_flags.append("landed_cost_incomplete")
    missing_terms = commercial_terms.get("missing") if isinstance(commercial_terms.get("missing"), list) else []
    for name in ("payment", "bond", "eligibility", "award"):
        if name in missing_terms:
            risk_flags.append(f"missing_{name}_term")

    draft_ready = not blockers
    result = {
        "draft_offer_ready": draft_ready,
        "risk_review_required": bool(risk_flags),
        "risk_flags": risk_flags,
        "external_action_authorized": False,
        "human_approval_required": True,
        "blockers": blockers,
        "verified_supplier_count": verified_supplier_count,
        "allowed_actions": ["internal_review", "draft_only"] if draft_ready else ["internal_review"],
        "forbidden_actions": ["send_email", "submit_bid", "place_order", "take_payment", "sign_contract"],
        "approval_chain": ["commercial_review", "risk_review", "human_final_approval"],
        "rule": (
            "A8 can prepare an internal draft only when the goods, buyer, specification, verified supplier, "
            "commercial feasibility and delivery evidence gates all pass. Risk flags remain visible and no "
            "external action is ever authorized automatically."
        ),
    }
    item["offer_risk_gate"] = result
    return result


def process_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("opportunities") or []
    ready = 0
    risk_review = 0
    blocked = 0
    for item in rows:
        if not isinstance(item, dict):
            continue
        result = evaluate(item)
        if result["draft_offer_ready"]:
            ready += 1
        else:
            blocked += 1
        if result["risk_review_required"]:
            risk_review += 1
    payload["offer_risk_summary"] = {
        "opportunities": len(rows),
        "internal_draft_ready": ready,
        "risk_review_required": risk_review,
        "blocked": blocked,
        "external_action_authorized": 0,
        "mode": "shadow",
        "human_approval_required": True,
    }
    return payload
