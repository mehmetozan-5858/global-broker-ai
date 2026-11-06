"""Read-only E-ZAK public document discovery with bounded official-host downloads.

No login, bypass, supplier contact or commercial approval. The index must be
publicly accessible; JS-only, challenge and rate-limit pages fail closed.
Usage: python scripts/ezak_public_annex_sync.py --output /private/ted-47078
"""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, unquote
from urllib.request import Request, build_opener, HTTPRedirectHandler

BASE = "https://zakazky.krajbezkorupce.cz/contract_display_47078.html"
HOST = "zakazky.krajbezkorupce.cz"
MAX_INDEX = 2_000_000
MAX_FILE = 12_000_000
EXTENSIONS = (".pdf", ".doc", ".docx", ".xlsx", ".xls")
EXPECTED_XLSX = "41144156ef49a411de75c423f3e460732bc1bc111da326d76801cb798de20d45"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            href = dict(attrs).get("href")
            if href:
                self.hrefs.append(href)


def official_url(url):
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname == HOST and not parsed.username and not parsed.password and parsed.port in (None, 443)


class OfficialRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not official_url(newurl):
            raise ValueError("Redirect outside the official E-ZAK host")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def get_bounded(url, limit):
    if not official_url(url):
        raise ValueError("Non-official E-ZAK URL")
    opener = build_opener(OfficialRedirects())
    request = Request(url, headers={"User-Agent": "GlobalBrokerEvidenceReview/1.0", "Accept": "text/html,application/pdf,application/octet-stream"})
    with opener.open(request, timeout=15) as response:
        if not official_url(response.url):
            raise ValueError("Final URL outside official E-ZAK host")
        if response.status != 200:
            raise ValueError("Unexpected HTTP status")
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("Source exceeds configured byte limit")
        return data, response.headers.get("Content-Type", "").lower(), response.url


def discover(index_html, index_url=BASE):
    parser = Links()
    parser.feed(index_html.decode("utf-8", errors="replace"))
    found = {}
    for href in parser.hrefs:
        url = urljoin(index_url, href)
        if not official_url(url):
            continue
        path = unquote(urlparse(url).path).lower()
        if any(path.endswith(ext) for ext in EXTENSIONS) or "download" in path or "document" in path or "file" in path:
            found[url] = True
    return sorted(found)


def sync(output):
    index, content_type, final_url = get_bounded(BASE, MAX_INDEX)
    if "html" not in content_type or b"<html" not in index[:10000].lower():
        raise ValueError("E-ZAK did not return an HTML index")
    urls = discover(index, final_url)
    if not urls:
        raise ValueError("No public annex links detected: manual source review required")
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for i, url in enumerate(urls):
        try:
            data, mime, final = get_bounded(url, MAX_FILE)
            if data[:256].lstrip().lower().startswith((b"<!doctype html", b"<html", b"<?xml")):
                raise ValueError("Error or challenge envelope is not an annex")
            if data.startswith(b"%PDF-"):
                kind = "pdf"
            elif data.startswith(bytes.fromhex("504b0304")):
                kind = "zip-based-office"
            elif data.startswith(bytes.fromhex("d0cf11e0")):
                kind = "legacy-office"
            else:
                raise ValueError("Unknown document signature")
            digest = hashlib.sha256(data).hexdigest()
            extension = ".pdf" if kind == "pdf" else ".bin"
            filename = f"annex-{i:03d}-{digest[:16]}{extension}"
            (output / filename).write_bytes(data)
            records.append({"source_url": final, "sha256": digest, "bytes": len(data), "kind": kind, "file": filename,
                            "matches_prior_xlsx_sha256": digest == EXPECTED_XLSX, "accepted": False})
        except (HTTPError, URLError, ValueError, TimeoutError) as exc:
            records.append({"source_url": url, "error": type(exc).__name__, "accepted": False})
    manifest = {"notice": "702997-2026", "amendment": "746528-2026", "ezak_dbid": 47078,
                "source_index": BASE, "records": records, "commercial_approval": False,
                "revision_verified": False, "complete_annex_set_verified": False}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    if not records or any("error" in item for item in records):
        raise ValueError("Incomplete annex acquisition; see private manifest")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = sync(args.output)
        print(json.dumps({"files_observed": len(result["records"]), "commercial_approval": False}))
    except (ValueError, HTTPError, URLError, OSError, TimeoutError) as exc:
        parser.exit(2, f"Public annex sync blocked: {type(exc).__name__}: {exc}\\n")
