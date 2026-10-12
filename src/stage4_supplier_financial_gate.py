"""Stage 4 supplier financial-eligibility gate.

Stage 3 category/company verification is intentionally not enough for price claims.
A supplier becomes financially evidence-eligible only when exact-spec matching is
explicitly source-backed by HTTPS evidence and linked to the verified candidate.
"""
from __future__ import annotations

from collections import Counter
from typing import Any
from urllib.parse import urlparse


def _https(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    p = urlparse(raw)
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        return None
    return raw


def _text(value: Any) -> str:
    return str(value or "").strip()


def process_payload(payload: dict[str, Any]) -> dict[str, Any]:
    eligible = 0
    rejected = 0
    reasons: Counter[str] = Counter()
    reviewed = 0

    for item in payload.get("opportunities") or []:
        if not isinstance(item, dict):
            continue
        research = item.get("supplier_research") or {}
        candidates = research.get("candidate_suppliers") or []
        if not isinstance(candidates, list):
            candidates = []
        evidence_rows = item.get("supplier_financial_evidence") or []
        if not isinstance(evidence_rows, list):
            evidence_rows = []

        by_name = {
            _text(c.get("name")).casefold(): c
            for c in candidates
            if isinstance(c, dict) and _text(c.get("name"))
        }
        results = []
        for ev in evidence_rows[:30]:
            if not isinstance(ev, dict):
                continue
            reviewed += 1
            name = _text(ev.get("supplier_name"))
            candidate = by_name.get(name.casefold())
            reason = None
            if not candidate or candidate.get("verified") is not True:
                reason = "stage3_verified_supplier_required"
            elif ev.get("exact_spec_match") is not True:
                reason = "explicit_exact_spec_match_required"
            elif not _https(ev.get("exact_spec_source_url")):
                reason = "exact_spec_https_source_required"
            elif not _https(ev.get("identity_evidence_url")):
                reason = "identity_https_source_required"
            elif not _https(ev.get("product_evidence_url")):
                reason = "product_https_source_required"
            elif not _text(ev.get("specification_reference")):
                reason = "specification_reference_required"

            if reason:
                rejected += 1
                reasons[reason] += 1
                results.append({"supplier_name": name or None, "eligible": False, "reason": reason})
                continue

            candidate["financial_evidence_eligible"] = True
            candidate["exact_spec_match_verified"] = True
            candidate["identity_evidence_url"] = _https(ev.get("identity_evidence_url"))
            candidate["product_evidence_url"] = _https(ev.get("product_evidence_url"))
            candidate["exact_spec_source_url"] = _https(ev.get("exact_spec_source_url"))
            candidate["specification_reference"] = _text(ev.get("specification_reference"))
            eligible += 1
            results.append({"supplier_name": name, "eligible": True, "reason": "accepted"})

        if results:
            item["stage4_supplier_financial_gate"] = {
                "results": results,
                "eligible_count": sum(1 for x in results if x["eligible"]),
                "fail_closed": True,
                "external_contact_authorized": False,
            }

    payload["stage4_supplier_financial_summary"] = {
        "evidence_rows_reviewed": reviewed,
        "eligible_suppliers": eligible,
        "rejected": rejected,
        "rejection_reasons": dict(sorted(reasons.items())),
        "rule": "Stage 3 verification alone cannot authorize price/margin claims; exact-spec HTTPS evidence is mandatory.",
        "fail_closed": True,
        "external_contact_authorized": False,
    }
    return payload
