from __future__ import annotations

import html
import re
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse


class _ScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        src = dict(attrs).get("src")
        if src:
            self.scripts.append(html.unescape(src))


def script_urls(markup: str, page_url: str, *, limit: int = 12) -> list[str]:
    parser = _ScriptParser()
    parser.feed(markup)
    host = urlparse(page_url).netloc.lower()
    results: list[str] = []
    seen: set[str] = set()
    for src in parser.scripts:
        url = urljoin(page_url, src)
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != host:
            continue
        if url in seen:
            continue
        seen.add(url)
        results.append(url)
        if len(results) >= limit:
            break
    return results


def _fetch_text(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = response.read(2_000_000)
    return body.decode("utf-8", "replace")


# Only public endpoint-like strings are returned. Query strings, fragments, bearer-like
# values and long opaque tokens are deliberately stripped after parsing so diagnostics
# cannot become a credential exfiltration path.
_ENDPOINT_RE = re.compile(
    r"(?P<q>['\"])(?P<value>(?:https?://[^'\"\s]{4,240}|/[^'\"\s]{3,220}))(?P=q)",
    re.I,
)
_KEYWORDS = (
    "api", "tender", "competition", "opportun", "procurement", "rfq", "rfx",
    "alltenders", "visitor", "mof-dpp", "ajax", "wp-json", "gettender", "searchtender",
)


def endpoint_hints(text: str, base_url: str, *, limit: int = 24) -> list[str]:
    host = urlparse(base_url).netloc.lower()
    results: list[str] = []
    seen: set[str] = set()
    for match in _ENDPOINT_RE.finditer(text):
        raw = html.unescape(match.group("value")).strip()
        if not any(keyword in raw.lower() for keyword in _KEYWORDS):
            continue
        absolute = urljoin(base_url, raw)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != host:
            continue
        clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if len(clean) > 260 or clean in seen:
            continue
        if clean.lower().endswith((".js", ".css", ".png", ".jpg", ".jpeg", ".svg", ".woff", ".woff2")):
            continue
        seen.add(clean)
        results.append(clean)
        if len(results) >= limit:
            break
    return results


def discover(markup: str, page_url: str, *, max_scripts: int = 8) -> dict[str, object]:
    scripts = script_urls(markup, page_url, limit=max_scripts)
    hints = endpoint_hints(markup, page_url)
    fetched = 0
    errors: list[str] = []
    for script in scripts:
        if len(hints) >= 24:
            break
        try:
            body = _fetch_text(script)
            fetched += 1
            for hint in endpoint_hints(body, page_url, limit=24):
                if hint not in hints:
                    hints.append(hint)
                if len(hints) >= 24:
                    break
        except Exception as exc:
            errors.append(f"{urlparse(script).path}:{type(exc).__name__}")
    return {
        "same_origin_scripts_seen": len(scripts),
        "same_origin_scripts_fetched": fetched,
        "endpoint_hints": hints[:24],
        "errors": errors[:8],
    }
