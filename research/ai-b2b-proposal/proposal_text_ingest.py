"""Offline text document ingestion with externally pinned digest and scope.

Research-only: no PDF/OCR, no remote fetching, no authenticity assertion.
Trusted manifest must be provided outside the untrusted document/model output.
"""
import hashlib
import re
from proposal_source_gate import sha256_text

MAX_BYTES = 1024 * 1024
MAX_LINES = 10000
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")


class IngestionRejected(ValueError):
    """Source unavailable or rejected; never treat as positive evidence."""


def ingest_pinned_text(raw_bytes, *, source_id, trusted_manifest):
    """Return (trusted_snapshot, source_records); caller must keep manifest independent.

    Required manifest fields: source_id, sha256_raw, company, region.
    Snapshot authenticity is NOT verified; only raw bytes + line integrity.
    """
    if not isinstance(raw_bytes, bytes) or not raw_bytes or len(raw_bytes) > MAX_BYTES:
        raise IngestionRejected("INPUT_BYTES_INVALID")
    if not isinstance(trusted_manifest, dict):
        raise IngestionRejected("MANIFEST_MISSING")
    if not isinstance(source_id, str) or not _IDENTIFIER.fullmatch(source_id):
        raise IngestionRejected("SOURCE_ID_INVALID")
    if trusted_manifest.get("source_id") != source_id:
        raise IngestionRejected("SOURCE_ID_MISMATCH")
    expected = trusted_manifest.get("sha256_raw")
    if not isinstance(expected, str) or not _SHA256.fullmatch(expected):
        raise IngestionRejected("EXPECTED_HASH_INVALID")
    actual = hashlib.sha256(raw_bytes).hexdigest()
    if actual != expected:
        raise IngestionRejected("RAW_HASH_MISMATCH")
    company = trusted_manifest.get("company")
    region = trusted_manifest.get("region")
    if not isinstance(company, str) or not company.strip():
        raise IngestionRejected("MANIFEST_COMPANY_MISSING")
    if not isinstance(region, str) or not region.strip():
        raise IngestionRejected("MANIFEST_REGION_MISSING")
    try:
        text = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise IngestionRejected("ENCODING_INVALID") from exc
    if raw_bytes.startswith(b"%PDF-"):
        raise IngestionRejected("UNSUPPORTED_DOCUMENT_TYPE")
    if text.startswith("\ufeff") or "\r" in text or any((ord(ch) < 32 and ch not in "\n\t") or ord(ch) == 127 for ch in text):
        raise IngestionRejected("UNSUPPORTED_TEXT_FORMAT")
    physical_lines = text.split("\n")
    if physical_lines and physical_lines[-1] == "":
        physical_lines.pop()
    if not physical_lines or len(physical_lines) > MAX_LINES:
        raise IngestionRejected("LINE_COUNT_INVALID")
    if not any(item.strip() for item in physical_lines):
        raise IngestionRejected("DOCUMENT_EMPTY")
    lines = {"L" + str(i): line for i, line in enumerate(physical_lines, start=1)}
    canonical = "".join(key + "\t" + lines[key] + "\n" for key in sorted(lines))
    snapshot = {
        "company": company,
        "region": region,
        "lines": lines,
        "sha256": sha256_text(canonical),
        "sha256_raw": actual,
        "ingestion_format": "text/plain; charset=utf-8",
        "real_world_authenticity_verified": False,
    }
    records = [
        {"source_id": source_id, "line": "L" + str(i), "text": line,
         "company": company, "region": region}
        for i, line in enumerate(physical_lines, start=1)
        if line.strip()
    ]
    return {source_id: snapshot}, records


def reject_pdf_or_unpinned(raw_bytes):
    """PDF must go through a separately reviewed page-aware parser."""
    raise IngestionRejected("PDF_NOT_SUPPORTED_NO_SOURCE_CITATIONS")
