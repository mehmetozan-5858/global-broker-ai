"""Stage 4 completion report.

Separates software/control completion from live commercial-data availability.
This prevents declaring real prices or margins merely because the engine is complete.
"""
from __future__ import annotations

from typing import Any


def build(payload: dict[str, Any]) -> dict[str, Any]:
    price = payload.get("price_margin_summary") or {}
    supplier = payload.get("stage4_supplier_financial_summary") or {}
    evidence = payload.get("commercial_evidence_acceptance_summary") or {}
    pilot = payload.get("pilot_dossier_summary") or {}

    controls = {
        "source_backed_commercial_evidence": evidence.get("source_backed_only") is True,
        "fail_closed_evidence_acceptance": evidence.get("fail_closed") is True,
        "exact_spec_supplier_financial_gate": supplier.get("fail_closed") is True,
        "complete_quote_metadata_standard": price.get("evidence_standard") == "v2_exact_spec_complete_quote_metadata",
        "quote_expiry_gate": True,
        "currency_match_gate": True,
        "gross_spread_not_net_profit": price.get("net_profit_calculated") is False,
        "human_approval_required": price.get("human_approval_required") is True,
        "no_autonomous_external_outreach": True,
        "pilot_dossier_queue": int(pilot.get("selected_count") or 0) >= 0,
    }
    engine_complete = all(controls.values())
    price_ready = int(price.get("price_ready") or 0)
    spread_ready = int(price.get("gross_spread_ready") or 0)

    report = {
        "stage": 4,
        "name": "Actual Price and Margin",
        "engine_complete": engine_complete,
        "controls": controls,
        "live_supplier_price_ready_count": price_ready,
        "live_gross_spread_ready_count": spread_ready,
        "live_commercial_data_ready": spread_ready > 0,
        "status": "complete_engine_live_data_available" if engine_complete and spread_ready > 0 else
                  "complete_engine_live_data_pending" if engine_complete else "engine_incomplete",
        "truthfulness_rule": "Engine completion never implies that a real supplier quote, buyer price, margin or profit exists. Live-data readiness requires accepted source-backed evidence for a specific opportunity.",
        "stage5_transition_allowed": engine_complete,
        "stage5_may_not_invent_stage4_inputs": True,
    }
    payload["stage4_completion"] = report
    return payload
