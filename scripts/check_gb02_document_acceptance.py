"""Fail-closed GB-02 acceptance from a TED document-probe JSON record.

This is intentionally separate from the diagnostic workflow: a successful
probe *execution* is never the same thing as accepted technical documentation.
Usage: python scripts/check_gb02_document_acceptance.py path/to/probe.log
Review-only. Never initiates a request or approves commerce.
"""
import json
import sys
from pathlib import Path

MARKER = "TED_DOCUMENT_SOURCE_PROBE "


def evaluate(record):
    # Only exact non-negative integers count; booleans and strings are not evidence.
    attempted = record.get("attempted")
    linked = record.get("linked_documents_parsed")
    counts_valid = (type(attempted) is int and attempted > 0
                    and type(linked) is int and linked > 0)
    required = (
        counts_valid
        and record.get("linked_document_evidence_accepted") is True
        and record.get("annex_completeness_verified") is True
        and record.get("document_gate") == "accepted"
        and record.get("commercial_approval") is False
    )
    return {
        "gb02_document_acceptance": bool(required),
        "linked_documents_parsed": linked if type(linked) is int and linked >= 0 else 0,
        "annex_completeness_verified": record.get("annex_completeness_verified") is True,
        "commercial_approval": False,
        "status": "document_evidence_ready_for_separate_review" if required else "blocked",
    }


def inspect_log(text):
    lines = [line.split(MARKER, 1)[1] for line in text.splitlines() if MARKER in line]
    if not lines:
        raise ValueError("No TED_DOCUMENT_SOURCE_PROBE evidence")
    record = json.loads(lines[-1])
    if not isinstance(record, dict):
        raise ValueError("Invalid probe record")
    return evaluate(record)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: check_gb02_document_acceptance.py <probe-log>")
    try:
        result = inspect_log(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (ValueError, OSError, json.JSONDecodeError) as err:
        sys.exit(f"GB-02 review blocked: {err}")
    print(json.dumps(result, sort_keys=True))
    sys.exit(0 if result["gb02_document_acceptance"] else 2)
