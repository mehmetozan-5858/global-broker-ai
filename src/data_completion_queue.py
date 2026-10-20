from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlsplit

from .opportunity_identity import stable_opportunity_id


_BAD_TEXT = (
    "bekleniyor",
    "bilinmiyor",
    "unknown",
    "pending",
    "ayrıştırılmadı",
    "çıkarılmadı",
    "not started",
    "n/a",
    "tbd",
    "kontrollü tanıştırma",
)


def _text(value: Any) -> str:
    if value is None or isinstance(value, (bool, dict)):
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join(_text(x) for x in value if x is not None).strip()
    return str(value).strip()


def _known(value: Any) -> bool:
    text = _text(value).lower()
    return bool(text) and not any(bad in text for bad in _BAD_TEXT)


def _pick(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = row.get(key)
        if _known(value):
            return value
    return None


def _official_source(row: dict[str, Any]) -> str | None:
    for key in (
        "source_url",
        "source-url",
        "notice_url",
        "detail_url",
        "document_url",
        "official_url",
        "tender_url",
        "url",
    ):
        value = row.get(key)
        if isinstance(value, str):
            try:
                parsed = urlsplit(value)
                if parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password:
                    return value
            except ValueError:
                pass
    return None


def _buyer(row: dict[str, Any]) -> Any:
    return _pick(
        row,
        (
            "buyer-name",
            "buyer_name",
            "contracting_authority",
            "organization_name",
            "agency",
            "borrower",
        ),
    )


def _product(row: dict[str, Any]) -> Any:
    field = row.get("field_evidence") or {}
    evidence = field.get("product") or {}
    if evidence.get("status") == "source_backed" and evidence.get("inferred") is not True and _known(evidence.get("value")):
        return evidence.get("value")
    return _pick(
        row,
        (
            "product",
            "product_name",
            "product_category",
            "cpv_description",
            "title_tr",
            "title_original",
            "notice-title",
            "title",
            "bid_description",
        ),
    )


def _quantity_or_budget(row: dict[str, Any]) -> Any:
    if row.get("source") == "TED":
        quantity = _pick(row, ("quantity-lot", "quantity", "requested_quantity", "qty", "contract_quantity", "estimated_quantity", "volume"))
        if quantity is not None:
            return quantity
        source = row.get("structured_source_evidence") or {}
        fact = source.get("estimated_value") if isinstance(source, dict) else None
        if not isinstance(fact, dict) or fact.get("inferred") is not False:
            return None
        value, currency = row.get("estimated_value"), row.get("budget_currency")
        try:
            valid = not isinstance(value, bool) and Decimal(str(value)).is_finite() and Decimal(str(value)) > 0
        except (InvalidOperation, ValueError):
            valid = False
        if valid and str(value) == str(fact.get("value")) and currency == fact.get("currency") and isinstance(currency, str) and len(currency) == 3 and currency.isupper() and currency.isalpha():
            return value
        return None
    return _pick(
        row,
        (
            "quantity-lot",
            "quantity",
            "requested_quantity",
            "qty",
            "contract_quantity",
            "estimated_quantity",
            "volume",
            "estimated-value-lot",
            "estimated_value",
            "budget",
            "amount",
            "value",
        ),
    )


def _deadline(row: dict[str, Any]) -> Any:
    return _pick(
        row,
        (
            "deadline-receipt-tender-date-lot",
            "submission_deadline_date",
            "deadline_date",
            "deadline",
            "responseDeadLine",
            "closing_date",
        ),
    )


def _country(row: dict[str, Any]) -> Any:
    return _pick(
        row,
        (
            "buyer-country",
            "buyer_country",
            "project_ctry_name",
            "country_name",
            "country",
            "country_code",
            "project_ctry_code",
            "buyer_country_code",
        ),
    )


def _missing(row: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if row.get("ted_lot_selection_required") is True:
        missing.append("lot_selection")
    if not _known(_buyer(row)):
        missing.append("buyer_identity")
    if not _known(_product(row)):
        missing.append("product")
    quantity = _quantity_or_budget(row)
    if not _known(quantity) or (isinstance(quantity, (int, float)) and quantity <= 0) or _text(quantity) in {"0", "0.0"}:
        missing.append("quantity_or_budget")
    if not _known(_deadline(row)):
        missing.append("deadline")
    if not _known(_country(row)):
        missing.append("country")
    if not _official_source(row):
        missing.append("official_source")
    return missing


def _next_agent(missing: list[str]) -> str:
    order = (
        ("lot_selection", "specification_agent"),
        ("official_source", "source_research_agent"),
        ("buyer_identity", "buyer_research_agent"),
        ("product", "specification_agent"),
        ("quantity_or_budget", "source_terms_agent"),
        ("deadline", "source_terms_agent"),
        ("country", "source_research_agent"),
    )
    for key, agent in order:
        if key in missing:
            return agent
    return "commercial_research_agent"


def _priority(row: dict[str, Any], missing: list[str]) -> int:
    # This is queue priority only, not a probability, deal score or profit claim.
    score = 100 - 12 * len(missing)
    if _official_source(row):
        score += 15
    if row.get("buyer_verified") is True:
        score += 15
    supplier = row.get("supplier_research") or {}
    if int(supplier.get("verified_supplier_count") or 0) > 0:
        score += 20
    return max(0, score)


def build(payload: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in (payload.get("opportunities") or []) if isinstance(row, dict)]
    counts: Counter[str] = Counter()
    queue: list[dict[str, Any]] = []
    complete = 0

    for row in rows:
        missing = _missing(row)
        row["data_completion"] = {"core_complete": not missing, "missing_fields": missing, "source_backed_only": True}
        counts.update(missing)
        if not missing:
            complete += 1
            continue
        queue.append(
            {
                "opportunity_id": row.get("opportunity_id")
                or row.get("id")
                or row.get("publication-number")
                or row.get("notice_id")
                or stable_opportunity_id(row),
                "product": _product(row),
                "country": _country(row),
                "missing_core_fields": missing,
                "missing_count": len(missing),
                "priority_score": _priority(row, missing),
                "next_agent": _next_agent(missing),
                "research_only": True,
                "human_approval_required": True,
            }
        )

    queue.sort(
        key=lambda item: (
            -int(item["priority_score"]),
            int(item["missing_count"]),
            str(item.get("product") or ""),
        )
    )

    result = {
        "opportunities_reviewed": len(rows),
        "core_complete": complete,
        "core_incomplete": len(rows) - complete,
        "completion_rate_pct": round((complete / len(rows) * 100), 1) if rows else 0.0,
        "missing_field_counts": dict(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))),
        "queue_count": len(queue),
        "queue": queue[:100],
        "queue_truncated": len(queue) > 100,
        "queue_rule": "Official-source and near-complete opportunities are filled first; no missing facts are fabricated.",
    }
    payload["data_completion_queue"] = result
    return result
