from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


STANDARD_RE = re.compile(r"\b(?:ISO\s*\d{3,6}(?::\d{4})?|EN\s*\d{2,6}(?:[-:]\d+)*|CE\b|IEC\s*\d{3,6}|ASTM\s*[A-Z]?\d{2,5})\b", re.I)
SENTENCE_RE = re.compile(r"(?<=[.!?;])\s+|\n+")

TECH_KEYS = [
    "technical-specification",
    "technical_specification",
    "technical_requirements",
    "specification",
    "description-lot",
    "detail_original",
    "detail_tr",
]
ELIGIBILITY_KEYS = [
    "selection-criteria",
    "selection_criteria",
    "eligibility",
    "qualification_requirements",
    "participation_requirements",
]
AWARD_KEYS = ["award-criteria", "award_criteria", "evaluation_criteria"]
DELIVERY_KEYS = [
    "place-of-performance-other-lot",
    "place-of-performance-city-lot",
    "place-of-performance-country-lot",
    "delivery_location",
    "delivery_terms",
]
QTY_KEYS = ["quantity-lot", "quantity", "estimated_quantity", "volume", "quantity-unit-lot", "unit"]
DOCUMENT_KEYS = [
    "official_links",
    "document_url",
    "documents_url",
    "tender_url",
    "notice_url",
    "source_url",
    "links",
]

KEYWORDS = {
    "technical": ["specification", "technical", "capacity", "dimension", "performance", "accuracy", "material", "model", "type"],
    "quantity": ["quantity", "units", "pieces", "pcs", "ton", "tonne", "kg", "litre", "liter", "adet", "miktar"],
    "delivery": ["delivery", "deliver", "place of performance", "destination", "teslim"],
    "eligibility": ["eligible", "qualification", "experience", "certificate", "license", "selection criteria", "yeterlilik"],
    "standards": ["iso", " en ", "iec", "astm", "ce marking", "standard"],
}


def text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return " | ".join(filter(None, (text(v) for v in value)))
    if isinstance(value, dict):
        return " | ".join(filter(None, (text(v) for v in value.values())))
    return str(value)


