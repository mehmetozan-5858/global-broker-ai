"""Bounded navigation from a lot page to its explicitly linked tender index.

Navigation hints only discover documents; they never select a lot or authorize
external actions. Ordinary links and guessed URLs are deliberately excluded.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit, urlunsplit


PARENT_LABEL = re.compile(
    r"^(?:vai all['’]elenco lotti|all lots|lot overview|parent notice|main tender)$",
    re.I,
)


def same_origin(left: str, right: str) -> bool:
    try:
        def origin(url: str):
            p = urlsplit(url)
            if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password:
                return None
            return p.scheme, p.hostname.lower(), p.port or (443 if p.scheme == "https" else 80)
        first = origin(left)
        return first is not None and first == origin(right)
    except (TypeError, ValueError):
        return False


def document_indexes(links: list[dict[str, str]], base_url: str) -> list[str]:
    out: list[str] = []
    for link in links:
        label = " ".join(link.get("label", "").split())
        if not PARENT_LABEL.fullmatch(label):
            continue
        try:
            url = urljoin(base_url, link["href"])
            p = urlsplit(url)
            # Parent indices have no query or fragment. A link to login, a
            # download or a state-changing endpoint is never an index hint.
            if p.query or p.fragment or not same_origin(url, base_url):
                continue
            if not re.fullmatch(r"/(?:tender|tenders|notice|notices)/[A-Za-z0-9_-]+/?", p.path):
                continue
            url = urlunsplit((p.scheme, p.netloc, p.path, "", ""))
            if url.rstrip("/") != base_url.rstrip("/") and url not in out:
                out.append(url)
        except (KeyError, TypeError, ValueError):
            continue
    return out
