"""Fail-closed, read-only acceptance gate for TED 702997-2026 tank evidence.

A green test of this gate means blocking rules are working; it does not mean
technical or commercial tender acceptance. No live network or supplier actions.
"""
import json
from pathlib import Path
from scripts.audit_ted_tank_capacity_envelopes import SOURCE, audit

REQUIRED_EVIDENCE = (
    "authoritative_2026_10_27_revision_confirmed",
    "official_drawing_revision_confirmed",
    "supplier_usable_volume_certificates_for_27_tanks",
    "dimension_conflicts_resolved_by_authority",
    "pump_filter_piping_site_requirements_verified",
    "site_installation_and_clearance_verified",
    "independent_engineering_approval",
)


def decision(matrix, evidence=None):
    result = audit(matrix)
    evidence = evidence if evidence is not None else {}
    if not isinstance(evidence, dict):
        raise ValueError("Evidence flags must be a mapping")
    # No user-provided override can hide geometric contradictions.
    flags = {key: evidence.get(key) is True for key in REQUIRED_EVIDENCE}
    conflicts = [row for row in result["rows"] if row["drawing_envelope_below_required_volume"]]
    spec_conflicts = [row for row in result["rows"] if row["spec_dimensional_envelope_below_required_volume"]]
    if matrix.get("technical_approval") is not False or matrix.get("commercial_approval") is not False:
        raise ValueError("Matrix cannot claim prior approval")
    blockers = []
    if conflicts:
        blockers.append("drawing_capacity_envelope_conflict")
    if spec_conflicts:
        blockers.append("specification_capacity_envelope_conflict")
    for key, confirmed in flags.items():
        if not confirmed:
            blockers.append("missing_" + key)
    # Deliberately no success/approval state: reviewed evidence only; requires
    # independent decision outside the automated audit.
    return {
        "notice": matrix["notice"],
        "status": "BLOCKED",
        "risk_level": "critical" if spec_conflicts else "high",
        "sites_with_drawing_conflict": sorted(r["site"] for r in conflicts),
        "sites_with_specification_conflict": sorted(r["site"] for r in spec_conflicts),
        "affected_new_tanks_in_drawing_conflict": sum(r["new_tank_count"] for r in conflicts),
        "evidence_flags_confirmed": sum(flags.values()),
        "evidence_flags_required": len(flags),
        "blockers": blockers,
        "technical_approval": False,
        "commercial_approval": False,
        "deployment_approval": False,
    }


if __name__ == "__main__":
    matrix = json.loads(SOURCE.read_text(encoding="utf-8"))
    status = decision(matrix)
    print(json.dumps(status, ensure_ascii=False, sort_keys=True))
    raise SystemExit(2)
