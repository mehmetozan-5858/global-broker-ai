from __future__ import annotations

import re
import urllib.parse
from typing import Iterable
from xml.etree import ElementTree

MAX_EXTRACTED_CHARS = 40000
ATTACHMENT_EXTENSIONS = (".pdf", ".docx", ".txt")


def _clean_text(parts: Iterable[str]) -> str:
    text = " ".join(" ".join((part or "").split()) for part in parts if part)
    return " ".join(text.split())[:MAX_EXTRACTED_CHARS]


def _looks_like_attachment(value: str) -> bool:
    try:
        path = urllib.parse.urlparse(value.strip()).path.lower()
    except Exception:
        return False
    return path.endswith(ATTACHMENT_EXTENSIONS)


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
