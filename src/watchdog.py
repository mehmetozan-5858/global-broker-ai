from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

DEFAULT_STALE_HOURS = 24
RESEARCH_ONLY_AGENTS = {
    "official_source",
    "physical_goods",
    "field_evidence",
    "specification",
    "verified_supplier",
    "commercial_feasibility",
    "offer_risk_gate",
}


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _identifier(item: dict[str, Any], index: int) -> str:
    for key in ("id", "opportunity_id", "tender_id", "reference_number", "rfq_number"):
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return f"row-{index + 1}"


def _last_progress(item: dict[str, Any]) -> datetime | None:
    candidates: list[Any] = [
        item.get("last_progress_at"),
        item.get("agent_updated_at"),
        item.get("updated_at"),
        (item.get("workflow") or {}).get("updated_at"),
    ]
    for section in (
        "buyer_verification",
        "supplier_research",
        "commercial_feasibility",
        "offer_risk_gate",
        "specification_analysis",
    ):
        value = (item.get(section) or {}).get("updated_at")
        if value:
            candidates.append(value)
    parsed = [dt for dt in (_parse_time(x) for x in candidates) if dt is not None]
    return max(parsed) if parsed else None


def build(payload: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    now_utc = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    policy = payload.get("watchdog_policy") or {}
    stale_hours = int(policy.get("stale_after_hours") or DEFAULT_STALE_HOURS)
    rows = [x for x in (payload.get("opportunities") or []) if isinstance(x, dict)]
    by_id = {_identifier(item, i): item for i, item in enumerate(rows)}
    center = payload.get("agent_center") or {}
    queue = [x for x in (center.get("work_queue") or []) if isinstance(x, dict)]

    findings: list[dict[str, Any]] = []
    counts = {"healthy": 0, "warning": 0, "stalled": 0, "unobservable": 0, "human_review": 0}

    for row in queue:
        oid = str(row.get("opportunity_id") or "")
        item = by_id.get(oid, {})
        next_agent = str(row.get("next_agent") or "human_review")
        blockers = list(row.get("blockers") or [])
        last = _last_progress(item)
        age_hours = None if last is None else round((now_utc - last).total_seconds() / 3600, 1)

        if next_agent == "human_review":
            health = "human_review"
            recommendation = "human_review"
            reason = "Araştırma kapıları tamamlanmış; insan incelemesi gerekiyor."
        elif last is None:
            health = "unobservable"
            recommendation = "add_telemetry"
            reason = "İlerleme zaman damgası yok; ajan takıldı varsayılamaz."
        elif age_hours is not None and age_hours >= stale_hours:
            health = "stalled"
            recommendation = "safe_requeue" if next_agent in RESEARCH_ONLY_AGENTS else "human_review"
            reason = f"Son doğrulanabilir ilerleme {age_hours} saat önce."
        elif len(blockers) >= 4:
            health = "warning"
            recommendation = "continue_research"
            reason = "Birden fazla kanıt kapısı halen açık."
        else:
            health = "healthy"
            recommendation = "continue_research"
            reason = "Mevcut kanıtlara göre kritik bekleme eşiği aşılmamış."

        counts[health] += 1
        findings.append(
            {
                "opportunity_id": oid,
                "title": row.get("title") or "Untitled opportunity",
                "next_agent": next_agent,
                "blockers": blockers,
                "health": health,
                "reason": reason,
                "last_progress_at": last.isoformat() if last else None,
                "age_hours": age_hours,
                "recommendation": recommendation,
                "safe_retry_candidate": bool(health == "stalled" and next_agent in RESEARCH_ONLY_AGENTS),
                "auto_restart_executed": False,
                "external_action_authorized": False,
            }
        )

    result = {
        "mode": "shadow",
        "stale_after_hours": stale_hours,
        "checked_at": now_utc.isoformat(),
        "counts": counts,
        "findings": findings,
        "requires_attention": [x for x in findings if x["health"] in {"stalled", "unobservable", "human_review"}],
        "policy": {
            "auto_restart_external_actions": False,
            "research_safe_retry_may_be_suggested": True,
            "email_send": False,
            "payment": False,
            "order": False,
            "contract_sign": False,
            "human_approval_required": True,
        },
    }
    payload["watchdog"] = result
    return result
