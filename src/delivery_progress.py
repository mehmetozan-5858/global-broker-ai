"""Fixed-scope delivery estimates, kept separate from launch/data readiness."""
from __future__ import annotations

import json
from pathlib import Path

EVIDENCE = ("tests", "deployment", "live_verification")


def public_summary(ledger: dict) -> dict:
    """Publish only the roadmap, never opportunity/customer or recovery data."""
    report = build(ledger)
    return {
        "date": ledger["date"],
        "surfaces": report["surfaces"],
        "next_package": report["next_package"],
        "step_summary": report["step_summary"],
        "next_software_step": report["next_software_step"],
        "packages": [{**{key: p[key] for key in ("id", "title", "points", "status", "acceptance")},
                      "steps": [{key: step[key] for key in ("id", "title", "category", "status", "blocker") if key in step}
                                for step in p.get("steps", [])]} for p in ledger["packages"]],
        "scope": "Web ve PWA uygulamasının sabit kapsamlı teslimat takibi. Ticari açılış oranı değildir.",
        "completion_rule": "Puanlar test, üretim yayını ve canlı kabul kanıtı tamamlanınca eklenir.",
    }


def build(ledger: dict) -> dict:
    baseline = ledger["baseline"]
    packages = ledger["packages"]
    result = {"measurement": ledger["measurement"], "surfaces": {}, "next_package": None,
              "next_software_step": None,
              "step_summary": {key: {"complete": 0, "total": 0} for key in ("software", "live_acceptance")}}
    ids = [p["id"] for p in packages]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate package IDs")
    for p in packages:
        step_ids = set()
        for step in p.get("steps", []):
            category = step.get("category")
            if category not in result["step_summary"] or step.get("status") not in {"pending", "in_progress", "complete", "blocked"} or step.get("id") in step_ids:
                raise ValueError("Invalid or duplicate step")
            step_ids.add(step["id"])
            if step["status"] == "complete" and not all(isinstance(step.get("evidence", {}).get(k), str) and step["evidence"][k].strip() for k in EVIDENCE):
                raise ValueError("Completed step requires tests, deployment and live evidence")
            if (p["status"] != "complete" and category == "software"
                    and step["status"] in {"pending", "in_progress"}
                    and result["next_software_step"] is None):
                result["next_software_step"] = {
                    "package_id": p["id"], "step_id": step["id"],
                    "title": step["title"],
                }
            result["step_summary"][category]["total"] += 1
            result["step_summary"][category]["complete"] += int(step["status"] == "complete")
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
