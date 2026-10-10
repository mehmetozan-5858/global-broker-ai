from __future__ import annotations

from typing import Any

TERM_FIELDS = {
    "quantity": ("quantity-lot", "quantity", "requested_quantity", "qty", "estimated_quantity", "volume"),
    "payment": ("payment_terms", "payment-terms", "terms_of_payment", "payment"),
    "bond": ("bid_bond", "tender_bond", "bid_security", "guarantee"),
    "performance_security": ("performance_security", "performance_bond", "final_guarantee"),
    "delivery": ("delivery_terms", "incoterm", "place-of-performance-other-lot", "delivery_location"),
    "eligibility": ("eligibility", "selection-criteria", "selection_criteria", "qualification_requirements"),
    "award": ("award-criteria", "award_criteria", "evaluation_criteria"),
}


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return " | ".join(filter(None, (_text(v) for v in value)))
    if isinstance(value, dict):
        return " | ".join(filter(None, (_text(v) for v in value.values())))
    return str(value)


def analyze(item: dict[str, Any]) -> dict[str, Any]:
    terms: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    extracted = item.get("a5_source_term_evidence") if isinstance(item.get("a5_source_term_evidence"), dict) else {}
    for name, keys in TERM_FIELDS.items():
        value = ""
        source = None
        for key in keys:
            value = _text(item.get(key))
            if value:
                source = key
                break
        provenance = extracted.get(source) if source and isinstance(extracted.get(source), dict) else None
        terms[name] = {
            "value": value or None,
            "source_field": source,
            "status": "source_backed" if value else "missing",
            "extracted_from_labeled_source_text": bool(provenance),
            "evidence_source_field": provenance.get("source_field") if provenance else None,
        }
        if not value:
            missing.append(name)
    result = {
        "terms": terms,
        "missing": missing,
        "complete": not missing,
        "source_backed_only": True,
        "rule": "Quantity, payment, bonds, delivery, eligibility and award terms are never inferred when absent from explicit source evidence.",
    }
    item["commercial_terms"] = result
    return result


def process_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("opportunities") or []
    complete = 0
    counts = {name: 0 for name in TERM_FIELDS}
    for item in rows:
        if not isinstance(item, dict):
            continue
        result = analyze(item)
        if result["complete"]:
            complete += 1
        for name, fact in result["terms"].items():
            if fact["status"] == "source_backed":
                counts[name] += 1
    payload["commercial_terms_summary"] = {
        "opportunities": len(rows),
        "complete": complete,
        "source_backed_counts": counts,
    }
    return payload
