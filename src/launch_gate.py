from __future__ import annotations

import os
from typing import Any


def _flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    rows = [x for x in (payload.get("opportunities") or []) if isinstance(x, dict)]
    spec = payload.get("specification_analysis") or {}
    field = payload.get("field_evidence_summary") or {}
    feas = payload.get("commercial_feasibility_summary") or {}

    checks = {
        "live_physical_goods_present": bool(rows),
        "all_live_rows_are_goods_candidates": bool(rows) and all((x.get("export_goods_review") or {}).get("status") == "goods_candidate" for x in rows),
        "source_evidence_present": bool(field),
        "specification_pipeline_present": bool(spec),
        "commercial_feasibility_pipeline_present": bool(feas),
        "server_side_auth_configured": _flag("GB_AUTH_READY"),
        "durable_private_storage_configured": _flag("GB_PRIVATE_STORAGE_READY"),
        "admin_dual_recovery_ready": _flag("GB_ADMIN_DUAL_RECOVERY_READY"),
        "legal_text_reviewed": _flag("GB_LEGAL_REVIEWED"),
        "payment_provider_tested": _flag("GB_PAYMENT_TESTED"),
        "verified_business_contact": _flag("GB_BUSINESS_CONTACT_VERIFIED"),
        "custom_domain_verified": _flag("GB_CUSTOM_DOMAIN_VERIFIED"),
        "gulf_live_ingestion_verified": _flag("GB_GULF_LIVE_VERIFIED"),
        "real_customer_acceptance_tested": _flag("GB_CUSTOMER_ACCEPTANCE_TESTED"),
    }
    technical_checks = (
        "live_physical_goods_present",
        "all_live_rows_are_goods_candidates",
        "source_evidence_present",
        "specification_pipeline_present",
        "commercial_feasibility_pipeline_present",
    )
    external_checks = tuple(k for k in checks if k not in technical_checks)
    blockers = [name for name, ok in checks.items() if not ok]
    result = {
        "launch_ready": not blockers,
        "mode": "production" if not blockers else "shadow",
        "checks": checks,
        "technical_checks_passed": all(checks[k] for k in technical_checks),
        "external_checks_passed": all(checks[k] for k in external_checks),
        "blockers": blockers,
        "rule": "Production launch stays closed until every required technical, admin-recovery, security, legal, payment, domain, Gulf-ingestion and acceptance gate is explicitly verified.",
    }
    payload["launch_gate"] = result
    return result
