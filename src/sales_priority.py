from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _is_true(value: Any) -> bool:
    return value is True


def _status(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    return str(value or "").strip().lower()


def _verification_backed(item: dict[str, Any]) -> bool:
    if item.get("buyer_verified") is True:
        return True
    verification = item.get("buyer_verification")
    if not isinstance(verification, dict):
        return False
    return (
        str(verification.get("status") or "").lower() == "verified"
        and bool(verification.get("evidence"))
    )


def _specification_ready(item: dict[str, Any]) -> bool:
    spec = item.get("specification")
    if not isinstance(spec, dict):
        spec = item.get("specification_analysis")
    if isinstance(spec, dict):
        status = str(spec.get("status") or spec.get("readiness") or "").lower()
        if status in {"ready", "supplier_ready", "complete", "parsed"}:
            return True
        if spec.get("supplier_ready") is True:
            return True
    return item.get("supplier_ready") is True


def sales_priority(item: dict[str, Any]) -> dict[str, Any]:
    """Rank opportunities for closing effort without inventing commercial facts.

    Unknown data never receives positive credit. Estimated value is rewarded only
    for being source-backed/present; currencies are not compared across notices.
    """
    score = 0
    reasons: list[str] = []
    blockers: list[str] = []

    if _verification_backed(item):
        score += 25
        reasons.append("verified_buyer")
    else:
        blockers.append("buyer_verification")

    if _specification_ready(item):
        score += 20
        reasons.append("supplier_ready_specification")
    else:
        blockers.append("specification_readiness")

    supplier_status = _status(item, "supplier_status")
    if supplier_status == "verified":
        score += 15
        reasons.append("verified_supplier")
    else:
        blockers.append("supplier_verification")

    compliance_status = _status(item, "compliance_status")
    if compliance_status == "clear":
        score += 10
        reasons.append("compliance_clear")
    elif compliance_status:
        blockers.append("compliance_clearance")

    margin_status = _status(item, "margin_status")
    if margin_status == "positive":
        score += 10
        reasons.append("positive_margin")
    else:
        blockers.append("margin_confirmation")

    if item.get("estimated_value") not in (None, "", 0):
        score += 8
        reasons.append("source_value_present")

    if str(item.get("deadline") or "").strip():
        score += 5
        reasons.append("deadline_present")

    doc = item.get("document_extraction")
    if isinstance(doc, dict) and (
        doc.get("status") == "parsed" or int(doc.get("parsed_count") or 0) > 0
    ):
        score += 5
        reasons.append("source_document_parsed")

    if str(item.get("source_url") or "").startswith("http"):
        score += 2
        reasons.append("source_link_present")

    score = min(100, score)
    if score >= 75:
        grade = "A"
        queue = "close_first"
    elif score >= 50:
        grade = "B"
        queue = "develop_next"
    else:
        grade = "C"
        queue = "research_only"

    return {
        "score": score,
        "grade": grade,
        "queue": queue,
        "reasons": reasons,
        "blockers": blockers,
        "source_backed_only": True,
    }


def enrich_payload(payload: dict[str, Any]) -> dict[str, Any]:
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        return payload

    counts = {"A": 0, "B": 0, "C": 0}
    for item in opportunities:
        if not isinstance(item, dict):
            continue
        priority = sales_priority(item)
        item["sales_priority"] = priority
        counts[priority["grade"]] += 1

    payload["sales_priority_summary"] = {
        "version": 1,
        "strategy": "close_probability_first",
        "grades": counts,
        "close_first": counts["A"],
        "develop_next": counts["B"],
        "research_only": counts["C"],
    }
    return payload


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.sales_priority <json-file>")
    path = Path(sys.argv[1])
    payload = json.loads(path.read_text(encoding="utf-8"))
    enrich_payload(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = payload.get("sales_priority_summary") or {}
    print(
        "SALES_PRIORITY_SUMMARY "
        f"A={summary.get('close_first', 0)} "
        f"B={summary.get('develop_next', 0)} "
        f"C={summary.get('research_only', 0)}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
