"""Fixed-scope delivery estimates, kept separate from launch/data readiness."""
from __future__ import annotations

import json
from pathlib import Path

EVIDENCE = ("tests", "deployment", "live_verification")


def build(ledger: dict) -> dict:
    baseline = ledger["baseline"]
    packages = ledger["packages"]
    result = {"measurement": ledger["measurement"], "surfaces": {}, "next_package": None}
    ids = [p["id"] for p in packages]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate package IDs")
    for p in packages:
        if p["status"] not in {"pending", "in_progress", "complete", "blocked"}:
            raise ValueError("Unknown package status")
        if p["status"] == "complete" and not all(
            isinstance(p.get("evidence", {}).get(k), str) and p["evidence"][k].strip()
            for k in EVIDENCE
        ):
            raise ValueError("Completed package requires tests, deployment and live evidence")
        if result["next_package"] is None and p["status"] != "complete":
            result["next_package"] = p["id"]
    for surface in ("web", "app"):
        weights = [p["points"][surface] for p in packages]
        if any(type(w) is not int or w < 0 for w in weights):
            raise ValueError("Weights must be nonnegative integers")
        start = baseline[surface]
        if type(start) is not int or not 0 <= start <= 100 or start + sum(weights) != 100:
            raise ValueError("Baseline plus fixed package weights must equal 100")
        earned = sum(p["points"][surface] for p in packages if p["status"] == "complete")
        result["surfaces"][surface] = {"baseline": start, "earned": earned, "current": start + earned}
    return result


if __name__ == "__main__":
    ledger = Path(__file__).resolve().parents[1] / "docs/delivery-progress.json"
    print(json.dumps(build(json.loads(ledger.read_text())), ensure_ascii=False, indent=2))
