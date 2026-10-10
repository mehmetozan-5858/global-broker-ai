from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

TEXT_KEYS = (
    "document_extracted_text",
    "description-lot",
    "detail_original",
    "detail_tr",
    "technical-specification",
    "technical_specification",
    "technical_requirements",
    "specification",
)

PATTERNS = {
    "quantity": [
        re.compile(r"(?im)\b(?:quantity|qty|miktar)\s*[:\-]\s*([^\n\r;]{1,120})"),
        re.compile(r"(?im)(?:الكمية)\s*[:\-]\s*([^\n\r;]{1,120})"),
    ],
    "payment_terms": [
        re.compile(r"(?im)\b(?:payment terms?|terms of payment|ödeme şart(?:ı|ları)?)\s*[:\-]\s*([^\n\r;]{2,300})"),
        re.compile(r"(?im)(?:شروط الدفع)\s*[:\-]\s*([^\n\r;]{2,300})"),
    ],
    "bid_bond": [
        re.compile(r"(?im)\b(?:bid bond|tender bond|bid security|temporary guarantee|geçici teminat)\s*[:\-]\s*([^\n\r;]{1,200})"),
        re.compile(r"(?im)(?:التأمين المؤقت|ضمان العطاء)\s*[:\-]\s*([^\n\r;]{1,200})"),
    ],
    "performance_security": [
        re.compile(r"(?im)\b(?:performance bond|performance security|kesin teminat)\s*[:\-]\s*([^\n\r;]{1,200})"),
        re.compile(r"(?im)(?:ضمان الأداء|التأمين النهائي)\s*[:\-]\s*([^\n\r;]{1,200})"),
    ],
    "delivery_terms": [
        re.compile(r"(?im)\b(?:delivery terms?|delivery condition|incoterms?|teslim şart(?:ı|ları)?)\s*[:\-]\s*([^\n\r;]{2,300})"),
        re.compile(r"(?im)(?:شروط التسليم)\s*[:\-]\s*([^\n\r;]{2,300})"),
    ],
    "delivery_location": [
        re.compile(r"(?im)\b(?:delivery location|place of delivery|place of performance|teslim yeri)\s*[:\-]\s*([^\n\r;]{2,300})"),
        re.compile(r"(?im)(?:مكان التسليم|مكان التنفيذ)\s*[:\-]\s*([^\n\r;]{2,300})"),
    ],
    "eligibility": [
        re.compile(r"(?im)\b(?:eligibility|qualification requirements?|participation requirements?|yeterlilik(?: kriterleri| şartları)?)\s*[:\-]\s*([^\n\r]{3,500})"),
        re.compile(r"(?im)(?:متطلبات التأهيل|شروط المشاركة)\s*[:\-]\s*([^\n\r]{3,500})"),
    ],
    "award_criteria": [
        re.compile(r"(?im)\b(?:award criteria|evaluation criteria|değerlendirme kriter(?:i|leri))\s*[:\-]\s*([^\n\r]{3,500})"),
        re.compile(r"(?im)(?:معايير الترسية|معايير التقييم)\s*[:\-]\s*([^\n\r]{3,500})"),
    ],
}


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(_text(v) for v in value if _text(v))
    if isinstance(value, dict):
        return "\n".join(_text(v) for v in value.values() if _text(v))
    return str(value)


def _source_blocks(item: dict[str, Any]) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    for key in TEXT_KEYS:
        value = _text(item.get(key)).strip()
        if value:
            blocks.append((key, value))
    return blocks


def _clean(value: str) -> str:
    return " ".join(value.split()).strip(" :-\t")[:500]


def extract(item: dict[str, Any]) -> dict[str, Any]:
    evidence: dict[str, dict[str, str]] = {}
    for source_field, block in _source_blocks(item):
        for target, patterns in PATTERNS.items():
            if target in evidence or item.get(target):
                continue
            for pattern in patterns:
                match = pattern.search(block)
                if not match:
                    continue
                value = _clean(match.group(1))
                if not value:
                    continue
                item[target] = value
                evidence[target] = {
                    "value": value,
                    "source_field": source_field,
                    "method": "explicit_labeled_source_text",
                }
                break

    item["a5_source_term_evidence"] = evidence
    return {
        "extracted": len(evidence),
        "fields": sorted(evidence),
        "source_backed_only": True,
    }


def process_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("opportunities") or []
    counts = {key: 0 for key in PATTERNS}
    opportunities_with_terms = 0
    for item in rows:
        if not isinstance(item, dict):
            continue
        result = extract(item)
        if result["extracted"]:
            opportunities_with_terms += 1
        for field in result["fields"]:
            counts[field] += 1
    payload["a5_source_terms_summary"] = {
        "opportunities": len(rows),
        "opportunities_with_new_terms": opportunities_with_terms,
        "new_source_backed_counts": counts,
        "rule": "Only explicitly labelled source text is promoted; unlabeled free text remains candidate evidence.",
    }
    return payload


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.a5_source_terms <json-file>")
    path = Path(sys.argv[1])
    payload = json.loads(path.read_text(encoding="utf-8"))
    process_payload(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("A5_SOURCE_TERMS", json.dumps(payload["a5_source_terms_summary"], ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    main()
