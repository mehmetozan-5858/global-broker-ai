from __future__ import annotations

import re
import urllib.parse
from typing import Iterable, Any
from xml.etree import ElementTree

MAX_EXTRACTED_CHARS = 40000
ATTACHMENT_EXTENSIONS = (".pdf", ".docx", ".txt")
EMAIL_RE = re.compile(r"(?i)(?<![A-Z0-9._%+-])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})(?![A-Z0-9._%+-])")
PHONE_RE = re.compile(r"(?<!\d)(\+?\d[\d\s()./-]{7,}\d)(?!\d)")


def _clean_text(parts: Iterable[str]) -> str:
    text = " ".join(" ".join((part or "").split()) for part in parts if part)
    return " ".join(text.split())[:MAX_EXTRACTED_CHARS]


def _looks_like_attachment(value: str) -> bool:
    try:
        path = urllib.parse.urlparse(value.strip()).path.lower()
    except Exception:
        return False
    return path.endswith(ATTACHMENT_EXTENSIONS)


def _local_name(tag: Any) -> str:
    text = str(tag or "")
    if "}" in text:
        text = text.rsplit("}", 1)[-1]
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _node_text(node: ElementTree.Element) -> str:
    return " ".join(" ".join(node.itertext()).split()).strip()


def _clean_phone(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" .,-/()")
    digits = re.sub(r"\D", "", value)
    return value if 8 <= len(digits) <= 16 else ""


def extract_ted_contacts(data: bytes) -> dict[str, str]:
    """Extract only explicit TED/eForms touchpoint contact values.

    The parser is namespace/schema tolerant, but intentionally conservative: it
    accepts e-mail/telephone/person values only from explicit contact field names,
    and accepts HTTPS web addresses only from explicit internet-address fields.
    It never promotes an arbitrary narrative e-mail or URL to buyer contact data.
    """
    root = ElementTree.fromstring(data)
    result: dict[str, str] = {}

    for node in root.iter():
        name = _local_name(node.tag)
        value = _node_text(node)
        if not value:
            continue

        if "electronicmail" in name or name in {"email", "emailaddress", "emailuri"}:
            match = EMAIL_RE.search(value)
            if match and "contact_email" not in result:
                result["contact_email"] = match.group(1).lower()
                result["contact_evidence_source"] = "ted_xml_touchpoint"
            continue

        if "telephone" in name or name in {"phone", "phonenumber", "telephonecommunication"}:
            match = PHONE_RE.search(value)
            if match and "contact_phone" not in result:
                phone = _clean_phone(match.group(1))
                if phone:
                    result["contact_phone"] = phone
                    result["contact_evidence_source"] = "ted_xml_touchpoint"
            continue

        if name in {"contactname", "personname", "contactpointname"} and "contact_person" not in result:
            if 2 <= len(value) <= 160:
                result["contact_person"] = value
                result["contact_evidence_source"] = "ted_xml_touchpoint"
            continue

        if (
            "internetaddress" in name
            or name in {"websiteuri", "endpointuri", "buyerprofileuri"}
        ) and "buyer_website" not in result:
            if value.lower().startswith("https://"):
                result["buyer_website"] = value.rstrip(".,;)")
                result["contact_evidence_source"] = "ted_xml_touchpoint"

    return result


def parse_ted_xml(data: bytes, base_url: str) -> tuple[str, list[str]]:
    """Extract source-backed text and attachment links from TED/eForms XML.

    Namespace names and tag layouts can change between eForms notice types, so this
    deliberately reads XML text nodes generically instead of binding to one schema.
    It never invents fields: only source text and explicit URL-like attributes/text
    are returned.
    """
    root = ElementTree.fromstring(data)
    text = _clean_text(root.itertext())

    links: list[str] = []
    seen: set[str] = set()
    for node in root.iter():
        candidates = list(node.attrib.values())
        if node.text:
            candidates.extend(re.findall(r"https?://[^\s<>'\"]+", node.text))
        for raw in candidates:
            if not isinstance(raw, str):
                continue
            raw = raw.strip()
            if not raw:
                continue
            absolute = urllib.parse.urljoin(base_url, raw)
            if absolute in seen or not _looks_like_attachment(absolute):
                continue
            seen.add(absolute)
            links.append(absolute)
            if len(links) >= 3:
                return text, links
    return text, links


def is_xml_source(data: bytes, content_type: str, url: str) -> bool:
    content_type = (content_type or "").lower()
    path = urllib.parse.urlparse(url).path.lower().rstrip("/")
    prefix = data.lstrip()[:80].lower()
    return (
        "xml" in content_type
        or path.endswith("/xml")
        or path.endswith(".xml")
        or prefix.startswith(b"<?xml")
        or prefix.startswith(b"<notice")
    )
