"""Bounded TED Search facts; arrays never establish associations between lots."""
from __future__ import annotations
import re
from datetime import date
from decimal import Decimal, InvalidOperation

def _values(value):
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        return [str(value).strip()] if str(value).strip() else []
    if isinstance(value, list):
        return list(dict.fromkeys(x for v in value for x in _values(v)))
    return []

def _one(value):
    values = _values(value)
    return values[0] if len(values) == 1 else None

def _positive(value):
    try:
        return value is not None and Decimal(value).is_finite() and Decimal(value) > 0
    except (InvalidOperation, ValueError):
        return False

def notice_context(item):
    if item.get("source") != "TED":
        return None
    form = _one(item.get("form-type"))
    labels = {
        "competition": "İhale çağrısı — son tarih ayrıca doğrulanmalı",
        "result": "Sonuç ilanı — yeni alım çağrısı değil",
        "completion": "Tamamlanmış sözleşme bildirimi",
        "cont-modif": "Sözleşme değişikliği — yeni alım çağrısı değil",
        "planning": "Ön bilgi / planlama — başvuru çağrısı değil",
        "consultation": "Pazar istişaresi — ihale çağrısı değil",
        "dir-awa-pre": "Doğrudan alım ön bildirimi — açık ihale çağrısı değil",
        "bri": "İşletme kaydı — alım çağrısı değil",
    }
    if form not in labels:
        form = "unknown"
    return {"form_type": form, "call_for_tenders": form == "competition",
            "research_only": form != "competition",
            "label_tr": labels.get(form, "İlan türü doğrulanmalı — araştırma kaydı")}

def apply_search_fields(item):
    publication = _one(item.get("publication-number"))
    if item.get("source") != "TED" or not publication or not re.fullmatch(r"[0-9]{1,8}-[0-9]{4}", publication):
        return item
    source = "https://ted.europa.eu/en/notice/-/detail/" + publication
    item.setdefault("source_url", source)
    item["notice_context"] = notice_context(item)
    ids = _values(item.get("identifier-lot"))
    if any(not re.fullmatch(r"LOT-[A-Za-z0-9_-]+", v) for v in ids):
        item["ted_lot_selection_required"] = True
        return item
    if ids:
        item["ted_search_lot_ids"] = ids
        item["ted_lot_count"] = len(ids)
        item["ted_lot_selection_required"] = len(ids) > 1
    # Multiple or unidentified lots cannot be joined by position or equal values.
    if len(ids) != 1:
        item["ted_lot_selection_required"] = True
        return item
    raw_deadline = _one(item.get("deadline-receipt-tender-date-lot"))
    if raw_deadline and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}Z?", raw_deadline):
        try:
            deadline = date.fromisoformat(raw_deadline.rstrip("Z")).isoformat()
        except ValueError:
            pass
        else:
            item["deadline-receipt-tender-date-lot"] = deadline
    amount = _one(item.get("estimated-value-lot"))
    currency = _one(item.get("estimated-value-cur-lot"))
    if not _positive(amount) or not currency or not re.fullmatch(r"[A-Z]{3}", currency):
        return item
    if item.get("estimated_value") not in (None, "", [], {}) or item.get("budget_currency") not in (None, "", currency):
        return item
    item["estimated_value"] = amount
    item["budget_currency"] = currency
    item.setdefault("structured_source_evidence", {})["estimated_value"] = {
        "value": amount, "currency": currency, "source_url": source,
        "source_path": "ted_search.estimated-value-lot",
        "lot_id": ids[0], "inferred": False,
    }
    return item
