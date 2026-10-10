from __future__ import annotations

import json
import sys
from pathlib import Path

from .agent_center import build as build_agent_center
from .commercial_feasibility import process_payload as process_feasibility
from .commercial_terms import process_payload as process_commercial_terms
from .gulf_sources import annotate_payload as annotate_gulf_sources
from .launch_gate import evaluate as evaluate_launch
from .launch_readiness_report import build as build_launch_readiness_report
from .offer_risk_gate import process_payload as process_offer_risk
from .supplier_research import process_payload as process_supplier_research


def process(payload: dict) -> dict:
    annotate_gulf_sources(payload)                  # A4 registry / truthfulness gate
    process_commercial_terms(payload)               # A5 commercial tender terms
    process_supplier_research(payload)              # A6 source-backed research queue
    process_feasibility(payload)                    # A7 calculation readiness
    process_offer_risk(payload)                     # A8 draft / risk gate
    build_agent_center(payload)                     # A9 measurable agent center
    evaluate_launch(payload)                        # A10 fail-closed production gate
    build_launch_readiness_report(payload)          # operator-visible launch blocker report
    return payload


def main(path: str) -> None:
    p = Path(path)
    payload = json.loads(p.read_text(encoding="utf-8"))
    process(payload)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("REMAINING_PIPELINE", json.dumps({
        "gulf_live": (payload.get("gulf_sources") or {}).get("live_ingestion_verified"),
        "supplier_ready": (payload.get("supplier_research_summary") or {}).get("research_ready"),
        "commercial_ready": (payload.get("commercial_feasibility_summary") or {}).get("calculation_ready"),
        "draft_ready": (payload.get("offer_risk_summary") or {}).get("internal_draft_ready"),
        "launch_ready": (payload.get("launch_gate") or {}).get("launch_ready"),
        "launch_blockers": (payload.get("launch_gate") or {}).get("blockers"),
        "launch_categories": (payload.get("launch_readiness_report") or {}).get("categories"),
        "intended_market_scope": (payload.get("launch_readiness_report") or {}).get("intended_market_scope"),
        "worldwide_live_coverage_verified": False,
    }, ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.remaining_pipeline <payload.json>")
    main(sys.argv[1])
