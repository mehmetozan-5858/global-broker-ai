"""Source-backed overlay for the second pilot dossier: Netherlands Police LHP carry equipment.

This module records only evidence already present in official/traceable public sources.
Supplier leads remain category matches until the exact tender specification is reviewed.
No quote, price, or supplier verification is fabricated.
"""
from __future__ import annotations

from typing import Any

OPPORTUNITY_ID = "gb_04100c0f0da5c6a5c11d27f6253bf28c"

OVERLAY: dict[str, Any] = {
    "source_url": "https://ted.europa.eu/en/notice/-/detail/663841-2026",
    "product_name": "LHP taşıma ekipmanı: LHP çantası, bacak çantası ve bacak çantası bağlantı aparatı",
    "title_tr": "Hollanda Polisi LHP taşıma ekipmanı alımı",
    "buyer_registry_evidence": [
        {
            "authority": "official_institution_directory",
            "url": "https://www.politie.nl/en/information/about-the-netherlands-police.html",
            "buyer_name": "Politie",
            "name_match": True,
            "country_match": True,
            "note": "Official Netherlands Police website identifies the national police force.",
        },
        {
            "authority": "public_entity_registry",
            "url": "https://www.politie.nl/wet-open-overheid/organisatiegegevens",
            "buyer_name": "Politie",
            "name_match": True,
            "country_match": True,
            "note": "Official Netherlands Police organisation-information page independently corroborates the institution.",
        },
    ],
    "stage4_research": {
        "status": "buyer_verified_supplier_spec_research",
        "researched_at": "2026-10-12",
        "notice_number": "663841-2026",
        "procedure_reference": "4074015e-cc95-4e5f-9ddd-ea43ec393e1c",
        "product_scope": "Police LHP carrying equipment: two LHP bag sizes, LHP leg bag and connector for the leg bag.",
        "quantity_status": "source_backed_32000",
        "quantity": "32000",
        "estimated_value_status": "public_notice_secondary_corroboration",
        "estimated_value_eur": "2500000",
        "deadline": "2026-11-05T13:00:00Z",
        "price_status": "not_quoted",
        "document_access_gate": {
            "status": "public_tender_documents_available",
            "external_purchase_required": False,
            "payment_authorized": False,
            "exact_specification_extracted": False,
            "document_route": "https://s2c.mercell.com/today/235745",
            "reason": "TED source identifies the goods, quantity and procurement-document route. Exact material, dimensions, construction and interface details still require tender-document review before supplier verification or quote acceptance.",
        },
        "supplier_leads": [
            {
                "name": "Fora Group",
                "url": "https://fora-grup-savunma.idef.com.tr/",
                "status": "category_match_exact_spec_pending",
                "identity_evidence": "IDEF exhibitor profile identifies the Turkish company and its production/export activity.",
                "product_evidence": "Produces tactical medical equipment, soft/hard carrying cases, individual first-aid bags and operational medical bags; reports exports to 32 countries.",
            },
            {
                "name": "ETM Çanta",
                "url": "https://etmcanta.com.tr/en/bag-manufacturer-in-turkey-or-oem-and-private-label-etm-canta",
                "status": "category_match_exact_spec_pending",
                "identity_evidence": "Official Turkish manufacturer website.",
                "product_evidence": "Lists medical equipment bags, technical/service bags, protective transport cases and custom OEM/private-label production to customer specifications.",
            },
            {
                "name": "Akıncı Taktik / Anafarta",
                "url": "https://www.europages.com.tr/tr/company/akinci-taktik-tekstil-ve-savunma-sanayi-ticaret-anonim-sirketi-22307614",
                "status": "category_match_exact_spec_pending",
                "identity_evidence": "Verified manufacturer profile lists İzmir production location and worldwide delivery.",
                "product_evidence": "Manufactures tactical pouches, bags and backpacks for military, law-enforcement and security use and supports custom production.",
            },
            {
                "name": "Tetrat Group",
                "url": "https://www.tetratgrup.com.tr/en/tccc",
                "status": "category_match_exact_spec_pending",
                "identity_evidence": "Official company website identifies Ankara operations in tactical and emergency medical equipment.",
                "product_evidence": "Product portfolio includes individual first-aid bags, operation bags and field emergency medical bags.",
            },
        ],
        "next_required_evidence": [
            "extract exact bag dimensions/material/attachment-interface requirements from tender documents",
            "map each supplier candidate to every mandatory specification",
            "verify at least three supplier identities and exact-spec capability",
            "obtain source-backed supplier quote with currency and validity",
        ],
        "rule": "Category-level bag manufacturing capability is not exact tender compliance. Supplier verification and pricing remain blocked until the tender specification is matched line-by-line.",
    },
}


def apply(payload: dict[str, Any]) -> dict[str, Any]:
    applied = 0
    for row in payload.get("opportunities") or []:
        if not isinstance(row, dict):
            continue
        oid = row.get("opportunity_id") or row.get("id")
        if str(oid) != OPPORTUNITY_ID:
            continue
        for key, value in OVERLAY.items():
            row[key] = value
        applied += 1
    payload["pilot_evidence_nl_summary"] = {
        "applied": applied,
        "source_backed_only": True,
        "no_supplier_quote_inferred": True,
        "no_exact_supplier_verification_inferred": True,
    }
    return payload
