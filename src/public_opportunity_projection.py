"""Strict public projection for Global Broker opportunities.

Public/customer-facing payloads are built from an explicit allowlist. Unknown or
new private fields are dropped by default.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime
import sys
from pathlib import Path
from typing import Any

from src.opportunity_identity import stable_opportunity_id
from src.ted_search_fields import notice_context

BUYER_DISPLAY = "Alıcı kimliği kontrollü tanıştırma ile paylaşılır"

SECTOR_KEYWORDS = {
    "furniture": ("furniture", "mobilya", "chair", "table", "desk", "cabinet", "wood"),
    "machinery": ("cnc", "machine", "machinery", "makine", "lathe", "milling", "industrial equipment", "spare part"),
    "textile": ("textile", "tekstil", "garment", "apparel", "fabric", "kumaş", "uniform", "yarn"),
    "automotive": ("automotive", "vehicle part", "auto part", "otomotiv", "brake", "suspension", "filter", "tire", "tyre"),
    "packaging": ("packaging", "ambalaj", "carton", "cardboard", "corrugated", "label", "bottle", "container"),
    "construction": ("construction", "building material", "inşaat", "ceramic", "tile", "door", "window", "insulation"),
    "food": ("food", "gıda", "grain", "rice", "wheat", "lentil", "nuts", "fruit", "agriculture"),
    "chemicals": ("chemical", "kimya", "fertilizer", "gübre", "resin", "polymer", "paint", "coating"),
    "electronics": ("electrical", "electronic", "elektrik", "elektronik", "cable", "switchgear", "lighting", "transformer", "battery"),
    "medical": ("medical", "medikal", "hospital", "laboratory", "diagnostic", "surgical", "sterilization"),
}


def _scalar(value: Any) -> Any:
    return value if isinstance(value, (str, int, float, bool)) and value not in ("") else None


def _pick(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = _scalar(row.get(key))
        if value is not None:
            return value
    return None


def _evidence_value(row: dict[str, Any], name: str) -> Any:
    evidence = row.get("field_evidence")
    if not isinstance(evidence, dict):
        return None
    item = evidence.get(name)
    if not isinstance(item, dict) or item.get("status") != "source_backed":
        return None
    return _scalar(item.get("value"))


def infer_sector(row: dict[str, Any]) -> str:
    explicit = _scalar(row.get("sector_id"))
    if isinstance(explicit, str) and explicit:
        return explicit
    haystack = " ".join(str(x) for x in (
        _pick(row, ("product_name", "product", "title_tr", "title_original", "notice-title", "title")),
        _evidence_value(row, "product"),
    ) if x).lower()
    for sector, words in SECTOR_KEYWORDS.items():
        if any(word in haystack for word in words):
            return sector
    return "other"


def project_public_opportunity(row: dict[str, Any], *, sector_id: str | None = None) -> dict[str, Any]:
    """Return only explicitly approved customer-facing fields."""
    if not isinstance(row, dict):
        raise TypeError("opportunity must be a dict")

    review = row.get("export_goods_review") if isinstance(row.get("export_goods_review"), dict) else {}
    coverage = row.get("core_field_coverage") if isinstance(row.get("core_field_coverage"), dict) else {}
    verification = row.get("verification") if isinstance(row.get("verification"), dict) else {}

    result: dict[str, Any] = {
        "opportunity_id": stable_opportunity_id(row),
        "buyer_masked": True,
        "buyer_display": BUYER_DISPLAY,
        "sector_id": sector_id or infer_sector(row),
    }
    context = notice_context(row)
    previous_context = row.get("notice_context")
    if "form-type" not in row and isinstance(previous_context, dict) and (row.get("source") == "TED" or row.get("source_name") == "TED"):
        context = notice_context({"source": "TED", "form-type": previous_context.get("form_type")})
    if context is not None:
        result["notice_context"] = context

    candidates = {
        "product_name": _evidence_value(row, "product") or _pick(row, ("product_name", "product", "title_tr", "title_original", "notice-title", "title")),
        "country": _evidence_value(row, "country") or _pick(row, ("buyer-country", "country_name", "project_ctry_name", "country", "country_code")),
        "country_code": _pick(row, ("country_code", "buyer_country_code")),
        "approx_quantity": _evidence_value(row, "quantity") or _pick(row, ("quantity-lot", "quantity", "requested_quantity", "qty", "approx_quantity")),
        "deadline": _evidence_value(row, "deadline") or _pick(row, ("deadline-receipt-tender-date-lot", "responseDeadLine", "deadline_date", "submission_deadline_date", "deadline", "closing_date")),
        "delivery_term": _pick(row, ("incoterm", "delivery_term", "delivery_terms", "delivery_condition")),
        "opportunity_type": _pick(row, ("opportunity_type", "notice_type", "procurement_method", "type")),
        "verification_category": _pick(row, ("verification_category", "verification_status")) or _scalar(verification.get("status")),
        "source_type": _pick(row, ("source_type", "portal_family")),
        "source_name": _pick(row, ("source", "source_name")),
        "goods_status": _scalar(review.get("status")) or ("goods_candidate" if row.get("goods_status") == "goods_candidate" else None),
        "published_at": _pick(row, ("published_at", "publication_date", "date", "created_at")),
        "status": _pick(row, ("status", "opportunity_status")),
    }
    for key, value in candidates.items():
        if value is not None:
            result[key] = value
    detail = _scalar(row.get('public_product_detail') or row.get('product_detail'))
    if detail:
        result['product_detail'] = detail

    research = row.get('supplier_research')
    if isinstance(research, dict):
        suppliers = research.get('candidate_suppliers')
        if isinstance(suppliers, list):
            capability = [s for s in suppliers if isinstance(s, dict) and s.get('verified') is True and s.get('match_level') == 'capability_only']
            if capability:
                result['supplier_capability_count'] = len(capability)
                result['supplier_match_status'] = 'capability_only_exact_spec_pending'

    # Publish only an explicitly sourced notice estimate, never a supplier price.
    structured = row.get("structured_source_evidence")
    fact = structured.get("estimated_value") if isinstance(structured, dict) else None
    search_budget = (
        isinstance(fact, dict) and fact.get("source_path") == "ted_search.estimated-value-lot"
        and row.get("source") == "TED" and row.get("ted_lot_count") == 1
        and row.get("ted_lot_selection_required") is False
        and row.get("ted_search_lot_ids") == [fact.get("lot_id")]
        and fact.get("source_url") == "https://ted.europa.eu/en/notice/-/detail/" + str(row.get("publication-number") or "")
    )
    if isinstance(fact, dict) and fact.get("inferred") is False and (search_budget or fact.get("source_path") == "procurementproject/requestedtendertotal/estimatedoverallcontractamount"):
        amount = fact.get("value")
        currency = fact.get("currency")
        try:
            positive = not isinstance(amount, bool) and Decimal(str(amount)).is_finite() and Decimal(str(amount)) > 0
        except (InvalidOperation, ValueError):
            positive = False
        if positive and isinstance(currency, str) and re.fullmatch(r"[A-Z]{3}", currency) and str(row.get("estimated_value")) == str(amount) and row.get("budget_currency") == currency:
            result["estimated_budget"] = str(amount)
            result["budget_currency"] = currency
    # The publication pipeline may retain this bounded public summary after it
    # removes the private XML documents and provenance excerpts from its snapshot.
    public_terms = row.get("public_source_terms")
    if not isinstance(public_terms, dict) and row.get("buyer_masked") is True and row.get("goods_status") == "goods_candidate":
        # A previous projection contains the validated notice estimate only.
        public_terms = {"kind": "notice_estimate", "estimated_budget": row.get("estimated_budget"),
                        "budget_currency": row.get("budget_currency")}
    if isinstance(public_terms, dict) and public_terms.get("kind") == "notice_estimate":
        amount = public_terms.get("estimated_budget")
        currency = public_terms.get("budget_currency")
        try:
            positive = not isinstance(amount, bool) and Decimal(str(amount)).is_finite() and Decimal(str(amount)) > 0
        except (InvalidOperation, ValueError):
            positive = False
        if "estimated_budget" not in result and positive and isinstance(currency, str) and re.fullmatch(r"[A-Z]{3}", currency):
            result["estimated_budget"] = str(amount)
            result["budget_currency"] = currency
    if type(row.get("ted_lot_count")) is int and row["ted_lot_count"] >= 0:
        result["lot_count"] = row["ted_lot_count"]
        result["lot_selection_required"] = row.get("ted_lot_selection_required") is True
    if isinstance(row.get("ted_lots"), list):
        result["lot_count"] = len(row["ted_lots"])
        result["lot_selection_required"] = row.get("ted_lot_selection_required") is True

    # Publish only fixed review reason codes, never private document text or URLs.
    analysis = row.get("specification_analysis")
    reasons = analysis.get("document_coverage_blockers") if isinstance(analysis, dict) else None
    if reasons is None and row.get("buyer_masked") is True:
        # Preserve vetted enum codes when re-projecting an already public feed.
        reasons = row.get("document_coverage_blockers")
    allowed_reasons = ("source_text_truncated", "attachment_candidates_skipped")
    if isinstance(reasons, list):
        approved_reasons = [code for code in allowed_reasons if code in reasons]
        if approved_reasons:
            result["document_coverage_blockers"] = approved_reasons

    # Customer-safe review metadata contains enums only, never source excerpts.
    if row.get("source_lot_selection_required") is True or row.get("ted_lot_selection_required") is True or row.get("lot_selection_required") is True:
        result["lot_selection_required"] = True
    if "lot_count" not in result and type(row.get("lot_count")) is int and row["lot_count"] > 0:
        result["lot_count"] = row["lot_count"]
    if row.get("source") == "WORLD_BANK" and type(row.get("source_lot_count")) is int and 0 < row["source_lot_count"] <= 64:
        result["lot_count"] = row["source_lot_count"]
    line_items = row.get("source_line_items")
    evidence = row.get("source_line_items_evidence")
    if isinstance(line_items, list) and isinstance(evidence, dict) and evidence.get("method") == "explicit_notice_table" and 0 < len(line_items) <= 64:
        result["source_line_item_count"] = len(line_items)
    elif type(row.get("source_line_item_count")) is int and 0 < row["source_line_item_count"] <= 64:
        result["source_line_item_count"] = row["source_line_item_count"]
    extraction = row.get("document_extraction")
    if isinstance(extraction, dict):
        attempts = extraction.get("attempts")
        attempts = attempts if isinstance(attempts, list) else []
        official_notice = any(isinstance(a, dict) and a.get("status") == "parsed"
                              and a.get("format") == "world_bank_notice_json" for a in attempts)
        parsed = type(extraction.get("parsed_count")) is int and extraction["parsed_count"] > 0
        has_text = isinstance(row.get("document_extracted_text"), str) and bool(row["document_extracted_text"].strip())
        result["source_text_status"] = ("official_notice_read" if official_notice else "source_text_read") if parsed and has_text else "pending"
    elif isinstance(row.get("source_text_status"), str) and row.get("source_text_status") in {"official_notice_read", "source_text_read", "pending"}:
        # Projection runs again at the authenticated API boundary.
        result["source_text_status"] = row["source_text_status"]
    completion = row.get("data_completion")
    missing = completion.get("missing_fields") if isinstance(completion, dict) else row.get("dossier_missing_fields")
    if isinstance(missing, list):
        allowed_missing = ("lot_selection", "buyer_identity", "product", "quantity_or_budget", "deadline", "country", "official_source")
        result["dossier_missing_fields"] = [key for key in allowed_missing if key in missing]
    if result.get("lot_selection_required") is True:
        missing = result.setdefault("dossier_missing_fields", [])
        if "lot_selection" not in missing:
            missing.insert(0, "lot_selection")

    source_state = row.get("notice_source_state", row.get("source_data_state"))
    if isinstance(source_state, str) and source_state in {"current_document", "previously_verified_document"}:
        verified = row.get("notice_source_verified_at", row.get("source_verified_at"))
        try:
            datetime.fromisoformat(str(verified))
        except ValueError:
            pass
        else:
            result["source_data_state"] = source_state
            result["source_verified_at"] = str(verified)[:40]

    verified_count = coverage.get("verified_or_source_backed", row.get("source_backed_fields"))
    total_count = coverage.get("total", row.get("source_field_total"))
    if isinstance(verified_count, int) and verified_count >= 0:
        result["source_backed_fields"] = verified_count
    if isinstance(total_count, int) and total_count > 0:
        result["source_field_total"] = total_count
    if result.get("lot_selection_required") is True:
        for ambiguous in ("approx_quantity", "estimated_budget", "budget_currency"):
            result.pop(ambiguous, None)
    return result


def project_public_feed(data: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for row in data.get("opportunities") or []:
        if not isinstance(row, dict):
            continue
        review = row.get("export_goods_review") if isinstance(row.get("export_goods_review"), dict) else {}
        if review.get("status") != "goods_candidate":
            continue
        rows.append(project_public_opportunity(row))
    return {
        "mode": "public_allowlist_feed",
        "privacy_notice": "Buyer identity, contact data, source URLs, document text and private research are not published.",
        "opportunities": rows,
        "count": len(rows),
    }


def _main(argv: list[str]) -> int:
    if len(argv) != 3:
        raise SystemExit("usage: python -m src.public_opportunity_projection INPUT OUTPUT")
    source, destination = map(Path, argv[1:])
    data = json.loads(source.read_text(encoding="utf-8"))
    destination.write_text(json.dumps(project_public_feed(data), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"PUBLIC_ALLOWLIST_FEED opportunities={len(project_public_feed(data)['opportunities'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
