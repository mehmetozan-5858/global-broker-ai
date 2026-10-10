from __future__ import annotations

from typing import Any

# Operational launch blockers are not a measure of code completion.
CATEGORIES = {
    "source_evidence": (
        "live_physical_goods_present",
        "all_live_rows_are_goods_candidates",
        "source_evidence_present",
        "specification_pipeline_present",
        "commercial_feasibility_pipeline_present",
        "gulf_current_scan_verified",
        "gulf_live_ingestion_verified",
    ),
    "security_storage": (
        "server_side_auth_configured",
        "durable_private_storage_configured",
        "admin_dual_recovery_ready",
    ),
    "legal_payment_contact": (
        "legal_text_reviewed",
        "payment_provider_tested",
        "verified_business_contact",
        "custom_domain_verified",
    ),
    "customer_acceptance": ("real_customer_acceptance_tested",),
}


def build(payload: dict[str, Any]) -> dict[str, Any]:
    gate = payload.get("launch_gate") or {}
    checks = gate.get("checks") or {}
    if not isinstance(checks, dict):
        checks = {}
    categories = {}
    for name, required in CATEGORIES.items():
        pending = [key for key in required if checks.get(key) is not True]
        categories[name] = {
            "passed": len(required) - len(pending),
            "required": len(required),
            "pending": pending,
            "ready": not pending,
        }

    gulf = payload.get("gulf_sources") or {}
    country_checks = (
        ("Saudi Arabia", "saudi_live_ingestion_verified"),
        ("United Arab Emirates", "uae_live_ingestion_verified"),
        ("Qatar", "qatar_live_ingestion_verified"),
    )
    regional_sources = {
        country: {"live_this_scan": gulf.get(key) is True}
        for country, key in country_checks
    }
    report = {
        "intended_market_scope": "worldwide",
        "worldwide_live_coverage_verified": False,
        "market_scope_note": (
            "Global physical-goods B2B brokerage is the intended scope, not verified "
            "worldwide live coverage. Gulf priority checks are a launch "
            "quality requirement, not a country restriction on worldwide discovery."
        ),
        "production_launch_ready": gate.get("launch_ready") is True,
        "mode": "production" if gate.get("launch_ready") is True else "shadow",
        "blockers": list(gate.get("blockers") or []),
        "categories": categories,
        "priority_gulf_sources": regional_sources,
        "readiness_percent": None,
        "readiness_percent_note": (
            "No percentage inferred from check counts: external security, legal, "
            "payment and human acceptance are not interchangeable with code tests."
        ),
    }
    payload["launch_readiness_report"] = report
    return report
