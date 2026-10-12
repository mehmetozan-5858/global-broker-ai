"""Curated, source-backed evidence overlays for pilot commercial dossiers.

These records are intentionally narrow and fail closed. They may add authoritative
buyer corroboration and research leads, but they do not invent quantity, technical
specifications, prices or supplier verification.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

EVIDENCE: dict[str, dict[str, Any]] = {
    "saudi-etimad-261039003553": {
        "buyer_registry_evidence": [
            {
                "authority": "official_institution_directory",
                "url": "https://my.gov.sa/en/agencies/17348",
                "buyer_name": "الهيئة السعودية للمياه",
                "name_match": True,
                "country_match": True,
                "note": "Saudi National Platform lists Saudi Water Authority as a government agency.",
            },
            {
                "authority": "public_entity_registry",
                "url": "https://swa.gov.sa/",
                "buyer_name": "الهيئة السعودية للمياه",
                "name_match": True,
                "country_match": True,
                "note": "Official Saudi Water Authority government domain.",
            },
        ],
        "stage4_research": {
            "status": "blocked_pending_full_tender_documents",
            "researched_at": "2026-10-12",
            "tender_reference": "261039003553",
            "competition_number": "60021318",
            "product_scope": "Low-voltage electrical cable/spare parts for Al-Busaita purification plant, western coast",
            "quantity_status": "not_found_in_current_public_notice",
            "price_status": "not_quoted",
            "document_access_gate": {
                "status": "full_tender_document_required",
                "public_notice_has_exact_spec": False,
                "public_notice_has_quantity": False,
                "public_notice_document_fee_sar": "200.00",
                "payment_authorized": False,
                "external_purchase_required": True,
                "reason": "Public notice exposes category-level cable demand but not the exact conductor/core/cross-section/armour specification or lot quantity. Do not price until tender documents are obtained.",
                "resolution": "Obtain the official Etimad tender package through an authorized access path before exact supplier matching or quote acceptance.",
            },
            "supplier_leads": [
                {
                    "name": "Saudi Cable Company",
                    "url": "https://www.saudicable.com/en/products/electric-cables/index.html",
                    "status": "category_match_verified_exact_spec_pending",
                    "identity_evidence": "Official manufacturer product site.",
                    "product_evidence": "0.6/1 kV low-voltage power cables; Cu/Al; PVC/XLPE; armored or unarmored; IEC/BS standards listed.",
                    "independent_qualification": None,
                },
                {
                    "name": "Riyadh Cables",
                    "url": "https://riyadh-cables.com/products/",
                    "status": "category_match_independently_qualified_exact_spec_pending",
                    "identity_evidence": "Official manufacturer website and Riyadh manufacturing address.",
                    "product_evidence": "Official catalogue includes Low Voltage Cables (LV) product family.",
                    "independent_qualification": {
                        "authority": "Saudi Electricity Company",
                        "url": "https://www.se.com.sa/-/media/sec/Our-Partners/Our-Suppliers/LIST-OF-QUALIFIED-MANUFACTURERS-SUPPLIERSS---March-2026.ashx",
                        "scope": "LV Power cables",
                        "specification": "11-SDMS-01",
                        "effective_list": "March 2026",
                        "note": "Independent industry qualification confirms LV cable manufacturing capability; it does not prove compliance with this Saudi Water Authority tender.",
                    },
                },
                {
                    "name": "Pamukkale Kablo",
                    "url": "https://www.pk.com.tr/en/Urunler.aspx",
                    "status": "category_match_independently_certified_exact_spec_pending",
                    "identity_evidence": "Official manufacturer site identifies Denizli factory and export sales channel.",
                    "product_evidence": "Official catalogue lists PVC/XLPE/HFFR low-voltage cables and export capability.",
                    "independent_qualification": {
                        "authority": "BASEC / TSE",
                        "url": "https://www.basec.org.uk/customers/a1700/",
                        "scope": "Low-voltage building wires and armoured power cables up to 1 kV; manufacturer certifications",
                        "note": "Independent certification supports manufacturing capability only; exact tender specification remains pending.",
                    },
                },
                {
                    "name": "Jeddah Cables",
                    "url": "https://www.se.com.sa/-/media/sec/Our-Partners/Our-Suppliers/LIST-OF-QUALIFIED-MANUFACTURERS-SUPPLIERSS---March-2026.ashx",
                    "status": "independent_lv_qualification_exact_spec_pending",
                    "identity_evidence": "Saudi Electricity Company prequalified manufacturer list.",
                    "product_evidence": "Listed for LV Power cables, specification 11-SDMS-01.",
                    "independent_qualification": {
                        "authority": "Saudi Electricity Company",
                        "scope": "LV Power cables",
                        "specification": "11-SDMS-01",
                        "effective_list": "March 2026",
                    },
                },
                {
                    "name": "DUCAB",
                    "url": "https://www.se.com.sa/-/media/sec/Our-Partners/Our-Suppliers/LIST-OF-QUALIFIED-MANUFACTURERS-SUPPLIERSS---March-2026.ashx",
                    "status": "independent_lv_qualification_exact_spec_pending",
                    "identity_evidence": "Saudi Electricity Company prequalified manufacturer list.",
                    "product_evidence": "Listed for LV Power cables, specification 11-SDMS-01.",
                    "independent_qualification": {
                        "authority": "Saudi Electricity Company",
                        "scope": "LV Power cables",
                        "specification": "11-SDMS-01",
                        "effective_list": "March 2026",
                    },
                },
                {
                    "name": "Bahra Cables",
                    "url": "https://www.se.com.sa/-/media/sec/Our-Partners/Our-Suppliers/LIST-OF-QUALIFIED-MANUFACTURERS-SUPPLIERSS---March-2026.ashx",
                    "status": "independent_lv_qualification_exact_spec_pending",
                    "identity_evidence": "Saudi Electricity Company prequalified manufacturer list.",
                    "product_evidence": "Appears in Saudi Electricity Company cable manufacturer qualification lists; exact SWA tender match remains unproven.",
                    "independent_qualification": {
                        "authority": "Saudi Electricity Company",
                        "scope": "cable manufacturer qualification",
                        "effective_list": "March 2026",
                    },
                },
            ],
            "next_required_evidence": [
                "exact cable technical specification from full tender documents",
                "quantity/lot size from full tender documents",
                "exact-spec supplier match",
                "source-backed supplier quote with currency and validity",
            ],
            "rule": "Category-level product evidence and third-party industry qualification do not count as exact supplier verification until the tender specification and quantity are available.",
        },
    }
}


def apply(payload: dict[str, Any]) -> dict[str, Any]:
    applied = 0
    blocked_docs = 0
    for row in payload.get("opportunities") or []:
        if not isinstance(row, dict):
            continue
        oid = row.get("opportunity_id") or row.get("id")
        overlay = EVIDENCE.get(str(oid))
        if not overlay:
            continue
        for key, value in overlay.items():
            row[key] = value
        gate = (row.get("stage4_research") or {}).get("document_access_gate") or {}
        if gate.get("status") == "full_tender_document_required":
            blocked_docs += 1
        applied += 1
    payload["pilot_evidence_summary"] = {
        "applied": applied,
        "blocked_by_tender_document_access": blocked_docs,
        "source_backed_only": True,
        "no_price_or_quantity_inference": True,
    }
    return payload


def main(path: str) -> None:
    target = Path(path)
    payload = json.loads(target.read_text(encoding="utf-8"))
    apply(payload)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PILOT_EVIDENCE applied={payload['pilot_evidence_summary']['applied']}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.pilot_evidence <payload.json>")
    main(sys.argv[1])
