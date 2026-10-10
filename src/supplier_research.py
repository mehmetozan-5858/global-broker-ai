from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return " ".join(_text(v) for v in value if _text(v)).strip()
    if isinstance(value, dict):
        return " ".join(_text(v) for v in value.values() if _text(v)).strip()
    return str(value).strip()


def _https_url(value: Any) -> str | None:
    raw = _text(value)
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    return raw


def _candidate_status(candidate: dict[str, Any], product: str) -> dict[str, Any]:
    name = _text(candidate.get("name") or candidate.get("supplier_name"))
    source_url = _https_url(candidate.get("source_url") or candidate.get("official_url"))
    product_evidence = _text(candidate.get("product_match_evidence") or candidate.get("product_evidence"))
    identity_evidence = _text(candidate.get("identity_verification_evidence") or candidate.get("company_evidence"))
    quote_source_url = _https_url(candidate.get("quote_source_url"))
    normalized_product = product.casefold()
    evidence_match = bool(product_evidence) and (
        normalized_product in product_evidence.casefold()
        or any(token in product_evidence.casefold() for token in normalized_product.split() if len(token) >= 4)
    )
    verified = bool(name and source_url and product_evidence and identity_evidence and evidence_match)
    return {
        "name": name or None,
        "source_url": source_url,
        "product_match_evidence": product_evidence or None,
        "identity_verification_evidence": identity_evidence or None,
        "quote_source_url": quote_source_url,
        "verified": verified,
        "status": "verified" if verified else "verification_pending",
        "missing_evidence": [
            key
            for key, ok in (
                ("supplier_name", bool(name)),
                ("https_source_url", bool(source_url)),
                ("product_match_evidence", bool(product_evidence and evidence_match)),
                ("identity_verification_evidence", bool(identity_evidence)),
            )
            if not ok
        ],
    }


def prepare(item: dict[str, Any]) -> dict[str, Any]:
    spec = item.get("specification_analysis") or {}
    product = _text(((item.get("field_evidence") or {}).get("product") or {}).get("value")) or _text(
        item.get("product_name") or item.get("title_tr") or item.get("title_original")
    )
    country = _text(((item.get("field_evidence") or {}).get("country") or {}).get("value")) or _text(
        item.get("country") or item.get("buyer-country")
    )
    ready = bool(product) and bool(spec.get("supplier_sourcing_ready"))

    raw_candidates = item.get("supplier_candidates")
    candidates: list[dict[str, Any]] = []
    if ready and isinstance(raw_candidates, list):
        for candidate in raw_candidates[:20]:
            if isinstance(candidate, dict):
                candidates.append(_candidate_status(candidate, product))

    verified_count = sum(1 for candidate in candidates if candidate.get("verified"))
    result = {
        "status": "verified_supplier_available" if verified_count else ("research_ready" if ready else "specification_review_pending"),
        "dossier_ready": ready,
        "product": product or None,
        "buyer_country": country or None,
        "search_query": f'"{product}" manufacturer exporter' if ready else None,
        "candidate_suppliers": candidates,
        "verified_supplier_count": verified_count,
        "verification_required": True,
        "blocked_by_missing_fields": [] if ready else ["specification_evidence"],
        "rule": "A supplier is verified only when name, HTTPS source URL, product-match evidence and company identity evidence are all present and consistent.",
    }
    item["supplier_research"] = result
    return result


def process_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("opportunities") or []
    ready = 0
    verified_suppliers = 0
    opportunities_with_verified_supplier = 0
    for item in rows:
        if not isinstance(item, dict):
            continue
        result = prepare(item)
        if result["dossier_ready"]:
            ready += 1
        count = int(result.get("verified_supplier_count") or 0)
        verified_suppliers += count
        if count:
            opportunities_with_verified_supplier += 1
    payload["supplier_research_summary"] = {
        "opportunities": len(rows),
        "research_ready": ready,
        "blocked": max(0, len(rows) - ready),
        "verified_suppliers": verified_suppliers,
        "opportunities_with_verified_supplier": opportunities_with_verified_supplier,
        "mode": "source_verified_candidates",
    }
    return payload
