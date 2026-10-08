from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


STANDARD_RE = re.compile(r"\b(?:ISO\s*\d{3,6}(?::\d{4})?|EN\s*\d{2,6}(?:[-:]\d+)*|CE\b|IEC\s*\d{3,6}|ASTM\s*[A-Z]?\d{2,5})\b", re.I)
SENTENCE_RE = re.compile(r"(?<=[.!?;])\s+|\n+")

STRUCTURED_TECH_KEYS = [
    "technical-specification",
    "technical_specification",
    "technical_requirements",
    "specification",
]
NARRATIVE_KEYS = ["description-lot", "detail_original", "detail_tr"]
DOCUMENT_TEXT_KEYS = ["document_extracted_text"]
TECH_KEYS = STRUCTURED_TECH_KEYS + NARRATIVE_KEYS + DOCUMENT_TEXT_KEYS
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
    "technical": ["specification", "technical", "capacity", "dimension", "performance", "accuracy", "material", "model", "type", "equipment", "device", "requirement", "minimum", "maximum", "tolerance"],
    "quantity": ["quantity", "units", "pieces", "pcs", "ton", "tonne", "kg", "litre", "liter", "adet", "miktar", "套", "台", "吨"],
    "delivery": ["delivery", "deliver", "place of performance", "destination", "teslim", "交付", "履行"],
    "eligibility": ["eligible", "qualification", "experience", "certificate", "license", "selection criteria", "yeterlilik", "资格"],
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


def _meaningful_narrative(fields: list[dict[str, str]], technical_hits: list[str]) -> bool:
    longest = max((len(x["text"]) for x in fields), default=0)
    return longest >= 120 and bool(technical_hits)


def _append_unique(values: Any, value: str) -> list[str]:
    out = list(values) if isinstance(values, list) else []
    if value not in out:
        out.append(value)
    return out


def analyze_opportunity(item: dict[str, Any]) -> dict[str, Any]:
    sentences = source_sentences(item)
    structured_technical = first_values(item, STRUCTURED_TECH_KEYS)
    narrative_fields = first_values(item, NARRATIVE_KEYS)
    document_fields = first_values(item, DOCUMENT_TEXT_KEYS)
    eligibility_fields = first_values(item, ELIGIBILITY_KEYS)
    award_fields = first_values(item, AWARD_KEYS)
    delivery_fields = first_values(item, DELIVERY_KEYS)
    quantity_fields = first_values(item, QTY_KEYS)
    docs = document_links(item)
    detected_standards = standards(item, sentences)

    technical_hits = evidence_by_keywords(sentences, KEYWORDS["technical"])
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

    has_attachment = any(d["kind"] in {"pdf", "attachment"} for d in docs)
    extraction = item.get("document_extraction") if isinstance(item.get("document_extraction"), dict) else {}
    document_parsed = bool(document_fields) and extraction.get("parsed_count", 0) > 0
    structured_ready = bool(structured_technical)
    narrative_ready = _meaningful_narrative(narrative_fields, technical_hits) and bool(
        quantity_evidence or delivery_evidence or eligibility_evidence or detected_standards
    )
    document_ready = document_parsed and _meaningful_narrative(document_fields, technical_hits) and bool(
        quantity_evidence or delivery_evidence or eligibility_evidence or detected_standards
    )
    specification_ready = structured_ready or narrative_ready or document_ready

    if structured_ready:
        status = "structured_specification_analyzed"
    elif document_ready:
        status = "source_document_analyzed"
    elif narrative_ready:
        status = "source_description_analyzed"
    elif docs:
        status = "document_analysis_pending"
    elif narrative_fields:
        status = "source_description_insufficient"
    else:
        status = "source_detail_missing"

    if structured_technical:
        technical_evidence = structured_technical[:10]
    else:
        origin = "source_document_candidate" if document_parsed else "source_text_candidate"
        technical_evidence = [{"field": origin, "text": s} for s in technical_hits][:10]

    analysis = {
        "status": status,
        "source_backed_only": True,
        "supplier_sourcing_ready": specification_ready,
        "structured_specification_present": structured_ready,
        "document_text_present": bool(document_fields),
        "document_parsed": document_parsed,
        "technical_evidence": technical_evidence,
        "quantity_evidence": quantity_evidence[:10],
        "delivery_evidence": delivery_evidence[:10],
        "eligibility_evidence": eligibility_evidence[:10],
        "award_evidence": award_fields[:10],
        "standards": detected_standards,
        "documents": docs,
        "attachment_requires_parsing": has_attachment and not document_parsed,
        "source_excerpt": "\n".join(sentences[:12])[:6000] or None,
    }
    item["specification_analysis"] = analysis

    dossier = item.get("dossier") if isinstance(item.get("dossier"), dict) else None
    if dossier is not None:
        dossier["specification_status"] = status
        dossier["specification_sourcing_ready"] = specification_ready
        dossier["standards"] = detected_standards
        dossier["document_links"] = docs
        dossier["document_parsed"] = document_parsed
        dossier["technical_evidence_count"] = len(analysis["technical_evidence"])
        dossier["eligibility_evidence_count"] = len(analysis["eligibility_evidence"])
        if not specification_ready:
            dossier["supplier_sourcing_ready"] = False
            dossier["missing_fields"] = _append_unique(dossier.get("missing_fields"), "specification_evidence")

    supplier = item.get("supplier_research")
    if isinstance(supplier, dict) and not specification_ready:
        supplier["dossier_ready"] = False
        supplier["status"] = "specification_review_pending"
        supplier["blocked_by_missing_fields"] = _append_unique(
            supplier.get("blocked_by_missing_fields"), "specification_evidence"
        )

    workflow = item.get("workflow")
    if isinstance(workflow, dict):
        workflow["specification_analysis"] = {
            "status": status,
            "supplier_sourcing_ready": specification_ready,
            "technical_evidence_count": len(analysis["technical_evidence"]),
            "document_count": len(docs),
            "document_parsed": document_parsed,
            "attachment_requires_parsing": has_attachment and not document_parsed,
        }
        dossier_flow = workflow.get("opportunity_dossier")
        if isinstance(dossier_flow, dict) and not specification_ready:
            dossier_flow["status"] = "specification_review_pending"
            dossier_flow["missing_fields"] = _append_unique(
                dossier_flow.get("missing_fields"), "specification_evidence"
            )
    return item


def analyze_payload(payload: dict[str, Any]) -> dict[str, Any]:
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        return payload
    analyzed = 0
    ready = 0
    pending_documents = 0
    insufficient = 0
    attachments = 0
    parsed_documents = 0
    for item in opportunities:
        if not isinstance(item, dict):
            continue
        analyze_opportunity(item)
        analyzed += 1
        spec = item.get("specification_analysis") or {}
        if spec.get("supplier_sourcing_ready"):
            ready += 1
        if spec.get("status") == "document_analysis_pending":
            pending_documents += 1
        if spec.get("status") in {"source_description_insufficient", "source_detail_missing"}:
            insufficient += 1
        if spec.get("attachment_requires_parsing"):
            attachments += 1
        if spec.get("document_parsed"):
            parsed_documents += 1
    payload["specification_analysis"] = {
        "version": 3,
        "mode": "source_evidence_plus_public_documents",
        "analyzed_count": analyzed,
        "supplier_sourcing_ready": ready,
        "document_analysis_pending": pending_documents,
        "insufficient_source_detail": insufficient,
        "attachments_requiring_parser": attachments,
        "parsed_document_opportunities": parsed_documents,
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
