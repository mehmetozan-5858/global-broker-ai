"""Evidence-aware opportunity freshness and source classification."""
from __future__ import annotations
from datetime import date, datetime
from urllib.parse import urlparse

OFFICIAL_SOURCES = {"TED", "WORLD_BANK", "SAM_GOV", "UNGM", "UNDP"}

def parse_deadline(raw):
    if isinstance(raw, (list, tuple)):
        dates = [d for v in raw if (d := parse_deadline(v)) is not None]
        return min(dates) if dates else None
    if isinstance(raw, dict):
        dates = [d for v in raw.values() if (d := parse_deadline(v)) is not None]
        return min(dates) if dates else None
    if not isinstance(raw, str) or not raw.strip():
        return None
    s = raw.strip()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    for fmt in ("%d/%m/%Y", "%d.%m.%Y", "%m/%d/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

def assess(item, today=None):
    today = today or date.today()
    raw = item.get("deadline-receipt-tender-date-lot") or item.get("deadline_date")
    deadline = parse_deadline(raw)
    if deadline is None:
        freshness = "deadline_unknown_review"
    elif deadline < today:
        freshness = "expired"
    else:
        freshness = "open_by_date_only"
    source = str(item.get("source") or "").upper()
    source_url = str(item.get("source_url") or "").strip()
    parsed = urlparse(source_url)
    has_link = parsed.scheme == "https" and bool(parsed.netloc)
    return {
        "freshness_status": freshness,
        "deadline_normalized": deadline.isoformat() if deadline else None,
        "source_type": "public_procurement_notice" if source in OFFICIAL_SOURCES else "source_type_unverified",
        "source_link_status": "present_unverified" if has_link else "missing_or_invalid",
        "private_buyer_mandate_verified": False,
        "buyer_due_diligence_status": "pending",
        "supplier_due_diligence_status": "pending",
        "pricing_evidence_status": "pending",
        "commission_agreement_status": "not_signed",
        "outreach_status": "shadow_not_sent",
        "human_review_required": True,
    }
