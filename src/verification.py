"""Fail-closed verification helpers for Global Broker opportunities.

A buyer name appearing in an official/public notice identifies the source-side
buyer, but it is not sufficient corporate/commercial due diligence.  This
module prevents source identification from being represented as a verified
buyer in data published to the mobile site.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def buyer_is_verified(item: dict[str, Any]) -> bool:
    """Return True only when explicit verification evidence is present.

    Existing feeds currently provide buyer identity/source information, not a
    completed due-diligence record.  Future verification agents may set
    ``buyer_verification`` with ``status=verified`` and at least one evidence
    item after checking the legal entity against authoritative sources.
    """
    record = item.get("buyer_verification")
    if not isinstance(record, dict):
        return False
    evidence = record.get("evidence")
    return record.get("status") == "verified" and isinstance(evidence, list) and bool(evidence)


def sanitize_opportunity(item: dict[str, Any]) -> dict[str, Any]:
    verified = buyer_is_verified(item)
    item["buyer_verified"] = verified

    buyer_name = str(item.get("buyer-name") or "").strip()
    if verified:
        item["compliance_status"] = "buyer_verified_due_diligence_complete"
    elif buyer_name:
        item["compliance_status"] = "buyer_identified_due_diligence_pending"
    else:
        item["compliance_status"] = "buyer_identity_pending"

    risk = item.get("risk_agent")
    if isinstance(risk, dict):
        # Source identification and buyer verification are intentionally
        # separate signals.
        risk["buyer_source_identified"] = bool(buyer_name)
        risk["buyer_verified"] = verified
        risk.pop("buyer_source_verified", None)

    workflow = item.get("workflow")
    if isinstance(workflow, dict) and isinstance(workflow.get("buyer"), dict):
        workflow["buyer"]["verified"] = verified
        if verified:
            workflow["buyer"]["status"] = "verified"
        elif buyer_name:
            workflow["buyer"]["status"] = "source_identified_due_diligence_pending"
        else:
            workflow["buyer"]["status"] = "identity_pending"
    return item


def sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    opportunities = payload.get("opportunities")
    if isinstance(opportunities, list):
        for item in opportunities:
            if isinstance(item, dict):
                sanitize_opportunity(item)
    return payload


def sanitize_file(path: str) -> None:
    target = Path(path)
    payload = json.loads(target.read_text(encoding="utf-8"))
    sanitize_payload(payload)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m src.verification <json-file>", file=sys.stderr)
        return 2
    sanitize_file(argv[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