def first_values(item: dict[str, Any], keys: list[str]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for key in keys:
        value = text(item.get(key))
        if value:
            out.append({"field": key, "text": value})
    return out


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        value = value.strip()
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def collect_urls(value: Any) -> list[str]:
    urls: list[str] = []
    if isinstance(value, str):
        if value.startswith(("http://", "https://")):
            urls.append(value)
        else:
            urls.extend(re.findall(r"https?://[^\s\]\[\)\(\"'<>]+", value))
    elif isinstance(value, list):
        for entry in value:
            urls.extend(collect_urls(entry))
    elif isinstance(value, dict):
        for entry in value.values():
            urls.extend(collect_urls(entry))
    return unique_strings([u.rstrip(".,;)") for u in urls])


def document_links(item: dict[str, Any]) -> list[dict[str, str]]:
    found: list[str] = []
    for key in DOCUMENT_KEYS:
        found.extend(collect_urls(item.get(key)))
    links = unique_strings(found)
    out: list[dict[str, str]] = []
    for url in links:
        low = url.lower().split("?", 1)[0]
        if low.endswith(".pdf"):
            kind = "pdf"
        elif low.endswith((".doc", ".docx", ".xls", ".xlsx", ".zip")):
            kind = "attachment"
        else:
            kind = "source_page"
        out.append({"url": url, "kind": kind})
    return out


def source_sentences(item: dict[str, Any]) -> list[str]:
    blocks = first_values(item, TECH_KEYS + ELIGIBILITY_KEYS + AWARD_KEYS + DELIVERY_KEYS + QTY_KEYS)
    sentences: list[str] = []
    for block in blocks:
        raw = block["text"]
        parts = [p.strip() for p in SENTENCE_RE.split(raw) if p.strip()]
        sentences.extend(parts or [raw])
    return unique_strings(sentences)


def evidence_by_keywords(sentences: list[str], keywords: list[str], limit: int = 8) -> list[str]:
    hits: list[str] = []
    for sentence in sentences:
        low = f" {sentence.lower()} "
        if any(keyword in low for keyword in keywords):
            hits.append(sentence[:900])
            if len(hits) >= limit:
                break
    return hits


def standards(item: dict[str, Any], sentences: list[str]) -> list[str]:
    raw = " ".join(sentences + [text(item.get(k)) for k in TECH_KEYS])
    return unique_strings([m.group(0).upper() for m in STANDARD_RE.finditer(raw)])[:30]


def analyze_opportunity(item: dict[str, Any]) -> dict[str, Any]:
    sentences = source_sentences(item)
    technical_fields = first_values(item, TECH_KEYS)
    eligibility_fields = first_values(item, ELIGIBILITY_KEYS)
    award_fields = first_values(item, AWARD_KEYS)
    delivery_fields = first_values(item, DELIVERY_KEYS)
    quantity_fields = first_values(item, QTY_KEYS)
    docs = document_links(item)
    detected_standards = standards(item, sentences)

    technical_evidence = evidence_by_keywords(sentences, KEYWORDS["technical"])
    quantity_evidence = quantity_fields or [
        {"field": "source_text_candidate", "text": s}
        for s in evidence_by_keywords(sentences, KEYWORDS["quantity"], 6)
    ]
    delivery_evidence = delivery_fields or [
        {"field": "source_text_candidate", "text": s}
        for s in evidence_by_keywords(sentences, KEYWORDS["delivery"], 6)
    ]
    eligibility_evidence = eligibility_fields or [
        {"field": "source_text_candidate", "text": s}
        for s in evidence_by_keywords(sentences, KEYWORDS["eligibility"], 6)
    ]

    dossier = item.get("dossier") if isinstance(item.get("dossier"), dict) else {}
    has_detail = bool(technical_fields or technical_evidence or quantity_fields or eligibility_fields or delivery_fields)
    has_attachment = any(d["kind"] in {"pdf", "attachment"} for d in docs)

    if has_detail:
        status = "source_fields_analyzed"
    elif docs:
        status = "document_analysis_pending"
    else:
        status = "source_detail_missing"

    analysis = {
        "status": status,
        "source_backed_only": True,
        "technical_evidence": technical_fields[:10] or [
            {"field": "source_text_candidate", "text": s} for s in technical_evidence
        ],
        "quantity_evidence": quantity_evidence[:10],
        "delivery_evidence": delivery_evidence[:10],
        "eligibility_evidence": eligibility_evidence[:10],
        "award_evidence": award_fields[:10],
        "standards": detected_standards,
        "documents": docs,
        "attachment_requires_parsing": has_attachment,
        "source_excerpt": "\n".join(sentences[:12])[:6000] or None,
    }
    item["specification_analysis"] = analysis

    if dossier is not None:
        dossier["specification_status"] = status
        dossier["standards"] = detected_standards
        dossier["document_links"] = docs
        dossier["technical_evidence_count"] = len(analysis["technical_evidence"])
        dossier["eligibility_evidence_count"] = len(analysis["eligibility_evidence"])

    workflow = item.get("workflow")
    if isinstance(workflow, dict):
        workflow["specification_analysis"] = {
            "status": status,
            "technical_evidence_count": len(analysis["technical_evidence"]),
            "document_count": len(docs),
            "attachment_requires_parsing": has_attachment,
        }
    return item


def analyze_payload(payload: dict[str, Any]) -> dict[str, Any]:
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        return payload
    analyzed = 0
    pending_documents = 0
    attachments = 0
    for item in opportunities:
        if not isinstance(item, dict):
            continue
        analyze_opportunity(item)
        analyzed += 1
        spec = item.get("specification_analysis") or {}
        if spec.get("status") == "document_analysis_pending":
            pending_documents += 1
        if spec.get("attachment_requires_parsing"):
            attachments += 1
    payload["specification_analysis"] = {
        "version": 1,
        "mode": "source_evidence_only",
        "analyzed_count": analyzed,
        "document_analysis_pending": pending_documents,
        "attachments_requiring_parser": attachments,
    }
    return payload


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.specification <json-file>")
    path = Path(sys.argv[1])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload = analyze_payload(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
