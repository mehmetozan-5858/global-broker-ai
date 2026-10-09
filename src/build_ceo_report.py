"""Generate an internal CEO review report from sanitized opportunities JSON."""
from __future__ import annotations
import json
import sys
from datetime import date
from pathlib import Path
from src.pipeline import build_ceo_case, ceo_summary

def build_report(payload: dict) -> dict:
    cases = []
    for row in payload.get("opportunities", []):
        if isinstance(row, dict):
            cases.append(build_ceo_case(row))
    report = ceo_summary(cases)
    report["generated"] = date.today().isoformat()
    report["data_source"] = "sanitized_shadow_opportunities"
    return report

def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: python -m src.build_ceo_report INPUT_JSON OUTPUT_JSON", file=sys.stderr)
        return 2
    payload = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    report = build_report(payload)
    target = Path(argv[2])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
