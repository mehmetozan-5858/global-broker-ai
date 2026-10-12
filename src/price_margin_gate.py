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
FIELDS = ("supplier_quote", "quote_valid_until", "selling_quote", "quantity", "currency")


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


def _supplier(item: dict) -> bool:
    research = item.get("supplier_research") or {}
    candidates = research.get("candidate_suppliers") or []
    name = str(item.get("verified_unit_price_supplier") or "").casefold().strip()
    return bool(name and any(
        isinstance(c, dict) and c.get("verified") is True
        and str(c.get("name") or "").casefold().strip() == name
        for c in candidates
    ))


def assess(item: dict, today: date | None = None) -> dict:
    today = today or date.today()
    issues = []
    buy = _positive(item.get("verified_unit_price"))
    buy_source = item.get("verified_unit_price_source")
    supplier_ok = _supplier(item)
    buy_currency = str(item.get("quote_currency") or "").upper().strip()
    expiry = _date(item.get("quote_valid_until"))
    if not buy or not _https(buy_source) or not supplier_ok or buy_currency not in CURRENCIES:
        issues.append("verified_supplier_quote")
    if expiry is None:
        issues.append("quote_valid_until")
    elif expiry < today:
        issues.append("quote_expired")

    sell = _positive(item.get("verified_selling_unit_price"))
    sell_source = item.get("verified_selling_price_source")
    sell_currency = str(item.get("selling_currency") or "").upper().strip()
    if not sell or not _https(sell_source) or sell_currency not in CURRENCIES:
        issues.append("verified_selling_quote")
    elif buy_currency and sell_currency != buy_currency:
        issues.append("currency_mismatch")

    qty = _positive(item.get("quantity") or item.get("requested_quantity") or item.get("qty"))
    if not qty:
        issues.append("quantity")

    price_ready = not any(x in issues for x in ("verified_supplier_quote", "quote_valid_until", "quote_expired"))
    margin_ready = price_ready and not any(x in issues for x in ("verified_selling_quote", "currency_mismatch", "quantity"))
    result = {
        "status": "margin_ready" if margin_ready else ("price_ready" if price_ready else "research_required"),
        "price_ready": price_ready,
        "margin_ready": margin_ready,
        "missing_or_invalid": issues,
        "quote_valid_until": expiry.isoformat() if expiry else None,
        "source_backed_only": True,
        "external_outreach_enabled": False,
        "human_review_required": True,
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
        next_agent = ("Price Agent" if "verified_supplier_quote" in result["missing_or_invalid"]
                      else "Quote Validity Agent" if any(x in result["missing_or_invalid"] for x in ("quote_valid_until", "quote_expired"))
                      else "Buyer Price Agent" if any(x in result["missing_or_invalid"] for x in ("verified_selling_quote", "currency_mismatch"))
                      else "Source Terms Agent")
        queue.append({
            "opportunity_id": item.get("id") or item.get("opportunity_id") or item.get("notice_id"),
            "product": item.get("product_name") or item.get("title_tr") or item.get("title_original"),
            "blockers": result["missing_or_invalid"],
            "next_agent": next_agent,
            "acceptance_criteria": [
                "supplier quote: verified supplier, positive numeric unit price, currency, HTTPS source",
                "supplier quote validity: explicit ISO date, not expired",
                "buyer selling quote: positive numeric unit price, currency, named buyer, HTTPS source",
                "matching currency and explicit quantity before gross spread",
                "never label gross spread as net profit; human approval before external contact",
            ],
            "priority": 100 + min(supplier_count, 3) * 10 - len(result["missing_or_invalid"]) * 5,
            "research_only": True,
            "external_outreach_enabled": False,
        })
    queue.sort(key=lambda x: (-x["priority"], str(x["opportunity_id"] or "")))
    payload["price_margin_summary"] = {
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
