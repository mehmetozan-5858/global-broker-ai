"""Server-side preflight: do not spend introduction credits on incomplete dossiers.

This is a conservative gate before the Supabase request_introduction RPC.
It does not replace the RPC's entitlement checks, verification or refund logic.
"""
import json
import re
from pathlib import Path

from src.public_opportunity_projection import project_public_opportunity

_GENERIC_PRODUCTS = re.compile(
    r"^(?:araç (?:yedek )?parça(?:sı|ları)?|otomotiv (?:yedek )?parça(?:sı|ları)?|"
    r"medikal ürün(?: alımı)?|metal / maden ürünü(?: alımı)?|"
    r"yedek parça(?: alımı)?|ürün alımı|satın alma talebi)$",
    re.IGNORECASE,
)
_UNKNOWN = ("henüz netleşmedi", "bilinmiyor", "belirtilmemiş")


def missing_dossier_fields(item):
    product = str(item.get("product_name") or "").strip()
    missing = []
    if not product or _GENERIC_PRODUCTS.fullmatch(product) or any(word in product.lower() for word in _UNKNOWN):
        missing.append("product_name")
    if not item.get("approx_quantity"):
        missing.append("approx_quantity")
    if not item.get("deadline"):
        missing.append("deadline")
    if not (item.get("country") or item.get("country_code")):
        missing.append("country")
    if not (item.get("source_name") or item.get("source_type")):
        missing.append("source")
    return missing


def _feed_path():
    here = Path(__file__).resolve()
    for candidate in (
        here.parent.parent / "data" / "latest-opportunities.json",
        Path.cwd() / "data" / "latest-opportunities.json",
        Path("/var/task/data/latest-opportunities.json"),
    ):
        if candidate.is_file():
            return candidate
    return None


def introduction_preflight(opportunity_id):
    """Return (HTTP status, public error code) or (200, 'OK').

    Fail closed if feed unavailable. Never include private row data in errors.
    """
    path = _feed_path()
    if path is None:
        return 503, "OPPORTUNITY_FEED_UNAVAILABLE"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data.get("opportunities") or []
        for row in rows:
            if not isinstance(row, dict):
                continue
            review = row.get("export_goods_review")
            if not isinstance(review, dict) or review.get("status") != "goods_candidate":
                continue
            projected = project_public_opportunity(row)
            if projected["opportunity_id"] != opportunity_id:
                continue
            if missing_dossier_fields(projected):
                return 409, "OPPORTUNITY_DOSSIER_INCOMPLETE"
            return 200, "OK"
    except (OSError, ValueError, TypeError, KeyError):
        return 503, "OPPORTUNITY_FEED_UNAVAILABLE"
    return 404, "OPPORTUNITY_NOT_FOUND"
