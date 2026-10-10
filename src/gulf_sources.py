from __future__ import annotations

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
    sources = []
    for country, source in GULF_SOURCES.items():
        row = {"country": country, **source}
        sources.append(row)
    payload["gulf_sources"] = {
        "sources": sources,
        "live_ingestion_verified": False,
        "rule": "Registered official links are discovery sources only until real notice ingestion, document provenance and refresh tests pass.",
    }
    return payload
