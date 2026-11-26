"""Local-only, no-write diagnostic for a private opportunity snapshot.

Accepts a local JSON input; never contacts Supabase, GitHub, TED or AI providers.
Does not modify the input or publish individual opportunities/identifiers.
The optional output contains aggregate counts only and is NEVER approval to ingest.
"""
import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

from src.private_sync_payload import prepare
from src.private_snapshot_identity_gate import (
    PrivateSnapshotIdentityError, inspect_private_snapshot,
    require_unique_private_snapshot,
)


def diagnose_local_snapshot(source_path, aggregate_path=None):
    source = Path(source_path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("opportunities"), list):
        raise PrivateSnapshotIdentityError("invalid_snapshot_structure")

    # Prepare on a temporary COPY of the private data. The caller's snapshot is
    # never overwritten, and no raw records or identifiers are printed.
    with tempfile.TemporaryDirectory(prefix="gb-private-diagnostic-") as folder:
        temp = Path(folder) / "private.json"
        temp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            prepare(str(temp))
        prepared = json.loads(temp.read_text(encoding="utf-8"))
        rows = prepared.get("opportunities")
        counts = inspect_private_snapshot(rows)

    safe = {
        "schema": "gb-private-no-write-diagnostic-v1",
        "rows": counts["rows"],
        "duplicate_groups": counts["duplicate_identity_count"],
        "conflicting_groups": counts["conflicting_identity_count"],
        "cross_source_groups": counts["cross_source_collision_count"],
        "same_or_unknown_source_groups": counts["same_or_unknown_source_duplicate_count"],
        "missing_source_count": counts["missing_source_provenance_count"],
        "accepted_for_remote_write": False,
    }
    if aggregate_path is not None:
        Path(aggregate_path).write_text(
            json.dumps(safe, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
    # Report counts first, then fail closed when the input cannot be accepted.
    require_unique_private_snapshot(rows)
    return safe


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if not (1 <= len(args) <= 2):
        raise PrivateSnapshotIdentityError("usage: input.json [safe-aggregate.json]")
    result = diagnose_local_snapshot(args[0], args[1] if len(args) == 2 else None)
    print("GB_NO_WRITE_DIAGNOSTIC_OK rows={}".format(result["rows"]))


if __name__ == "__main__":
    try:
        main()
    except (PrivateSnapshotIdentityError, ValueError, KeyError, OSError, TypeError):
        raise SystemExit("GB_NO_WRITE_DIAGNOSTIC_BLOCKED")
