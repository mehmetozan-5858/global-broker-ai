from __future__ import annotations

from typing import Any


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return " ".join(filter(None, (_text(v) for v in value)))
    if isinstance(value, dict):
        return " ".join(filter(None, (_text(v) for v in value.values())))
    return str(value).strip()


def _first(item: dict[str, Any], *keys: str) -> tuple[str, str | None]:
    for key in keys:
        value = _text(item.get(key))
        if value:
            return value, key
    return "", None


def _verified_supplier_quote(item: dict[str, Any]) -> tuple[str, str | None, bool]:
    supplier = item.get("supplier_research") if isinstance(item.get("supplier_research"), dict) else {}
    verified_count = int(supplier.get("verified_supplier_count") or 0)
    value, field = _first(item, "verified_unit_price", "verified_supplier_unit_price")
    return value, field, verified_count > 0 and bool(value)


def assess(item: dict[str, Any]) -> dict[str, Any]:
    """Build a fail-closed commercial-feasibility record.

    No price, freight, duty, quantity, incoterm or margin is invented. A deal
    becomes calculation-ready only when minimum commercial facts exist and the
    unit price is explicitly tied to at least one verified supplier.
    """
    quantity, quantity_field = _first(item, "quantity-lot", "quantity", "requested_quantity", "qty")
    currency, currency_field = _first(item, "currency", "contract_currency", "quote_currency")
    unit_price, unit_price_field, supplier_quote_verified = _verified_supplier_quote(item)
    freight, freight_field = _first(item, "verified_freight", "freight_cost", "logistics_quote")
    duty, duty_field = _first(item, "verified_duty", "duty_cost", "customs_cost")
    incoterm, incoterm_field = _first(item, "incoterm", "delivery_terms")
    destination, destination_field = _first(item, "delivery_location", "buyer_city", "city")

    facts = {
        "quantity": {"value": quantity or None, "source_field": quantity_field, "verified": bool(quantity)},
        "currency": {"value": currency or None, "source_field": currency_field, "verified": bool(currency)},
        "unit_price": {
            "value": unit_price or None,
            "source_field": unit_price_field,
            "verified": supplier_quote_verified,
            "requires_verified_supplier": True,
        },
        "freight": {"value": freight or None, "source_field": freight_field, "verified": bool(freight)},
        "duty": {"value": duty or None, "source_field": duty_field, "verified": bool(duty)},
        "incoterm": {"value": incoterm or None, "source_field": incoterm_field, "verified": bool(incoterm)},
        "destination": {"value": destination or None, "source_field": destination_field, "verified": bool(destination)},
    }

    missing = [name for name, fact in facts.items() if not fact["value"]]
    blockers: list[str] = []
    for required in ("quantity", "currency", "unit_price", "freight", "destination"):
        if required in missing:
            blockers.append(required)
    if unit_price and not supplier_quote_verified:
        blockers.append("verified_supplier_quote")

    calculation_ready = not blockers
    landed_cost_ready = calculation_ready and bool(duty) and bool(incoterm)

    result = {
        "status": "landed_cost_ready" if landed_cost_ready else ("calculation_ready" if calculation_ready else "commercial_inputs_missing"),
        "source_backed_only": True,
        "calculation_ready": calculation_ready,
        "landed_cost_ready": landed_cost_ready,
        "facts": facts,
        "missing_inputs": missing,
        "blockers": blockers,
        "assumptions": [],
        "margin_claim_allowed": False,
        "human_review_required": True,
        "rule": "Unknown commercial inputs stay unknown; supplier pricing must be tied to a verified supplier; no price, freight, duty or margin is fabricated.",
    }
    item["commercial_feasibility"] = result
    return result


def process_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("opportunities") or []
    ready = 0
    landed = 0
    verified_quote_ready = 0
    for item in rows:
        if not isinstance(item, dict):
            continue
        result = assess(item)
        if result["calculation_ready"]:
            ready += 1
        if result["landed_cost_ready"]:
            landed += 1
        if (result.get("facts") or {}).get("unit_price", {}).get("verified"):
            verified_quote_ready += 1
    payload["commercial_feasibility_summary"] = {
        "opportunities": len(rows),
        "calculation_ready": ready,
        "landed_cost_ready": landed,
        "verified_supplier_quote_ready": verified_quote_ready,
        "blocked_missing_inputs": max(0, len(rows) - ready),
        "source_backed_only": True,
        "margin_claim_allowed": False,
    }
    return payload
