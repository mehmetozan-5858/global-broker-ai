"""Fail-closed buyer verification for Global Broker opportunities.

Stage 2 separates three different facts that must never be conflated:
1) a buyer name was found,
2) the buyer is confirmed by the official procurement source,
3) the legal entity/institution has independent authoritative corroboration.

Only level 3 may set ``buyer_verified=True``.  The other levels are useful
research progress, but they remain due-diligence pending.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SOURCE_URL_KEYS = (
    "source_url",
    "source-url",
    "notice_url",
    "detail_url",
    "document_url",
    "official_url",
    "tender_url",
    "url",
)
BUYER_KEYS = (
    "buyer-name",
    "buyer_name",
    "contracting_authority",
    "organization_name",
    "agency",
    "department",
    "office",
    "project_name",
)
COUNTRY_KEYS = (
    "buyer-country",
    "buyer_country",
    "project_ctry_name",
    "country_name",
    "country",
    "country_code",
)


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join(_text(x) for x in value if x is not None).strip()
    if isinstance(value, dict):
        return " ".join(_text(x) for x in value.values() if x is not None).strip()
    return str(value).strip()


def _first(item: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = _text(item.get(key))
        if value:
            return value
    return ""


def _https_source(item: dict[str, Any]) -> str:
    for key in SOURCE_URL_KEYS:
        value = _text(item.get(key))
        if value.startswith("https://"):
            return value
    return ""


def _buyer(item: dict[str, Any]) -> str:
    return _first(item, BUYER_KEYS)


def _country(item: dict[str, Any]) -> str:
    return _first(item, COUNTRY_KEYS)


def _source_evidence(item: dict[str, Any]) -> dict[str, Any] | None:
    buyer = _buyer(item)
    url = _https_source(item)
    if not buyer or not url:
        return None
    return {
        "type": "official_procurement_source",
        "source": _text(item.get("source")) or "official_source",
        "url": url,
        "buyer_name": buyer,
        "country": _country(item) or None,
        "supports": ["buyer_identity", "procurement_notice"],
    }


def _valid_registry_evidence(item: dict[str, Any]) -> list[dict[str, Any]]:
    """Accept only explicit, independently supplied authoritative evidence.

    Stage 2 does not invent or infer registry checks.  A future country-specific
    registry agent can append ``buyer_registry_evidence`` entries after making
    the real check.  Until then, official tender identification remains level 1.
    """
    rows = item.get("buyer_registry_evidence")
    if not isinstance(rows, list):
        return []
    accepted: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        url = _text(row.get("url"))
        authority = _text(row.get("authority") or row.get("source_type")).lower()
        name_match = row.get("name_match") is True
        country_match = row.get("country_match") is not False
        authoritative = authority in {
            "government_registry",
            "official_institution_directory",
            "company_registry",
            "tax_registry",
            "public_entity_registry",
        }
        if url.startswith("https://") and authoritative and name_match and country_match:
            accepted.append(dict(row))
    return accepted


def prepare_buyer_verification(item: dict[str, Any]) -> dict[str, Any]:
    buyer = _buyer(item)
    country = _country(item)
    source_ev = _source_evidence(item)
    registry = _valid_registry_evidence(item)
    contact = item.get("contact_enrichment") if isinstance(item.get("contact_enrichment"), dict) else {}

    evidence: list[dict[str, Any]] = []
    if source_ev:
        evidence.append(source_ev)
    evidence.extend(registry)

    if registry:
        status = "verified"
        level = 3
        next_action = "Alıcı doğrulandı; tedarikçi eşleştirme ve ticari incelemeye devam et."
    elif source_ev:
        status = "source_confirmed"
        level = 1
        next_action = "Bağımsız resmî kurum/şirket sicilinden tüzel kişilik veya kurum kaydını doğrula."
    elif buyer:
        status = "identity_found_source_missing"
        level = 0
        next_action = "Alıcı adını resmî ilan veya kurum kaynağıyla doğrula."
    else:
        status = "identity_pending"
        level = 0
        next_action = "Resmî kaynaktan alıcı kurum/şirket adını bul."

    item["buyer_verification"] = {
        "version": 1,
        "status": status,
        "verification_level": level,
        "buyer_name": buyer or None,
        "country": country or None,
        "official_source_confirmed": bool(source_ev),
        "source_backed_contact": contact.get("status") == "source_backed",
        "independent_registry_checks": len(registry),
        "evidence": evidence,
        "next_action": next_action,
        "fail_closed": True,
    }
    return item


def buyer_is_verified(item: dict[str, Any]) -> bool:
    """Return True only when explicit authoritative verification exists."""
    record = item.get("buyer_verification")
    if not isinstance(record, dict):
        return False
    evidence = record.get("evidence")
    return record.get("status") == "verified" and isinstance(evidence, list) and bool(evidence)


def sanitize_opportunity(item: dict[str, Any]) -> dict[str, Any]:
    prepare_buyer_verification(item)
    verified = buyer_is_verified(item)
    item["buyer_verified"] = verified

    buyer_name = _buyer(item)
    if verified:
        item["compliance_status"] = "buyer_verified_due_diligence_complete"
    elif buyer_name:
        item["compliance_status"] = "buyer_identified_due_diligence_pending"
    else:
        item["compliance_status"] = "buyer_identity_pending"

    risk = item.get("risk_agent")
    if isinstance(risk, dict):
        risk["buyer_source_identified"] = bool(buyer_name)
        risk["buyer_verified"] = verified
        risk.pop("buyer_source_verified", None)

    workflow = item.get("workflow")
    if isinstance(workflow, dict) and isinstance(workflow.get("buyer"), dict):
        workflow["buyer"]["verified"] = verified
        record = item.get("buyer_verification") or {}
        if verified:
            workflow["buyer"]["status"] = "verified"
        elif record.get("status") == "source_confirmed":
            workflow["buyer"]["status"] = "source_confirmed_due_diligence_pending"
        elif buyer_name:
            workflow["buyer"]["status"] = "source_identified_due_diligence_pending"
        else:
            workflow["buyer"]["status"] = "identity_pending"
    return item


def sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        payload["buyer_verification_summary"] = {
            "version": 1,
            "opportunities": 0,
            "verified": 0,
            "source_confirmed": 0,
            "identity_pending": 0,
            "queue_count": 0,
            "queue": [],
        }
        return payload

    counts: Counter[str] = Counter()
    queue: list[dict[str, Any]] = []
    reviewed = 0
    for item in opportunities:
        if not isinstance(item, dict):
            continue
        reviewed += 1
        sanitize_opportunity(item)
        record = item.get("buyer_verification") or {}
        status = _text(record.get("status")) or "identity_pending"
        counts[status] += 1
        if status != "verified":
            queue.append({
                "opportunity_id": item.get("opportunity_id") or item.get("id") or item.get("publication-number") or item.get("notice_id"),
                "buyer_name": _buyer(item) or None,
                "country": _country(item) or None,
                "status": status,
                "verification_level": int(record.get("verification_level") or 0),
                "deal_score": int(item.get("deal_score") or 0),
                "official_source_confirmed": bool(record.get("official_source_confirmed")),
                "source_backed_contact": bool(record.get("source_backed_contact")),
                "next_action": record.get("next_action"),
            })

    queue.sort(key=lambda row: (
        -int(row.get("official_source_confirmed") or 0),
        -int(row.get("source_backed_contact") or 0),
        -int(row.get("deal_score") or 0),
        str(row.get("buyer_name") or ""),
    ))
    payload["buyer_verification_summary"] = {
        "version": 1,
        "mode": "fail_closed_authoritative_evidence_only",
        "opportunities": reviewed,
        "verified": counts.get("verified", 0),
        "source_confirmed": counts.get("source_confirmed", 0),
        "identity_found_source_missing": counts.get("identity_found_source_missing", 0),
        "identity_pending": counts.get("identity_pending", 0),
        "queue_count": len(queue),
        "queue": queue[:100],
        "queue_truncated": len(queue) > 100,
        "rule": "Official tender identification is progress, not full buyer verification; independent authoritative corroboration is required for buyer_verified=true.",
    }
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
