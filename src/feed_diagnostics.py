from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse


def normalize_error(value: object) -> str:
    text = str(value or "unknown")
    if ":" in text:
        head, tail = text.split(":", 1)
        if head in {"HTTPError", "URLError", "TimeoutError", "ValueError", "OSError", "RuntimeError"}:
            if head == "HTTPError":
                # Keep HTTP status when present, discard long server text.
                pieces = tail.strip().split()
                status = next((p for p in pieces if p.isdigit() and len(p) == 3), None)
                return f"HTTPError:{status or 'unknown'}"
            if head == "ValueError":
                return f"ValueError:{tail.strip().split()[0] if tail.strip() else 'unknown'}"
            return head
    return text[:80]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.feed_diagnostics <live-json>")
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    opportunities = payload.get("opportunities") or []
    errors: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    source_errors: dict[str, Counter[str]] = defaultdict(Counter)
    status: Counter[str] = Counter()
    sample: dict[str, dict[str, str]] = {}
    attempted = parsed = 0

    for item in opportunities:
        if not isinstance(item, dict):
            continue
        info = item.get("document_extraction") or {}
        if not isinstance(info, dict):
            continue
        status[str(info.get("status") or "missing")] += 1
        if info.get("candidate_count"):
            attempted += 1
        if info.get("parsed_count"):
            parsed += 1
        for attempt in info.get("attempts") or []:
            if not isinstance(attempt, dict) or attempt.get("status") != "failed":
                continue
            url = str(attempt.get("url") or "")
            host = (urlparse(url).hostname or "unknown").lower()
            err = normalize_error(attempt.get("error"))
            errors[err] += 1
            sources[host] += 1
            source_errors[host][err] += 1
            sample.setdefault(err, {
                "host": host,
                "source": str(item.get("source") or ""),
                "url_path": urlparse(url).path[:180],
            })

    result = {
        "opportunities": len(opportunities),
        "attempted_opportunities": attempted,
        "parsed_opportunities": parsed,
        "extraction_status": dict(status.most_common()),
        "failure_types": dict(errors.most_common(20)),
        "failure_hosts": dict(sources.most_common(20)),
        "host_failure_types": {host: dict(counter.most_common(8)) for host, counter in source_errors.items()},
        "samples": sample,
    }
    print("DOCUMENT_FEED_DIAGNOSTICS " + json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
