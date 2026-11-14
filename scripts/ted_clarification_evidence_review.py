"""Offline review of *candidate* official clarification evidence for TED 702997-2026.

This module cannot remove the quarantine or approve a supplier. A URL, SHA-256
and reviewer claim are merely intake metadata, not verification that the source
actually resolves the contradictory tank requirements.
"""
import hashlib
import json
import re
from pathlib import Path
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


MAX_SOURCE_BYTES = 12_000_000


def check_local_evidence_bytes(candidate, file_path):
    """Verify bounded local bytes against metadata, without trusting provenance.

    Does not fetch URLs, inspect official document semantics, or release holds.
    A hash match only authenticates consistency with a *user-declared* digest.
    """
    outcome = review_candidate(candidate)
    outcome["claimed_sha256_matches_local_bytes"] = False
    outcome["local_bytes_checked"] = False
    if not outcome["metadata_complete"]:
        return outcome
    try:
        path = Path(file_path)
        if not path.is_file() or path.is_symlink():
            raise ValueError("missing_or_symlink_file")
        size = path.stat().st_size
        if size < 1 or size > MAX_SOURCE_BYTES:
            raise ValueError("file_outside_size_bound")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            total = 0
            while chunk := stream.read(65536):
                total += len(chunk)
                if total > MAX_SOURCE_BYTES:
                    raise ValueError("file_outside_size_bound")
                digest.update(chunk)
        outcome["local_bytes_checked"] = True
        outcome["claimed_sha256_matches_local_bytes"] = (
            digest.hexdigest() == candidate["sha256"]
        )
        if not outcome["claimed_sha256_matches_local_bytes"]:
            outcome["errors"].append("claimed_sha256_does_not_match_file")
    except (OSError, ValueError, TypeError):
        outcome["errors"].append("local_file_missing_or_invalid")
    if outcome["errors"]:
        outcome["status"] = "INVALID_OR_INCOMPLETE"
    # Even a matching claim can be an invented pair of bytes and digest.
    return outcome


def check_official_manifest_record(candidate, manifest, private_directory):
    """Cross-check candidate local bytes against a bounded official-fetch manifest.

    This establishes evidence-chain consistency only if the manifest was
    genuinely produced by the official-host downloader; a supplied JSON file
    alone is not authenticated. It never verifies authoritative revisions.
    """
    result = review_candidate(candidate)
    result["manifest_source_record_match"] = False
    result["manifest_file_sha256_match"] = False
    if not result["metadata_complete"]:
        return result
    if not isinstance(manifest, dict) or any(
        manifest.get(key) != value
        for key, value in (
            ("notice", "702997-2026"),
            ("amendment", "746528-2026"),
            ("ezak_dbid", 47078),
            ("source_index", "https://zakazky.krajbezkorupce.cz/contract_display_47078.html"),
            ("revision_verified", False),
            ("complete_annex_set_verified", False),
        )
    ):
        result["errors"].append("incorrect_or_unbounded_manifest")
    records = manifest.get("records") if isinstance(manifest, dict) else None
    if not isinstance(records, list) or len(records) > 40:
        result["errors"].append("invalid_manifest_records")
        records = []
    matches = [
        row for row in records
        if isinstance(row, dict)
        and row.get("source_url") == candidate.get("official_url")
        and row.get("sha256") == candidate.get("sha256")
        and row.get("accepted") is False
        and isinstance(row.get("bytes"), int)
        and 0 < row["bytes"] <= MAX_SOURCE_BYTES
    ]
    if len(matches) != 1:
        result["errors"].append("unique_manifest_document_record_required")
    if not result["errors"]:
        filename = matches[0].get("file")
        if (not isinstance(filename, str) or
                not re.fullmatch(r"annex-[0-9]{3}-[a-f0-9]{16}\.(?:bin|pdf)", filename) or
                not filename.endswith((".bin", ".pdf"))):
            result["errors"].append("invalid_manifest_file_identity")
        else:
            path = Path(private_directory) / filename
            local = check_local_evidence_bytes(candidate, path)
            result["manifest_source_record_match"] = True
            if not local["claimed_sha256_matches_local_bytes"]:
                result["errors"].append("manifest_local_sha256_mismatch")
            elif not path.is_file() or path.is_symlink():
                result["errors"].append("manifest_local_file_invalid")
            elif path.stat().st_size != matches[0]["bytes"]:
                result["errors"].append("manifest_file_size_mismatch")
            else:
                result["manifest_file_sha256_match"] = True
    if result["errors"]:
        result["status"] = "INVALID_OR_INCOMPLETE"
    # A manifest and downloaded bytes are still not proof that the document
    # supersedes the 27 October technical specification.
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) not in (2, 3):
        raise SystemExit("Usage: python -m scripts.ted_clarification_evidence_review <candidate.json> [local-source-file]")
    record = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result = check_local_evidence_bytes(record, sys.argv[2]) if len(sys.argv) == 3 else review_candidate(record)
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(2)  # Always stay in manual-review state
