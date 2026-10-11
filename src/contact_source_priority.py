from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

CONTACT_HINT = re.compile(
    r"(?i)\b(contact|procurement|purchasing|tender|vendor|supplier|buyer|email|phone|telephone|iletişim|irtibat|satın alma|ihale|tedarik)\b"
)

SOURCE_WEIGHTS = {
    "sam.gov": 95,
    "ted": 90,
    "monaqasat": 80,
    "etimad": 75,
    "ggzy": 65,
    "world_bank": 55,
}


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return " ".join(_text(x) for x in value if _text(x))
    if isinstance(value, dict):
        return " ".join(_text(x) for x in value.values() if _text(x))
    return str(value).strip()


def _source_url(row: dict[str, Any]) -> str:
    for key in ("source_url", "notice_url", "detail_url", "official_url", "url", "document_url"):
        value = str(row.get(key) or "").strip()
        if value.startswith("https://"):
            return value
    links = row.get("official_links")
    if isinstance(links, list):
        for value in links:
            value = str(value or "").strip()
            if value.startswith("https://"):
                return value
    return ""


def source_family(row: dict[str, Any]) -> str:
    source = _text(row.get("source") or row.get("source_name")).lower()
    url = _source_url(row)
    host = (urlparse(url).hostname or "").lower() if url else ""
    joined = f"{source} {host}"
    if "sam.gov" in joined or "sam_gov" in joined:
        return "sam.gov"
    if "ted" in joined or "ted.europa.eu" in joined:
        return "ted"
    if "monaqasat" in joined:
        return "monaqasat"
    if "etimad" in joined:
        return "etimad"
    if "ggzy" in joined:
        return "ggzy"
    if "world_bank" in joined or "world bank" in joined:
        return "world_bank"
    return host or source or "unknown"


def score_row(row: dict[str, Any]) -> tuple[int, list[str]]:
    reasons: list[str] = []
    family = source_family(row)
    score = SOURCE_WEIGHTS.get(family, 40)
    reasons.append(f"source:{family}")

    url = _source_url(row)
    if url:
        score += 20
        reasons.append("official_url")

    buyer = _text(
        row.get("buyer-name")
        or row.get("buyer_name")
        or row.get("organization_name")
        or row.get("contracting_authority")
        or row.get("agency")
        or ((row.get("field_evidence") or {}).get("buyer") or {}).get("value")
    )
    if buyer:
        score += 20
        reasons.append("buyer_identified")

    doc = _text(row.get("document_extracted_text"))
    if doc:
        score += 15
        reasons.append("source_document_text")
        if CONTACT_HINT.search(doc):
            score += 25
            reasons.append("contact_terms_in_source")

    if row.get("buyer_verified"):
        score += 10
        reasons.append("buyer_verified")

    probe = row.get("contact_probe")
    if isinstance(probe, dict) and probe.get("status") == "checked_no_direct_contact":
        score -= 30
        reasons.append("prior_probe_no_contact")

    if row.get("direct_contact_available") or row.get("contact_email") or row.get("contact_phone"):
        score = 1000
        reasons.append("already_direct")

    return max(0, min(1000, score)), reasons


def prioritize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("opportunities")
    if not isinstance(rows, list):
        return payload

    families: dict[str, int] = {}
    scored = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        score, reasons = score_row(row)
        family = source_family(row)
        families[family] = families.get(family, 0) + 1
        row["contact_discovery_priority"] = score
        row["contact_discovery_reason"] = reasons
        row["contact_source_family"] = family
        scored += 1

    payload["contact_source_priority_summary"] = {
        "version": 1,
        "mode": "source_backed_priority_no_hallucination",
        "scored": scored,
        "source_families": families,
    }
    return payload


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.contact_source_priority <json-file>")
    path = Path(sys.argv[1])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload = prioritize_payload(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
