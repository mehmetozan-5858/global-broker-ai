"""Bounded, read-only downloader for an explicitly selected TED OJ S daily XML archive.

Usage: python scripts/fetch_ted_daily_package.py 2026 216 /tmp/ted-daily.tar.gz
No schedule, credentials, bypass, deployment, or commercial acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

MAX_BYTES = 80_000_000
HOST = "ted.europa.eu"


def official(url):
    try:
        p = urlparse(url)
        return p.scheme == "https" and p.hostname == HOST and p.port in (None, 443) and not p.username and not p.password
    except ValueError:
        return False


class Redirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not official(newurl):
            raise ValueError("redirect outside official TED")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(year, issue, output):
    if not 2000 <= year <= 2100 or not 1 <= issue <= 366:
        raise ValueError("invalid OJ S issue")
    # TED's documented URL format uses /packages/notice/daily/YYYYNNNNN; live response is unverified. 
    # Publication numbers are NOT OJ S issue numbers.
    url = f"https://ted.europa.eu/packages/notice/daily/{year:04d}{issue:05d}"
    opener = build_opener(Redirects())
    with opener.open(Request(url, headers={"User-Agent": "GlobalBrokerEvidenceReview/1.0"}), timeout=25) as response:
        if response.status != 200 or not official(response.url):
            raise ValueError("untrusted or non-200 official response")
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("package exceeds bounded download limit")
        if not (data.startswith(bytes.fromhex("504b0304")) or data.startswith(bytes.fromhex("1f8b"))):
            raise ValueError("unexpected package signature; HTTP challenge or error envelope")
    if not data:
        raise ValueError("empty archive")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    return {"source": url, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
            "official_archive_downloaded": True, "notice_verified": False,
            "annexes_complete": False, "commercial_approval": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("year", type=int)
    parser.add_argument("issue", type=int)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(fetch(args.year, args.issue, args.output), sort_keys=True))
    except (OSError, ValueError) as error:
        parser.exit(2, f"TED daily download blocked: {type(error).__name__}: {error}\\n")
