"""Explicit review-only risk quarantine for the *specific* unresolved TED case.

An exact, isolated reference check avoids applying this tender's problems to
other opportunities. Do not treat it as global source freshness monitoring.
Changes to a future authoritative revision require reviewed source evidence.
"""
from __future__ import annotations
from urllib.parse import urlsplit

PUBLICATIONS = frozenset({"702997-2026", "746528-2026"})
REASONS = (
    "ted_702997_unresolved_drawing_capacity",
    "ted_702997_unresolved_specification_geometry",
    "ted_702997_authoritative_clarification_pending",
)


def _exact_identifiers(item: dict) -> set[str]:
    names = ("publication-number", "publication_number", "notice_id", "id", "opportunity_id")
    values = set()
    for field in names:
        value = item.get(field)
        if isinstance(value, str) and value.strip():
            values.add(value.strip())
        elif isinstance(value, list):
            values.update(v.strip() for v in value if isinstance(v, str) and v.strip())
    return values


def _exact_official_ted_urls(item: dict) -> set[str]:
    """Read only trusted, exact TED notice URL shapes; never match arbitrary text."""
    values = []
    for field in ("source_url", "notice_url", "official_links"):
        value = item.get(field)
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, list):
            values.extend(v for v in value if isinstance(v, str))
    found = set()
    for value in values:
        try:
            url = urlsplit(value.strip())
        except ValueError:
            continue
        if (
            url.scheme != "https"
            or url.hostname != "ted.europa.eu"
            or url.username is not None
            or url.password is not None
            or url.netloc.lower() not in ('ted.europa.eu', 'ted.europa.eu:443')
            or url.query
            or url.fragment
        ):
            continue
        for locale in ("en", "cs"):
            prefix = f"/{locale}/notice/-/detail/"
            if url.path.startswith(prefix):
                suffix = url.path[len(prefix):]
                if suffix in PUBLICATIONS:
                    found.add(suffix)
    return found


def is_quarantined_ted(item: dict) -> bool:
    """Exact identifier only: never substring-match or copy risk to other TEDs."""
    return bool((_exact_identifiers(item) | _exact_official_ted_urls(item)) & PUBLICATIONS)



def deadline_revision_review(item: dict) -> dict | None:
    """Internal warning; never overwrite the deadline shown by TED ingestion.

    The amended notice has been published with a 2026-11-27 date, while
    historical mirrors of the original show 2026-11-11. This check is a
    provenance discrepancy signal, NOT authoritative present validity.
    """
    if not is_quarantined_ted(item):
        return None
    names = ("deadline-receipt-tender-date-lot", "deadline", "submission_deadline")
    observed = set()
    for name in names:
        value = item.get(name)
        samples = value if isinstance(value, list) else [value]
        for sample in samples:
            if isinstance(sample, str):
                date_part = sample.strip()[:10]
                if date_part in {"2026-11-11", "2026-11-27"}:
                    observed.add(date_part)
    return {
        "amendment_notice": "746528-2026",
        "amendment_published_deadline_date": "2026-11-27",
        "old_original_deadline_present": "2026-11-11" in observed,
        "incoming_deadline_dates": sorted(observed),
        "live_deadline_authoritatively_verified": False,
        "automatic_deadline_replacement": False,
        "offer_submission_authorized": False,
    }


def tender_specific_blockers(item: dict) -> list[str]:
    return list(REASONS) if is_quarantined_ted(item) else []
