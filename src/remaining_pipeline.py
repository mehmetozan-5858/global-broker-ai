from __future__ import annotations

import json
import sys
from pathlib import Path

from .agent_center import build as build_agent_center
from .commercial_evidence_acceptance import process_payload as process_commercial_evidence
from .commercial_feasibility import process_payload as process_feasibility
from .commercial_blocker_triage import build as build_commercial_blocker_triage
from .commercial_research_agents import build as build_commercial_research_agents
from .commercial_terms import process_payload as process_commercial_terms
from .data_completion_queue import build as build_data_completion_queue
from .deal_lifecycle import process_payload as process_deal_lifecycle
from .gulf_sources import annotate_payload as annotate_gulf_sources
from .launch_gate import evaluate as evaluate_launch
from .launch_readiness_report import build as build_launch_readiness_report
from .offer_candidate_queue import build as build_offer_candidate_queue
from .offer_risk_gate import process_payload as process_offer_risk
from .price_margin_gate import process_payload as process_price_margin
from .pilot_dossiers import build as build_pilot_dossiers
from .pilot_evidence import apply as apply_pilot_evidence
from .supplier_research import process_payload as process_supplier_research
from .verification import sanitize_payload as sanitize_buyer_verification


def process(payload: dict) -> dict:
    annotate_gulf_sources(payload)                  # A4 registry / truthfulness gate
    apply_pilot_evidence(payload)                   # persistent source-backed pilot research
    sanitize_buyer_verification(payload)            # re-evaluate buyer after authoritative pilot evidence
    process_commercial_terms(payload)               # A5 commercial tender terms
    build_data_completion_queue(payload)            # core source-data completion priority queue
    process_supplier_research(payload)              # A6 source-backed supplier verification
    process_commercial_evidence(payload)            # verified price/freight/source-term evidence acceptance
    process_feasibility(payload)                    # A7 calculation readiness
    process_price_margin(payload)                   # Stage 4 verified quotes, expiry, gross spread
    build_commercial_blocker_triage(payload)        # source-backed commercial research queue
    build_commercial_research_agents(payload)       # Price/Logistics/Source Terms agent tasks
    build_pilot_dossiers(payload)                   # evidence-ranked first 10 real dossiers
    process_offer_risk(payload)                     # A8 draft / risk gate
    build_offer_candidate_queue(payload)            # internal-only human offer review queue
    build_agent_center(payload)                     # A9 measurable agent center + watchdog
    process_deal_lifecycle(payload)                 # A12 evidence-gated deal/payment lifecycle
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
        "pilot_evidence_applied": (payload.get("pilot_evidence_summary") or {}).get("applied"),
        "buyer_verified": (payload.get("buyer_verification_summary") or {}).get("verified"),
        "data_core_complete": (payload.get("data_completion_queue") or {}).get("core_complete"),
        "data_core_incomplete": (payload.get("data_completion_queue") or {}).get("core_incomplete"),
        "data_completion_rate_pct": (payload.get("data_completion_queue") or {}).get("completion_rate_pct"),
        "data_missing_field_counts": (payload.get("data_completion_queue") or {}).get("missing_field_counts"),
        "supplier_ready": (payload.get("supplier_research_summary") or {}).get("research_ready"),
        "commercial_evidence_accepted": (payload.get("commercial_evidence_acceptance_summary") or {}).get("accepted"),
        "commercial_evidence_rejected": (payload.get("commercial_evidence_acceptance_summary") or {}).get("rejected"),
        "stage4_price_ready": (payload.get("price_margin_summary") or {}).get("price_ready"),
        "stage4_gross_spread_ready": (payload.get("price_margin_summary") or {}).get("gross_spread_ready"),
        "pilot_dossiers_selected": (payload.get("pilot_dossier_summary") or {}).get("selected_count"),
        "pilot_dossiers_missing_evidence": (payload.get("pilot_dossier_summary") or {}).get("missing_evidence_counts"),
        "stage4_blockers": (payload.get("price_margin_summary") or {}).get("missing_or_invalid_counts"),
        "commercial_ready": (payload.get("commercial_feasibility_summary") or {}).get("calculation_ready"),
        "commercial_blocker_counts": (payload.get("commercial_blocker_triage") or {}).get("blocker_counts"),
        "commercial_research_tasks": (payload.get("commercial_research_agents") or {}).get("task_count"),
        "commercial_research_agent_counts": (payload.get("commercial_research_agents") or {}).get("agent_task_counts"),
        "draft_ready": (payload.get("offer_risk_summary") or {}).get("internal_draft_ready"),
        "offer_review_candidates": (payload.get("offer_candidate_queue") or {}).get("candidate_count"),
        "offer_review_risk_cases": (payload.get("offer_candidate_queue") or {}).get("risk_review_required"),
        "deal_case_count": (payload.get("deal_lifecycle_summary") or {}).get("case_count"),
        "deal_state_counts": (payload.get("deal_lifecycle_summary") or {}).get("state_counts"),
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
