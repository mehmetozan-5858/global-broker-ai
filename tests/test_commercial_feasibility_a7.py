from src.commercial_feasibility import assess, process_payload


def base_item():
    return {
        "quantity": "100",
        "currency": "USD",
        "verified_unit_price": "12.50",
        "verified_freight": "500",
        "delivery_location": "Riyadh",
        "supplier_research": {"verified_supplier_count": 1},
    }


def test_ready_requires_verified_supplier_quote():
    item = base_item()
    result = assess(item)
    assert result["calculation_ready"] is True
    assert result["facts"]["unit_price"]["verified"] is True
    assert result["landed_cost_ready"] is False


def test_unverified_supplier_blocks_quote_even_when_price_present():
    item = base_item()
    item["supplier_research"] = {"verified_supplier_count": 0}
    result = assess(item)
    assert result["calculation_ready"] is False
    assert "verified_supplier_quote" in result["blockers"]


def test_generic_supplier_price_is_not_promoted_to_verified_quote():
    item = base_item()
    item.pop("verified_unit_price")
    item["supplier_unit_price"] = "9.90"
    result = assess(item)
    assert result["calculation_ready"] is False
    assert result["facts"]["unit_price"]["value"] is None


def test_landed_cost_requires_duty_and_incoterm():
    item = base_item()
    item["verified_duty"] = "5%"
    item["incoterm"] = "CIF"
    result = assess(item)
    assert result["calculation_ready"] is True
    assert result["landed_cost_ready"] is True
    assert result["margin_claim_allowed"] is False


def test_summary_counts_truthfully():
    ready = base_item()
    landed = base_item()
    landed["verified_duty"] = "100"
    landed["incoterm"] = "DAP"
    blocked = base_item()
    blocked["supplier_research"] = {"verified_supplier_count": 0}
    payload = {"opportunities": [ready, landed, blocked]}
    process_payload(payload)
    summary = payload["commercial_feasibility_summary"]
    assert summary["calculation_ready"] == 2
    assert summary["landed_cost_ready"] == 1
    assert summary["verified_supplier_quote_ready"] == 2
    assert summary["margin_claim_allowed"] is False
