"""Explicit review-only risk quarantine for the *specific* unresolved TED case.

An exact, isolated reference check avoids applying this tender's problems to
other opportunities. Do not treat it as global source freshness monitoring.
Changes to a future authoritative revision require reviewed source evidence.
"""
from __future__ import annotations

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


def is_quarantined_ted(item: dict) -> bool:
    """Exact identifier only: never substring-match or copy risk to other TEDs."""
    return bool(_exact_identifiers(item) & PUBLICATIONS)


def tender_specific_blockers(item: dict) -> list[str]:
    return list(REASONS) if is_quarantined_ted(item) else []
