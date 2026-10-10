from __future__ import annotations

from copy import deepcopy
from typing import Any

GULF_SOURCES = {
    "Saudi Arabia": {
        "name": "Etimad",
        "url": "https://tenders.etimad.sa/Tender/AllTendersForVisitor",
        "status": "official_source_registered",
        "live_ingestion": False,
    },
    "United Arab Emirates": {
        "name": "UAE Ministry of Finance Current Business Opportunities",
        "url": "https://mof.gov.ae/en/public-finance/government-procurement/current-business-opportunities/",
        "status": "official_source_registered",
        "live_ingestion": False,
    },
    "Qatar": {
        "name": "Monaqasat",
        "url": "https://monaqasat.mof.gov.qa/TendersOnlineServices/AvailableMinistriesTenders/2",
        "status": "official_source_registered",
        "live_ingestion": False,
    },
    "Kuwait": {"name": "Kuwait public procurement", "url": None, "status": "adapter_pending", "live_ingestion": False},
    "Oman": {"name": "Oman public procurement", "url": None, "status": "adapter_pending", "live_ingestion": False},
    "Bahrain": {"name": "Bahrain public procurement", "url": None, "status": "adapter_pending", "live_ingestion": False},
    "Yemen": {"name": "Yemen public procurement", "url": None, "status": "adapter_pending", "live_ingestion": False},
}


def _live(feed: dict[str, Any], count_key: str) -> tuple[bool, int]:
    count = int(feed.get(count_key) or 0)
    return bool(feed.get("live_ingestion")) and count > 0, count


def annotate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    registry = deepcopy(GULF_SOURCES)
    qatar_live, qatar_count = _live(payload.get("qatar_monaqasat_feed") or {}, "parsed_goods")
    uae_live, uae_count = _live(payload.get("uae_mof_feed") or {}, "parsed_opportunities")
    saudi_live, saudi_count = _live(payload.get("saudi_etimad_feed") or {}, "parsed_opportunities")

    for country, live, count in (
        ("Qatar", qatar_live, qatar_count),
        ("United Arab Emirates", uae_live, uae_count),
        ("Saudi Arabia", saudi_live, saudi_count),
    ):
        if live:
            registry[country]["live_ingestion"] = True
            registry[country]["status"] = "live_ingestion_verified_this_scan"
            registry[country]["last_scan_rows"] = count

    sources = [{"country": country, **source} for country, source in registry.items()]
    priority = ("Saudi Arabia", "United Arab Emirates", "Qatar")
    priority_live = all(registry[country]["live_ingestion"] for country in priority)
    payload["gulf_sources"] = {
        "sources": sources,
        "saudi_live_ingestion_verified": saudi_live,
        "uae_live_ingestion_verified": uae_live,
        "qatar_live_ingestion_verified": qatar_live,
        "priority_gulf_live_ingestion_verified": priority_live,
        "live_ingestion_verified": priority_live,
        "rule": "Each country becomes live only after real official notice ingestion in the current scan. Priority Gulf coverage requires Saudi Arabia, UAE and Qatar; registered links alone do not count.",
    }
    return payload
