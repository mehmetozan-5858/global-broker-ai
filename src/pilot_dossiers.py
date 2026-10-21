"""Prioritize ten source-backed Global Broker dossiers without inventing market data."""
from __future__ import annotations
from collections import Counter
from typing import Any
from datetime import date
from src.opportunity_quality import parse_deadline
from src.ted_search_fields import notice_context


def _present(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return False
    text = str(value).strip().lower()
    return bool(text) and text not in {"unknown", "pending", "none", "null", "n/a", "—", "-"}


def _first(row: dict, *keys: str) -> Any:
    return next((row[k] for k in keys if _present(row.get(k))), None)


def _official_source(row: dict) -> Any:
    direct = _first(
        row,
        "source_url",
        "source-url",
        "notice_url",
        "detail_url",
        "official_url",
        "document_url",
        "url",
    )
    if direct:
        return direct
    for url in row.get("official_links") or []:
        if isinstance(url, str) and url.startswith("https://"):
            return url
    dossier = row.get("dossier") or {}
    for url in dossier.get("official_links") or []:
        if isinstance(url, str) and url.startswith("https://"):
            return url
    return None


def _spec_ready(row: dict) -> bool:
    analysis = row.get("specification_analysis") or {}
    dossier = row.get("dossier") or {}
    stage4 = row.get("stage4_research") or {}
    gate = stage4.get("document_access_gate") or {}
    return bool(
        analysis.get("supplier_sourcing_ready") is True
        or dossier.get("supplier_sourcing_ready") is True
        or gate.get("exact_specification_extracted") is True
    )


def build(payload: dict, today: date | None = None) -> dict:
    today = today or date.today()
    rows = [r for r in (payload.get("opportunities") or []) if isinstance(r, dict)]
    ranked = []
    missing_counts: Counter[str] = Counter()
    for index, row in enumerate(rows):
        fields = row.get("field_evidence") or {}
        buyer = row.get("buyer_verification") or {}
        supplier = row.get("supplier_research") or {}
        price = row.get("price_margin_gate") or {}
        source = _official_source(row)
        product = (fields.get("product") or {}).get("value") or _first(row, "product_name", "title_original", "title_tr")
        buyer_name = _first(row, "buyer-name", "buyer_name", "contracting_authority", "organization_name", "agency")
        quantity = _first(row, "quantity-lot", "quantity", "requested_quantity", "qty", "estimated_quantity")
        deadline = _first(row, "deadline-receipt-tender-date-lot", "submission_deadline_date", "deadline_date", "deadline")
        country = _first(row, "buyer-country", "country_name", "country", "country_code")
        scope_pending = row.get("source_lot_selection_required") is True or row.get("ted_lot_selection_required") is True
        spec_ready = _spec_ready(row) and not scope_pending
        deadline = _first(row, "deadline_normalized", "deadline-receipt-tender-date-lot", "submission_deadline_date", "deadline_date", "deadline")
        parsed_deadline = parse_deadline(deadline)
        current = parsed_deadline is not None and parsed_deadline >= today
        context = notice_context(row)
        research_notice = bool(context and context.get("research_only"))
        freshness = "deadline_unknown_review" if parsed_deadline is None else "expired" if not current else "open_by_date_only"
        missing = [k for k, v in {
            "source_url": bool(source and str(source).startswith("https://")),
            "product": _present(product),
            "buyer_name": _present(buyer_name),
            "quantity": _present(quantity) and not scope_pending,
            "lot_selection": not scope_pending,
            "current_deadline": current,
            "call_for_tenders": not research_notice,
            "deadline": _present(deadline),
            "country": _present(country),
            "exact_specification": spec_ready,
            "verified_supplier": int(supplier.get("verified_supplier_count") or 0) > 0,
            "verified_price": price.get("price_ready") is True,
            "buyer_verification": bool(row.get("buyer_verified") is True or buyer.get("verified") is True),
        }.items() if not v]
        missing_counts.update(missing)
        score = (100 - 9 * len(missing)
                 + (12 if spec_ready else 0)
                 + (15 if price.get("price_ready") is True else 0)
                 + (10 if int(supplier.get("verified_supplier_count") or 0) > 0 else 0))
        # The score ranks research work, never probability of deal or profit.
        row["commercial_dossier"] = {
            "status": "research_required" if missing else "evidence_complete_pending_human_review",
            "missing_evidence": missing,
            "priority_score": max(0, score),
            "official_source": source,
            "exact_specification_ready": spec_ready,
            "human_review_required": True,
            "external_outreach_enabled": False,
            "freshness_status": freshness,
            "research_notice": research_notice,
        }
        if research_notice:
            next_step = "research notice only; locate a current call for tenders"
        elif not current:
            next_step = "verify a current submission deadline before quotation work"
        elif scope_pending:
            next_step = "select and verify one lot scope before quotation work"
        elif "source_url" in missing or "buyer_name" in missing:
            next_step = "verify official source and buyer"
        elif "exact_specification" in missing:
            next_step = "extract exact technical specification from procurement documents"
        elif "verified_supplier" in missing:
            next_step = "verify exact-spec supplier"
        elif "verified_price" in missing:
            next_step = "obtain documented supplier price"
        else:
            next_step = "complete commercial terms and human review"
        ranked.append({
            "opportunity_index": index,
            "opportunity_id": row.get("opportunity_id") or row.get("id") or row.get("publication-number") or row.get("notice_id"),
            "priority_score": max(0, score),
            "missing_evidence": missing,
            "next_step": next_step,
            "current_call_by_date_only": current and not research_notice,
        })
    ranked.sort(key=lambda x: (not x["current_call_by_date_only"], -x["priority_score"], len(x["missing_evidence"]), x["opportunity_index"]))
    payload["pilot_dossier_summary"] = {
        "opportunities_reviewed": len(rows),
        "pilot_target": 10,
        "selected_count": min(10, len(ranked)),
        "fully_evidenced_count": sum(not x["missing_evidence"] for x in ranked),
        "missing_evidence_counts": dict(sorted(missing_counts.items())),
        "first_ten": ranked[:10],
        "no_invented_quotes": True,
        "human_review_required": True,
    }
    return payload
