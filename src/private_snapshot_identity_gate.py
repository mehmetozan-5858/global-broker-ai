"""Preflight private snapshot identities before remote Supabase ingest.

Never publish row content, direct contacts or opportunity IDs to CI output.
This is a fail-closed diagnostic, not a deduplication or acceptance shortcut.
"""
import hashlib
import json
import sys
from pathlib import Path


class PrivateSnapshotIdentityError(ValueError):
    pass


def inspect_private_snapshot(rows):
    if not isinstance(rows, list) or not rows:
        raise PrivateSnapshotIdentityError("empty_or_invalid_snapshot")
    if len(rows) > 1000:
        raise PrivateSnapshotIdentityError("too_many_rows")
    seen = {}
    missing_provenance = 0
    duplicates = set()
    conflicts = set()
    cross_source = set()
    same_source = set()
    for row in rows:
        if not isinstance(row, dict):
            raise PrivateSnapshotIdentityError("invalid_opportunity_row")
        identifier = str(row.get("opportunity_id") or row.get("id") or "")[:200]
        if not identifier:
            raise PrivateSnapshotIdentityError("missing_opportunity_id")
        digest = hashlib.sha256(
            json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode()
        ).hexdigest()
        source = str(row.get('source') or row.get('source_name') or '').strip()
        if not source:
            missing_provenance += 1
        if identifier in seen:
            duplicates.add(identifier)
            previous_digest, previous_source = seen[identifier]
            if previous_digest != digest:
                conflicts.add(identifier)
            if previous_source and source and previous_source != source:
                cross_source.add(identifier)
            else:
                same_source.add(identifier)
        else:
            seen[identifier] = (digest, source)
    # No IDs or row text returned or logged: only aggregate counts.
    return {"rows": len(rows), "missing_source_provenance_count": missing_provenance,
            "duplicate_identity_count": len(duplicates),
            "conflicting_identity_count": len(conflicts),
            "cross_source_collision_count": len(cross_source),
            "same_or_unknown_source_duplicate_count": len(same_source)}


def require_unique_private_snapshot(rows):
    outcome = inspect_private_snapshot(rows)
    if outcome["missing_source_provenance_count"]:
        raise PrivateSnapshotIdentityError(
            "missing_source_provenance: rows={}".format(outcome["missing_source_provenance_count"])
        )
    if outcome["duplicate_identity_count"]:
        raise PrivateSnapshotIdentityError(
            "duplicate_opportunity_id: repeated={} conflicting={} cross_source={}".format(
                outcome["duplicate_identity_count"], outcome["conflicting_identity_count"],
                outcome["cross_source_collision_count"]
            )
        )
    return outcome


def main(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    result = require_unique_private_snapshot(data.get("opportunities"))
    print("PRIVATE_SNAPSHOT_IDENTITY_OK rows={}".format(result["rows"]))


if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except (PrivateSnapshotIdentityError, ValueError, KeyError) as exc:
        raise SystemExit("PRIVATE_SNAPSHOT_IDENTITY_BLOCKED " + str(exc))
