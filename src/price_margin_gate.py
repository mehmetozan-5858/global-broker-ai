"""Stage 4: evidence-gated pricing, margin and quote-expiry checks.

This module NEVER discovers or fabricates market quotes. Research queue entries
identify missing evidence; financial outputs require source-backed inputs.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlparse

CURRENCIES = {"USD", "EUR", "GBP", "TRY", "CNY", "AED", "SAR", "QAR", "JPY", "CHF", "CAD", "AUD"}


def _positive(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() and number > 0 else None


def _https(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    p = urlparse(value)
    return p.scheme == "https" and bool(p.hostname) and not p.username and not p.password


def _date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _financial_supplier(item: dict) -> bool:
    """Require a supplier that is not only category-verified but exact-spec eligible.

    Stage 3's historic `verified=True` is deliberately insufficient for money claims.
    Stage 4 requires an explicit financial-evidence eligibility marker OR the complete
    evidence bundle plus an explicit exact-spec match.
    """
    research = item.get("supplier_research") or {}
    candidates = research.get("candidate_suppliers") or []
    name = str(item.get("verified_unit_price_supplier") or "").casefold().strip()
    if not name:
        return False
    for c in candidates:
        if not isinstance(c, dict):
            continue
        if str(c.get("name") or "").casefold().strip() != name or c.get("verified") is not True:
            continue
        if c.get("financial_evidence_eligible") is True:
            return True
        strong_bundle = (
            c.get("exact_spec_match_verified") is True
            and _https(c.get("source_url"))
            and _https(c.get("identity_evidence_url"))
            and _https(c.get("product_evidence_url"))
            and _nonempty(c.get("identity_verification_evidence"))
            and _nonempty(c.get("product_match_evidence"))
        )
        if strong_bundle:
            return True
    return False


def _quote_metadata(item: dict, prefix: str) -> list[str]:
    issues: list[str] = []
    if not _nonempty(item.get(f"{prefix}_quote_reference")):
        issues.append(f"{prefix}_quote_reference")
    issued = _date(item.get(f"{prefix}_quote_date"))
    if issued is None:
        issues.append(f"{prefix}_quote_date")
    if not _nonempty(item.get(f"{prefix}_price_unit")):
        issues.append(f"{prefix}_price_unit")
    if not _positive(item.get(f"{prefix}_quantity_basis")):
        issues.append(f"{prefix}_quantity_basis")
    return issues


def assess(item: dict, today: date | None = None) -> dict:
    today = today or date.today()
    issues: list[str] = []
    if item.get("ted_lot_selection_required") is True:
        issues.append("lot_selection")

    buy = _positive(item.get("verified_unit_price"))
    buy_source = item.get("verified_unit_price_source")
    supplier_ok = _financial_supplier(item)
    buy_currency = str(item.get("quote_currency") or "").upper().strip()
    expiry = _date(item.get("quote_valid_until"))
    if not buy or not _https(buy_source) or buy_currency not in CURRENCIES:
        issues.append("verified_supplier_quote")
    if not supplier_ok:
        issues.append("financially_eligible_exact_spec_supplier")
    issues.extend(_quote_metadata(item, "supplier"))
    if expiry is None:
        issues.append("quote_valid_until")
    elif expiry < today:
        issues.append("quote_expired")

    sell = _positive(item.get("verified_selling_unit_price"))
    sell_source = item.get("verified_selling_price_source")
    sell_currency = str(item.get("selling_currency") or "").upper().strip()
    buyer_name = item.get("selling_quote_buyer")
    if not sell or not _https(sell_source) or sell_currency not in CURRENCIES or not _nonempty(buyer_name):
        issues.append("verified_selling_quote")
    issues.extend(_quote_metadata(item, "buyer"))
    if buy_currency and sell_currency and sell_currency != buy_currency:
        issues.append("currency_mismatch")

    qty = _positive(item.get("quantity") or item.get("requested_quantity") or item.get("qty"))
    if not qty:
        issues.append("quantity")

    buy_blockers = {
        "lot_selection",
        "verified_supplier_quote", "financially_eligible_exact_spec_supplier",
        "supplier_quote_reference", "supplier_quote_date", "supplier_price_unit",
        "supplier_quantity_basis", "quote_valid_until", "quote_expired",
    }
    sell_blockers = {
        "verified_selling_quote", "buyer_quote_reference", "buyer_quote_date",
        "buyer_price_unit", "buyer_quantity_basis", "currency_mismatch", "quantity",
    }
    price_ready = not any(x in buy_blockers for x in issues)
    margin_ready = price_ready and not any(x in sell_blockers for x in issues)

    result = {
        "status": "margin_ready" if margin_ready else ("price_ready" if price_ready else "research_required"),
        "price_ready": price_ready,
        "margin_ready": margin_ready,
        "missing_or_invalid": list(dict.fromkeys(issues)),
        "quote_valid_until": expiry.isoformat() if expiry else None,
        "source_backed_only": True,
        "external_outreach_enabled": False,
        "human_review_required": True,
        "stage4_evidence_standard": "exact_spec_supplier_plus_complete_quote_metadata_v2",
        "note": "Gross product spread only; excludes freight, duty, tax, insurance, financing, fees and FX. Never a net-profit claim.",
    }
    if margin_ready:
        spread = (sell - buy) * qty
        result["gross_product_spread"] = str(spread)
        result["gross_spread_currency"] = buy_currency
        result["gross_spread_per_unit"] = str(sell - buy)
        result["gross_spread_pct_of_sale"] = str((sell - buy) / sell * 100)
        result["negative_spread"] = spread < 0
    item["price_margin_gate"] = result
    return result


def process_payload(payload: dict, today: date | None = None) -> dict:
    rows = [x for x in (payload.get("opportunities") or []) if isinstance(x, dict)]
    blockers = Counter()
    queue = []
    price_ready = margin_ready = 0
    for item in rows:
        result = assess(item, today)
        price_ready += int(result["price_ready"])
        margin_ready += int(result["margin_ready"])
        blockers.update(result["missing_or_invalid"])
        if result["margin_ready"]:
            continue
        research = item.get("supplier_research") or {}
        supplier_count = int(research.get("verified_supplier_count") or 0)
        missing = result["missing_or_invalid"]
        if any(x in missing for x in ("financially_eligible_exact_spec_supplier", "verified_supplier_quote")):
            next_agent = "Price Agent"
        elif any(x.startswith("supplier_") for x in missing) or any(x in missing for x in ("quote_valid_until", "quote_expired")):
            next_agent = "Quote Validation Agent"
        elif any(x.startswith("buyer_") for x in missing) or any(x in missing for x in ("verified_selling_quote", "currency_mismatch")):
            next_agent = "Buyer Price Agent"
        else:
            next_agent = "Source Terms Agent"
        queue.append({
            "opportunity_id": item.get("id") or item.get("opportunity_id") or item.get("notice_id"),
            "product": item.get("product_name") or item.get("title_tr") or item.get("title_original"),
            "blockers": missing,
            "next_agent": next_agent,
            "acceptance_criteria": [
                "supplier is exact-spec matched and financially evidence-eligible",
                "supplier quote has positive unit price, ISO currency, HTTPS source, quote reference, quote date, price unit, quantity basis and future validity date",
                "buyer price evidence has named buyer, positive unit price, ISO currency, HTTPS source, quote/reference date, price unit and quantity basis",
                "buy/sell currencies match and deal quantity is explicit before gross spread",
                "gross spread is never labelled net profit; no FX, freight, duty, tax or fee is guessed",
                "human approval remains mandatory before any external contact or commitment",
            ],
            "priority": 100 + min(supplier_count, 3) * 10 - len(missing) * 5,
            "research_only": True,
            "external_outreach_enabled": False,
        })
    queue.sort(key=lambda x: (-x["priority"], str(x["opportunity_id"] or "")))
    payload["price_margin_summary"] = {
        "stage": 4,
        "evidence_standard": "v2_exact_spec_complete_quote_metadata",
        "opportunities_reviewed": len(rows),
        "price_ready": price_ready,
        "gross_spread_ready": margin_ready,
        "missing_or_invalid_counts": dict(sorted(blockers.items())),
        "research_queue_count": len(queue),
        "research_queue": queue[:100],
        "queue_truncated": len(queue) > 100,
        "net_profit_calculated": False,
        "source_backed_only": True,
        "human_approval_required": True,
    }
    return payload
