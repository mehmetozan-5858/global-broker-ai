from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return " ".join(_text(v) for v in value if _text(v)).strip()
    if isinstance(value, dict):
        # Prefer English/Turkish scalar/list entries before flattening arbitrary maps.
        for key in ("tr", "tur", "en", "eng"):
            if key in value and _text(value[key]):
                return _text(value[key])
        return " ".join(_text(v) for v in value.values() if _text(v)).strip()
    return str(value).strip()


def _pick(item: dict[str, Any], keys: tuple[str, ...]) -> tuple[str, str | None]:
    for key in keys:
        if key in item:
            value = _text(item.get(key))
            if value:
                return value, key
    return "", None


FIELDS: dict[str, tuple[str, ...]] = {
    "country": (
        "buyer-country", "country_name", "project_ctry_name", "country", "buyer_country",
        "country_code", "project_ctry_code", "buyer_country_code",
    ),
    "city": (
        "place-of-performance-city-lot", "place_of_performance_city", "buyer_city",
        "delivery_city", "city", "project_city", "delivery_location", "project_location",
    ),
    "product": (
        "product_name", "product", "product_or_service", "title_tr", "title_original",
        "bid_description", "notice-title", "title",
    ),
    "quantity": (
        "quantity-lot", "quantity", "requested_quantity", "qty", "contract_quantity",
    ),
    "deadline": (
        "deadline-receipt-tender-date-lot", "responseDeadLine", "deadline_date",
        "submission_deadline_date", "deadline", "closing_date",
    ),
    "buyer": ("buyer-name", "buyer_name", "borrower", "agency", "department", "office"),
}


def annotate(item: dict[str, Any]) -> dict[str, Any]:
    evidence: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for name, keys in FIELDS.items():
        value, source_key = _pick(item, keys)
        status = "source_backed" if value else "missing"
        evidence[name] = {
            "value": value or None,
            "status": status,
            "source_field": source_key,
            "inferred": False,
        }
        if not value:
            missing.append(name)

    # Do not promote title text to a verified quantity/city/country. A3 keeps unknowns explicit.
    item["field_evidence"] = evidence
    item["missing_core_fields"] = missing
    item["core_field_coverage"] = {
        "verified_or_source_backed": len(FIELDS) - len(missing),
        "total": len(FIELDS),
        "complete": not missing,
    }
    return item


def process_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("opportunities") or []
    for item in rows:
        if isinstance(item, dict):
            annotate(item)
    counts = {name: 0 for name in FIELDS}
    complete = 0
    for item in rows:
        ev = item.get("field_evidence") or {}
        for name in counts:
            if (ev.get(name) or {}).get("status") == "source_backed":
                counts[name] += 1
        if (item.get("core_field_coverage") or {}).get("complete"):
            complete += 1
    payload["field_evidence_summary"] = {
        "opportunities": len(rows),
        "complete_core_records": complete,
        "source_backed_counts": counts,
        "rule": "missing values remain unknown; no inferred value is promoted as source-backed",
    }
    return payload


def main(path: str) -> None:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    process_payload(data)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("FIELD_EVIDENCE", json.dumps(data["field_evidence_summary"], ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.field_evidence <payload.json>")
    main(sys.argv[1])
