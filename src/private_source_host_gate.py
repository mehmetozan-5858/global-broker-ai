"""Read-only source-host provenance check for private opportunity snapshots.

A canonical source host is a minimum prerequisite, never an official notice
content, annex, supplier or commercial validation. Only aggregate counts returned.
"""
from urllib.parse import urlsplit
import json
import sys
from pathlib import Path

OFFICIAL_HOSTS = {
    "TED": frozenset({"ted.europa.eu"}),
    "WORLD_BANK": frozenset({"projects.worldbank.org"}),
    "SAM_GOV": frozenset({"sam.gov"}),
    "Qatar Monaqasat": frozenset({"monaqasat.mof.gov.qa"}),
    "Saudi Etimad official visitor API": frozenset({"tenders.etimad.sa"}),
}


def official_source_host(source, value):
    """Exact HTTPS hostname check; rejects lookalikes, credentials and ports."""
    allowed = OFFICIAL_HOSTS.get(source)
    if allowed is None or not isinstance(value, str):
        return False
    try:
        parts = urlsplit(value)
        return (
            parts.scheme == "https"
            and parts.hostname in allowed
            and parts.username is None
            and parts.password is None
            and parts.port in (None, 443)
            and bool(parts.path and parts.path != "/")
            and not any(ord(c) < 32 for c in value)
        )
    except ValueError:
        return False


def summarize_source_hosts(rows):
    if not isinstance(rows, list):
        raise ValueError("invalid_source_snapshot")
    return {
        "rows": len(rows),
        "official_host_matches": sum(
            official_source_host(r.get("source"), r.get("source_url"))
            for r in rows if isinstance(r, dict)
        ),
        "official_host_mismatches": sum(
            not official_source_host(r.get("source"), r.get("source_url"))
            for r in rows if isinstance(r, dict)
        ) + sum(not isinstance(r, dict) for r in rows),
        "content_and_annex_verified": False,
        "commercial_party_verified": False,
    }


def require_official_source_hosts(rows):
    report = summarize_source_hosts(rows)
    if not report["rows"] or report["official_host_mismatches"]:
        raise ValueError(
            "source_host_validation_blocked rows={} mismatches={}".format(
                report["rows"], report["official_host_mismatches"]
            )
        )
    return report


def main(snapshot_path):
    data = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    rows = data.get("opportunities") if isinstance(data, dict) else None
    result = require_official_source_hosts(rows)
    print("OFFICIAL_SOURCE_HOST_OK rows={}".format(result["rows"]))


if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except (IndexError, ValueError, OSError) as exc:
        # Never emit snapshot or contact contents in CI output.
        raise SystemExit("OFFICIAL_SOURCE_HOST_BLOCKED " + (
            str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        ))
