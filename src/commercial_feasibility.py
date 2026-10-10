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


def assess(item: dict[str, Any]) -> dict[str, Any]:
    """Build a conservative commercial-feasibility record.

    No price, freight, duty, quantity or margin is invented. A deal can be
    marked calculation-ready only when the underlying commercial facts are
    present as explicit source/operator-entered facts.
    """
    quantity, quantity_field = _first(item, "quantity-lot", "quantity", "requested_quantity", "qty")
    currency, currency_field = _first(item, "currency", "contract_currency", "quote_currency")
    unit_price, unit_price_field = _first(item, "verified_unit_price", "supplier_unit_price", "quote_unit_price")
    freight, freight_field = _first(item, "verified_freight", "freight_cost", "logistics_quote")
    duty, duty_field = _first(item, "verified_duty", "duty_cost", "customs_cost")
    incoterm, incoterm_field = _first(item, "incoterm", "delivery_terms")
    destination, destination_field = _first(item, "delivery_location", "project_location", "buyer_city", "city")

    facts = {
        "quantity": {"value": quantity or None, "source_field": quantity_field},
        "currency": {"value": currency or None, "source_field": currency_field},
        "unit_price": {"value": unit_price or None, "source_field": unit_price_field},
        "freight": {"value": freight or None, "source_field": freight_field},
        "duty": {"value": duty or None, "source_field": duty_field},
        "incoterm": {"value": incoterm or None, "source_field": incoterm_field},
        "destination": {"value": destination or None, "source_field": destination_field},
    }
    missing = [name for name, fact in facts.items() if not fact["value"]]
    calculation_ready = not any(name in missing for name in ("quantity", "currency", "unit_price", "freight", "destination"))
    result = {
        "status": "calculation_ready" if calculation_ready else "commercial_inputs_missing",
        "source_backed_only": True,
        "calculation_ready": calculation_ready,
        "facts": facts,
        "missing_inputs": missing,
        "assumptions": [],
        "margin_claim_allowed": False,
        "rule": "Unknown commercial inputs stay unknown; no price, freight, duty or margin is fabricated.",
    }
    item["commercial_feasibility"] = result
    return result


def process_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("opportunities") or []
    ready = 0
    for item in rows:
        if isinstance(item, dict):
            if assess(item)["calculation_ready"]:
                ready += 1
    payload["commercial_feasibility_summary"] = {
        "opportunities": len(rows),
        "calculation_ready": ready,
        "blocked_missing_inputs": max(0, len(rows) - ready),
        "source_backed_only": True,
    }
    return payload
