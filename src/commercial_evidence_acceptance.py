from __future__ import annotations

from collections import Counter
from typing import Any
from urllib.parse import urlparse


_ALLOWED_KINDS = {"unit_price", "selling_unit_price", "freight", "quantity", "currency", "incoterm", "destination"}
_SOURCE_TERM_TYPES = {"official_notice", "source_document", "tender_document", "buyer_document"}


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def _https(value: Any) -> str | None:
    raw = _text(value)
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    return raw


def _verified_supplier_names(item: dict[str, Any]) -> set[str]:
    research = item.get("supplier_research") if isinstance(item.get("supplier_research"), dict) else {}
    candidates = research.get("candidate_suppliers") if isinstance(research.get("candidate_suppliers"), list) else []
    return {
        _text(c.get("name")).casefold()
        for c in candidates
        if isinstance(c, dict) and c.get("verified") is True and _text(c.get("name"))
    }


def _accept(item: dict[str, Any], evidence: dict[str, Any]) -> tuple[bool, str]:
    kind = _text(evidence.get("kind")).casefold()
    value = _text(evidence.get("value"))
    source_url = _https(evidence.get("source_url"))
    if kind not in _ALLOWED_KINDS:
        return False, "unsupported_kind"
    if not value:
        return False, "missing_value"
    if not source_url:
        return False, "https_source_required"

    if kind == "unit_price":
        supplier = _text(evidence.get("supplier_name"))
        currency = _text(evidence.get("currency"))
        if not supplier or supplier.casefold() not in _verified_supplier_names(item):
            return False, "verified_supplier_required"
        if not currency:
            return False, "currency_required"
        item.setdefault("verified_unit_price", value)
        item.setdefault("quote_currency", currency)
        item.setdefault("verified_unit_price_source", source_url)
        item.setdefault("verified_unit_price_supplier", supplier)
        validity = _text(evidence.get("valid_until"))
        if validity:
            from datetime import date
            try:
                date.fromisoformat(validity)
            except ValueError:
                return False, "invalid_quote_validity_date"
            item.setdefault("quote_valid_until", validity)
        return True, "accepted"

    if kind == "selling_unit_price":
        currency = _text(evidence.get("currency")).upper()
        buyer_name = _text(evidence.get("buyer_name"))
        if not currency or not buyer_name:
            return False, "buyer_and_currency_required"
        item.setdefault("verified_selling_unit_price", value)
        item.setdefault("selling_currency", currency)
        item.setdefault("verified_selling_price_source", source_url)
        item.setdefault("selling_quote_buyer", buyer_name)
        return True, "accepted"

    if kind == "freight":
        currency = _text(evidence.get("currency"))
        origin = _text(evidence.get("origin"))
        destination = _text(evidence.get("destination"))
        if not currency or not origin or not destination:
            return False, "freight_scope_incomplete"
        item.setdefault("verified_freight", value)
        item.setdefault("freight_currency", currency)
        item.setdefault("freight_origin", origin)
        item.setdefault("delivery_location", destination)
        item.setdefault("verified_freight_source", source_url)
        mode = _text(evidence.get("transport_mode"))
        if mode:
            item.setdefault("transport_mode", mode)
        return True, "accepted"

    source_type = _text(evidence.get("source_type")).casefold()
    if source_type not in _SOURCE_TERM_TYPES:
        return False, "official_source_type_required"

    field_map = {
        "quantity": "quantity",
        "currency": "currency",
        "incoterm": "incoterm",
        "destination": "delivery_location",
    }
    target = field_map[kind]
    item.setdefault(target, value)
    provenance = item.setdefault("accepted_commercial_evidence", {})
    if isinstance(provenance, dict):
        provenance.setdefault(kind, {
            "value": value,
            "source_url": source_url,
            "source_type": source_type,
            "accepted": True,
        })
    return True, "accepted"


def process_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in (payload.get("opportunities") or []) if isinstance(row, dict)]
    accepted = 0
    rejected = 0
    reasons: Counter[str] = Counter()
    kinds: Counter[str] = Counter()

    for item in rows:
        submissions = item.get("commercial_evidence_submissions")
        if not isinstance(submissions, list):
            continue
        results: list[dict[str, Any]] = []
        for raw in submissions[:50]:
            if not isinstance(raw, dict):
                continue
            ok, reason = _accept(item, raw)
            kind = _text(raw.get("kind")).casefold() or "unknown"
            results.append({"kind": kind, "accepted": ok, "reason": reason})
            if ok:
                accepted += 1
                kinds[kind] += 1
            else:
                rejected += 1
                reasons[reason] += 1
        item["commercial_evidence_acceptance"] = {
            "results": results,
            "accepted_count": sum(1 for r in results if r["accepted"]),
            "rejected_count": sum(1 for r in results if not r["accepted"]),
            "fail_closed": True,
        }

    summary = {
        "opportunities": len(rows),
        "accepted": accepted,
        "rejected": rejected,
        "accepted_by_kind": dict(sorted(kinds.items())),
        "rejection_reasons": dict(sorted(reasons.items())),
        "source_backed_only": True,
        "fail_closed": True,
        "rule": "Commercial evidence is promoted only from HTTPS source-backed records; supplier pricing additionally requires a verified supplier and explicit currency.",
    }
    payload["commercial_evidence_acceptance_summary"] = summary
    return payload
