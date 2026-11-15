"""Offline PDF text-page ingestion, research-only, not a PDF authenticity check.

Only accepts pinned bytes of text-extractable, image-free PDFs. No OCR.
Independent manifest custody is required; PDF text alone proves nothing.
"""
import hashlib
import io
import re
from proposal_source_gate import sha256_text
from proposal_text_ingest import IngestionRejected

MAX_PDF_BYTES = 2 * 1024 * 1024
MAX_PAGES = 20
MAX_LINES = 10000
_ID = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def ingest_pinned_pdf(raw_bytes, *, source_id, trusted_manifest):
    if not isinstance(raw_bytes, bytes) or not raw_bytes or len(raw_bytes) > MAX_PDF_BYTES:
        raise IngestionRejected("PDF_INPUT_INVALID")
    if not raw_bytes.startswith(b"%PDF-"):
        raise IngestionRejected("PDF_HEADER_INVALID")
    if not isinstance(source_id, str) or not _ID.fullmatch(source_id):
        raise IngestionRejected("PDF_SOURCE_ID_INVALID")
    if not isinstance(trusted_manifest, dict) or trusted_manifest.get("source_id") != source_id:
        raise IngestionRejected("PDF_MANIFEST_MISSING_OR_SCOPE")
    pinned = trusted_manifest.get("sha256_raw")
    if not isinstance(pinned, str) or not _DIGEST.fullmatch(pinned):
        raise IngestionRejected("PDF_EXPECTED_HASH_INVALID")
    actual = hashlib.sha256(raw_bytes).hexdigest()
    if actual != pinned:
        raise IngestionRejected("PDF_RAW_HASH_MISMATCH")
    company, region = trusted_manifest.get("company"), trusted_manifest.get("region")
    if not isinstance(company, str) or not company.strip():
        raise IngestionRejected("PDF_COMPANY_MISSING")
    if not isinstance(region, str) or not region.strip():
        raise IngestionRejected("PDF_REGION_MISSING")
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise IngestionRejected("PDF_PARSER_UNAVAILABLE") from exc
    try:
        reader = PdfReader(io.BytesIO(raw_bytes), strict=True)
        if reader.is_encrypted:
            raise IngestionRejected("PDF_ENCRYPTED")
        count = len(reader.pages)
        if not 1 <= count <= MAX_PAGES:
            raise IngestionRejected("PDF_PAGE_COUNT_INVALID")
        lines = {}
        records = []
        for number, page in enumerate(reader.pages, start=1):
            # A PDF may contain pictures carrying claims invisible to text extraction.
            if len(page.images) > 0:
                raise IngestionRejected("PDF_PAGE_IMAGES_REQUIRE_REVIEW")
            text = page.extract_text(extraction_mode="plain")
            if not isinstance(text, str) or not text.strip():
                raise IngestionRejected("PDF_PAGE_TEXT_MISSING")
            if any((ord(ch) < 32 and ch not in "\n\t") or ord(ch) == 127 for ch in text):
                raise IngestionRejected("PDF_TEXT_CONTROL_CHARACTER")
            for index, line in enumerate(text.splitlines(), start=1):
                label = f"P{number}-L{index}"
                lines[label] = line
                if line.strip():
                    records.append({"source_id": source_id, "line": label, "page": number,
                                    "text": line, "company": company, "region": region})
                if len(lines) > MAX_LINES:
                    raise IngestionRejected("PDF_LINE_COUNT_EXCEEDED")
        if not records:
            raise IngestionRejected("PDF_TEXT_MISSING")
    except IngestionRejected:
        raise
    except Exception as exc:
        raise IngestionRejected("PDF_PARSE_FAILED") from exc
    canonical = "".join(key + "\t" + lines[key] + "\n" for key in sorted(lines))
    return {source_id: {
        "company": company, "region": region, "lines": lines,
        "sha256": sha256_text(canonical), "sha256_raw": actual,
        "page_count": count, "ingestion_format": "application/pdf",
        "real_world_authenticity_verified": False,
        "visual_content_verified": False,
    }}, records
