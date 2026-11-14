"""Offline review of *candidate* official clarification evidence for TED 702997-2026.

This module cannot remove the quarantine or approve a supplier. A URL, SHA-256
and reviewer claim are merely intake metadata, not verification that the source
actually resolves the contradictory tank requirements.
"""
import json
import re
from urllib.parse import urlsplit

TARGETS = ("Slavkov u Brna", "Veselí nad Moravou")
ALLOWED_HOSTS = frozenset(("zakazky.krajbezkorupce.cz", "ted.europa.eu"))
EXPECTED_NOTICES = frozenset(("702997-2026", "746528-2026"))
SHA256 = re.compile(r"^[a-f0-9]{64}$")
ISO_DATE = re.compile(r"^20[0-9]{2}-[01][0-9]-[0-3][0-9]$")
DIMENSIONS = ("minimum_volume_l", "maximum_diameter_mm", "maximum_height_mm")


def _official_https(url):
    if not isinstance(url, str) or len(url) > 1000:
        return False
    try:
        parsed = urlsplit(url)
        return (
            parsed.scheme == "https"
            and parsed.hostname in ALLOWED_HOSTS
            and parsed.netloc.lower() in ALLOWED_HOSTS
            and parsed.username is None
            and parsed.password is None
            and bool(parsed.path)
            and not parsed.query and not parsed.fragment
        )
    except ValueError:
        return False


def review_candidate(candidate):
    errors = []
    if not isinstance(candidate, dict):
        candidate = {}
        errors.append("invalid_evidence_record")
    if candidate.get("notice") not in EXPECTED_NOTICES:
        errors.append("wrong_notice")
    if candidate.get("site") not in TARGETS:
        errors.append("out_of_scope_site")
    if not _official_https(candidate.get("official_url")):
        errors.append("official_https_document_url_required")
    digest = candidate.get("sha256")
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        errors.append("content_sha256_required")
    issue_date = candidate.get("official_publication_date")
    if not isinstance(issue_date, str) or not ISO_DATE.fullmatch(issue_date):
        errors.append("official_publication_date_required")
    reviewer = candidate.get("reviewer")
    if not isinstance(reviewer, str) or not (3 <= len(reviewer.strip()) <= 120):
        errors.append("named_independent_reviewer_required")
    dimensions = candidate.get("corrected_requirements")
    if not isinstance(dimensions, dict) or any(
        type(dimensions.get(key)) is not int or dimensions[key] <= 0
        for key in DIMENSIONS
    ):
        errors.append("complete_corrected_dimensions_required")
    # A structurally complete metadata record is only reviewable, never a
    # verified authoritative publication or engineering approval.
    return {
        "status": "NEEDS_INDEPENDENT_SOURCE_REVIEW" if not errors else "INVALID_OR_INCOMPLETE",
        "metadata_complete": not errors,
        "errors": errors,
        "source_content_verified": False,
        "authoritative_revision_verified": False,
        "capacity_conflict_resolved": False,
        "technical_approval": False,
        "commercial_approval": False,
        "quarantine_release_authorized": False,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m scripts.ted_clarification_evidence_review <candidate.json>")
    from pathlib import Path
    record = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(json.dumps(review_candidate(record), sort_keys=True))
    raise SystemExit(2)  # Always stay in manual-review state
