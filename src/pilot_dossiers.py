"""Prioritize ten source-backed Global Broker dossiers without inventing market data."""
from __future__ import annotations
from collections import Counter
from typing import Any


def _present(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return False
    text = str(value).strip().lower()
    return bool(text) and text not in {"unknown", "pending", "none", "null", "n/a", "—", "-"}


def _first(row: dict, *keys: str) -> Any:
    return next((row[k] for k in keys if _present(row.get(k))), None)


def build(payload: dict) -> dict:
    rows = [r for r in (payload.get("opportunities") or []) if isinstance(r, dict)]
    ranked = []
    missing_counts: Counter[str] = Counter()
    for index, row in enumerate(rows):
        fields = row.get("field_evidence") or {}
        buyer = row.get("buyer_verification") or {}
        supplier = row.get("supplier_research") or {}
        price = row.get("price_margin_gate") or {}
        core = row.get("core_field_coverage") or {}
        source = _first(row, "source_url", "source-url", "notice_url", "detail_url", "official_url", "url")
        product = (fields.get("product") or {}).get("value") or _first(row, "product_name", "title_original", "title_tr")
        buyer_name = _first(row, "buyer-name", "buyer_name", "contracting_authority", "organization_name", "agency")
        quantity = _first(row, "quantity-lot", "quantity", "requested_quantity", "qty", "estimated_quantity")
        deadline = _first(row, "deadline-receipt-tender-date-lot", "submission_deadline_date", "deadline_date", "deadline")
        country = _first(row, "buyer-country", "country_name", "country", "country_code")
        missing = [k for k, v in {
            "source_url": bool(source and str(source).startswith("https://")),
            "product": _present(product),
            "buyer_name": _present(buyer_name),
            "quantity": _present(quantity),
            "deadline": _present(deadline),
            "country": _present(country),
            "verified_supplier": int(supplier.get("verified_supplier_count") or 0) > 0,
            "verified_price": price.get("price_ready") is True,
            "buyer_verification": bool(row.get("buyer_verified") is True or buyer.get("verified") is True),
        }.items() if not v]
        missing_counts.update(missing)
        score = (100 - 9 * len(missing)
                 + (15 if price.get("price_ready") is True else 0)
                 + (10 if int(supplier.get("verified_supplier_count") or 0) > 0 else 0))
        # The score ranks research work, never probability of deal or profit.
        row["commercial_dossier"] = {
            "status": "research_required" if missing else "evidence_complete_pending_human_review",
            "missing_evidence": missing,
            "priority_score": max(0, score),
            "human_review_required": True,
            "external_outreach_enabled": False,
        }
        ranked.append({
            "opportunity_index": index,
            "opportunity_id": row.get("opportunity_id") or row.get("id") or row.get("publication-number") or row.get("notice_id"),
            "priority_score": max(0, score),
            "missing_evidence": missing,
            "next_step": "verify official source and buyer" if "source_url" in missing or "buyer_name" in missing else
                         "verify supplier" if "verified_supplier" in missing else
                         "obtain documented supplier price" if "verified_price" in missing else
                         "complete commercial terms and human review",
        })
    ranked.sort(key=lambda x: (-x["priority_score"], len(x["missing_evidence"]), x["opportunity_index"]))
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
