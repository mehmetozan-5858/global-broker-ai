"""Strict public projection for Global Broker opportunities.

Public/customer-facing payloads are built from an explicit allowlist. Unknown or
new private fields are dropped by default.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from src.opportunity_identity import stable_opportunity_id
from src.introduction_readiness import missing_dossier_fields

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

    candidates = {
        "product_name": _evidence_value(row, "product") or _pick(row, ("product_name", "product", "title_tr", "title_original", "notice-title", "title")),
        "country": _evidence_value(row, "country") or _pick(row, ("buyer-country", "country_name", "project_ctry_name", "country", "country_code")),
        "country_code": _pick(row, ("country_code", "buyer_country_code")),
        "approx_quantity": _evidence_value(row, "quantity") or _pick(row, ("quantity-lot", "quantity", "requested_quantity", "qty")),
        "deadline": _evidence_value(row, "deadline") or _pick(row, ("deadline-receipt-tender-date-lot", "responseDeadLine", "deadline_date", "submission_deadline_date", "deadline", "closing_date")),
        "delivery_term": _pick(row, ("incoterm", "delivery_term", "delivery_terms", "delivery_condition")),
        "opportunity_type": _pick(row, ("opportunity_type", "notice_type", "procurement_method", "type")),
        "verification_category": _pick(row, ("verification_category", "verification_status")) or _scalar(verification.get("status")),
        "source_type": _pick(row, ("source_type", "portal_family")),
        "source_name": _pick(row, ("source", "source_name")),
        "goods_status": _scalar(review.get("status")),
        "published_at": _pick(row, ("published_at", "publication_date", "date", "created_at")),
        "status": _pick(row, ("status", "opportunity_status")),
    }
    for key, value in candidates.items():
        if value is not None:
            result[key] = value

    verified_count = coverage.get("verified_or_source_backed")
    total_count = coverage.get("total")
    if isinstance(verified_count, int) and verified_count >= 0:
        result["source_backed_fields"] = verified_count
    if isinstance(total_count, int) and total_count > 0:
        result["source_field_total"] = total_count
    # Apply the same readiness policy to every future incoming opportunity,
    # regardless of source, company, region, sector or feed size.
    missing = missing_dossier_fields(result)
    result["dossier_status"] = "research_required" if missing else "ready_for_review"
    result["missing_dossier_fields"] = missing
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
