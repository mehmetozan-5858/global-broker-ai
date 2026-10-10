from __future__ import annotations

from copy import deepcopy
from typing import Any

GULF_SOURCES = {
    "Saudi Arabia": {
        "name": "Etimad",
        "url": "https://tenders.etimad.sa/",
        "status": "official_source_registered",
        "live_ingestion": False,
    },
    "United Arab Emirates": {
        "name": "UAE Ministry of Finance Digital Procurement Platform",
        "url": "https://mof.gov.ae/en/public-finance/government-procurement/digital-procurement-platform/",
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


def annotate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    registry = deepcopy(GULF_SOURCES)
    qatar = payload.get("qatar_monaqasat_feed") or {}
    qatar_live = bool(qatar.get("live_ingestion")) and int(qatar.get("parsed_goods") or 0) > 0
    if qatar_live:
        registry["Qatar"]["live_ingestion"] = True
        registry["Qatar"]["status"] = "live_goods_ingestion_verified_this_scan"
        registry["Qatar"]["last_scan_goods"] = int(qatar.get("parsed_goods") or 0)

    sources = [{"country": country, **source} for country, source in registry.items()]
    priority = ("Saudi Arabia", "United Arab Emirates", "Qatar")
    priority_live = all(registry[country]["live_ingestion"] for country in priority)
    payload["gulf_sources"] = {
        "sources": sources,
        "qatar_live_ingestion_verified": qatar_live,
        "priority_gulf_live_ingestion_verified": priority_live,
        "live_ingestion_verified": priority_live,
        "rule": "Each country becomes live only after real notice ingestion in the current scan. Priority Gulf coverage requires Saudi Arabia, UAE and Qatar; registered links alone do not count.",
    }
    return payload
