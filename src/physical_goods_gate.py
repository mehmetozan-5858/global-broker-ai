from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .exportable_goods import classify


def apply_gate(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep only physical-goods candidates in the expensive research pipeline.

    Mixed/unknown records are retained in a separate review queue. Service,
    works and digital-only records are counted but not promoted or enriched.
    """
    opportunities = payload.get("opportunities") or []
    if not isinstance(opportunities, list):
        opportunities = []

    goods: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    excluded_service = 0
    excluded_non_physical = 0

    for raw in opportunities:
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        decision = classify(item)
        item["export_goods_review"] = decision
        status = decision.get("status")
        if status == "goods_candidate":
            item["opportunity_type"] = "FİZİKSEL_MAL_ADAYI"
            goods.append(item)
        elif status in {"review_mixed", "review_unknown"}:
            # Keep only for human review; downstream supplier/pricing research
            # must not treat these as commercial physical-goods opportunities.
            review.append(item)
        elif status == "exclude_non_physical":
            excluded_non_physical += 1
        else:
            excluded_service += 1

    payload["opportunities"] = goods
    payload["count"] = len(goods)
    payload["goods_review_queue"] = review
    payload["physical_goods_gate"] = {
        "mode": "physical_goods_only",
        "goods_candidates": len(goods),
        "review_mixed_or_unknown": len(review),
        "excluded_service_or_works": excluded_service,
        "excluded_non_physical": excluded_non_physical,
        "research_pipeline_receives_only_goods_candidates": True,
    }
    return payload


def main(path: str) -> None:
    p = Path(path)
    payload = json.loads(p.read_text(encoding="utf-8"))
    gated = apply_gate(payload)
    p.write_text(json.dumps(gated, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = gated["physical_goods_gate"]
    print("PHYSICAL_GOODS_GATE " + json.dumps(meta, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.physical_goods_gate <payload.json>")
    main(sys.argv[1])
