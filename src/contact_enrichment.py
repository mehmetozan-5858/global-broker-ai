from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

EMAIL_RE = re.compile(r"(?i)(?<![A-Z0-9._%+-])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})(?![A-Z0-9._%+-])")
PHONE_RE = re.compile(r"(?<!\d)(\+?\d[\d\s()./-]{7,}\d)(?!\d)")
URL_RE = re.compile(r"https://[^\s\]\[()\"'<>]+", re.I)
CONTACT_HINT_RE = re.compile(
    r"(?i)\b(contact|contact person|procurement|purchasing|tender|bid|commercial|sales|buyer|telephone|phone|email|e-mail|iletişim|irtibat|satın alma|ihale|tedarik)\b"
)

TEXT_KEYS = (
    "document_extracted_text",
    "source_excerpt",
    "notice_text",
    "description",
    "detail_original",
    "description-lot",
    "bid_description",
    "technical-specification",
    "detail_tr",
    "demand_summary_tr",
)
DIRECT_EMAIL_KEYS = ("contact_email", "buyer_email", "email_address", "email", "e-mail")
DIRECT_PHONE_KEYS = ("contact_phone", "buyer_phone", "phone_number", "phone", "telephone", "mobile")
DIRECT_PERSON_KEYS = ("contact_person", "representative", "contact_name", "contact-name")
WEBSITE_KEYS = ("buyer_website", "organization_url", "website", "buyer-touchpoint-internet-address")
SOURCE_URL_KEYS = ("source_url", "source-url", "notice_url", "detail_url", "official_url", "url", "document_url")


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "\n".join(_text(x) for x in value if _text(x))
    if isinstance(value, dict):
        return "\n".join(_text(x) for x in value.values() if _text(x))
    return str(value).strip()


def _first(item: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = _text(item.get(key))
        if value:
            return value
    return ""


def _clean_phone(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" .,-/()")
    digits = re.sub(r"\D", "", value)
    if len(digits) < 8 or len(digits) > 16:
        return ""
    return value


def _https_url(value: str) -> str:
    value = value.strip().rstrip(".,;)")
    return value if value.lower().startswith("https://") else ""


def _context_window(text: str, start: int, end: int, radius: int = 180) -> str:
    return text[max(0, start - radius): min(len(text), end + radius)]


def _extract_contextual(text: str) -> tuple[str, str, str]:
    email = ""
    phone = ""
    evidence = ""
    for match in EMAIL_RE.finditer(text):
        window = _context_window(text, match.start(), match.end())
        if CONTACT_HINT_RE.search(window):
            email = match.group(1).strip().lower()
            evidence = window.strip()[:500]
            break
    for match in PHONE_RE.finditer(text):
        candidate = _clean_phone(match.group(1))
        if not candidate:
            continue
        window = _context_window(text, match.start(), match.end())
        if CONTACT_HINT_RE.search(window):
            phone = candidate
            if not evidence:
                evidence = window.strip()[:500]
            break
    return email, phone, evidence


def enrich_opportunity(item: dict[str, Any]) -> dict[str, Any]:
    email = _first(item, DIRECT_EMAIL_KEYS).lower()
    phone = _clean_phone(_first(item, DIRECT_PHONE_KEYS))
    contact_person = _first(item, DIRECT_PERSON_KEYS)
    website = _https_url(_first(item, WEBSITE_KEYS))
    source_url = _https_url(_first(item, SOURCE_URL_KEYS))
    evidence_source = "structured_source_field" if (email or phone or contact_person or website) else ""
    evidence_excerpt = ""

    if not email or not phone:
        for key in TEXT_KEYS:
            raw = _text(item.get(key))
            if not raw:
                continue
            found_email, found_phone, excerpt = _extract_contextual(raw)
            if not email and found_email:
                email = found_email
            if not phone and found_phone:
                phone = found_phone
            if (found_email or found_phone) and not evidence_source:
                evidence_source = key
                evidence_excerpt = excerpt
            if email and phone:
                break

    direct = bool(email or phone)
    route = "direct_contact" if direct else ("verified_web" if website else ("official_source_route" if source_url else "none"))
    source_backed = bool(direct or website)

    item["direct_contact_available"] = direct
    item["contact_route_available"] = route != "none"
    item["contact_source_backed"] = source_backed

    if source_backed:
        if email:
            item["contact_email"] = email
        if phone:
            item["contact_phone"] = phone
        if contact_person:
            item["contact_person"] = contact_person
        if website:
            item["buyer_website"] = website

    item["contact_enrichment"] = {
        "version": 2,
        "status": "source_backed" if source_backed else ("route_only" if source_url else "missing"),
        "route_type": route,
        "direct_contact_available": direct,
        "evidence_source": evidence_source or None,
        "evidence_excerpt": evidence_excerpt or None,
    }
    return item


def enrich_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("opportunities")
    if not isinstance(rows, list):
        return payload
    direct = backed = routes = 0
    enriched: list[Any] = []
    for row in rows:
        if not isinstance(row, dict):
            enriched.append(row)
            continue
        row = enrich_opportunity(row)
        direct += int(bool(row.get("direct_contact_available")))
        backed += int(bool(row.get("contact_source_backed")))
        routes += int(bool(row.get("contact_route_available")))
        enriched.append(row)
    payload["opportunities"] = enriched
    payload["contact_enrichment_summary"] = {
        "version": 2,
        "mode": "source_only_no_hallucination",
        "opportunities": len([x for x in enriched if isinstance(x, dict)]),
        "direct_contacts": direct,
        "source_backed_contacts": backed,
        "contact_routes": routes,
    }
    return payload


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.contact_enrichment <json-file>")
    path = Path(sys.argv[1])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload = enrich_payload(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
