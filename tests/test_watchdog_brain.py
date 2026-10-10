from datetime import datetime, timedelta, timezone

from src.agent_center import build as build_agent_center
from src.watchdog import build as build_watchdog


def base_opportunity(**overrides):
    row = {
        "id": "opp-1",
        "title_tr": "Test fırsatı",
        "source_url": "https://example.com/source",
        "export_goods_review": {"status": "goods_candidate"},
        "core_field_coverage": {"complete": True},
        "specification_analysis": {"supplier_sourcing_ready": True, "status": "complete"},
        "supplier_research": {"verified_supplier_count": 1, "status": "verified"},
        "commercial_feasibility": {"calculation_ready": True, "status": "complete"},
        "offer_risk_gate": {"draft_offer_ready": True, "status": "ready"},
        "buyer_verification": {"status": "verified"},
    }
    row.update(overrides)
    return row


def test_ready_item_routes_to_human_review():
    payload = {"opportunities": [base_opportunity()]}
    build_agent_center(payload)
    finding = payload["watchdog"]["findings"][0]
    assert finding["health"] == "human_review"
    assert finding["recommendation"] == "human_review"
    assert finding["auto_restart_executed"] is False


def test_missing_heartbeat_is_unobservable_not_stalled():
    row = base_opportunity(core_field_coverage={"complete": False})
    payload = {"opportunities": [row]}
    build_agent_center(payload)
    finding = payload["watchdog"]["findings"][0]
    assert finding["health"] == "unobservable"
    assert finding["recommendation"] == "add_telemetry"


def test_old_research_progress_becomes_safe_retry_candidate():
    now = datetime(2026, 10, 10, 18, 0, tzinfo=timezone.utc)
    row = base_opportunity(
        core_field_coverage={"complete": False},
        updated_at=(now - timedelta(hours=30)).isoformat(),
    )
    payload = {
        "opportunities": [row],
        "watchdog_policy": {"stale_after_hours": 24},
    }
    build_agent_center(payload)
    build_watchdog(payload, now=now)
    finding = payload["watchdog"]["findings"][0]
    assert finding["health"] == "stalled"
    assert finding["safe_retry_candidate"] is True
    assert finding["recommendation"] == "safe_requeue"
    assert finding["external_action_authorized"] is False


def test_recent_progress_is_not_marked_stalled():
    now = datetime(2026, 10, 10, 18, 0, tzinfo=timezone.utc)
    row = base_opportunity(
        core_field_coverage={"complete": False},
        updated_at=(now - timedelta(hours=2)).isoformat(),
    )
    payload = {"opportunities": [row]}
    build_agent_center(payload)
    build_watchdog(payload, now=now)
    finding = payload["watchdog"]["findings"][0]
    assert finding["health"] in {"healthy", "warning"}
    assert finding["safe_retry_candidate"] is False


def test_watchdog_never_authorizes_external_actions():
    now = datetime(2026, 10, 10, 18, 0, tzinfo=timezone.utc)
    row = base_opportunity(
        source_url=None,
        updated_at=(now - timedelta(hours=48)).isoformat(),
    )
    payload = {"opportunities": [row]}
    build_agent_center(payload)
    build_watchdog(payload, now=now)
    watchdog = payload["watchdog"]
    assert watchdog["mode"] == "shadow"
    assert watchdog["policy"]["auto_restart_external_actions"] is False
    assert all(x["external_action_authorized"] is False for x in watchdog["findings"])
