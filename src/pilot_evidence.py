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
            "document_access": {
                "status": "full_document_not_publicly_retrieved",
                "public_notice_confirms_document_fee_sar": "200.00",
                "automated_spec_extraction_allowed": False,
                "reason": "Current public/visitor evidence does not expose the exact cable specification or quantity. Do not infer either from the title.",
                "resolution": "Obtain the official Etimad tender package through an authorized access path before exact supplier matching or quote acceptance.",
            },
            "supplier_leads": [
                {
                    "name": "Saudi Cable Company",
                    "url": "https://www.saudicable.com/en/products/electric-cables/index.html",
                    "status": "category_match_verified_exact_spec_pending",
                    "identity_evidence": "Official manufacturer product site.",
                    "product_evidence": "0.6/1 kV low-voltage power cables; Cu/Al; PVC/XLPE; armored or unarmored; IEC/BS standards listed.",
                },
                {
                    "name": "Riyadh Cables",
                    "url": "https://riyadh-cables.com/products/",
                    "status": "category_match_verified_exact_spec_pending",
                    "identity_evidence": "Official manufacturer website and Riyadh manufacturing address.",
                    "product_evidence": "Official catalogue includes Low Voltage Cables (LV) product family.",
                },
                {
                    "name": "Pamukkale Kablo",
                    "url": "https://www.pk.com.tr/en/Urunler.aspx?Id=13",
                    "status": "category_match_verified_exact_spec_pending",
                    "identity_evidence": "Official manufacturer site identifies Denizli factory and export sales channel.",
                    "product_evidence": "Official catalogue lists XLPE insulated low-voltage cables including BS 5467 variants.",
                },
            ],
            "next_required_evidence": [
                "exact cable technical specification from official tender documents",
                "quantity/lot size",
                "exact-spec supplier match",
                "source-backed supplier quote with currency and validity",
            ],
            "rule": "Category-level product evidence does not count as exact supplier verification until tender specification and quantity are available.",
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
        research = row.get("stage4_research") or {}
        if (research.get("document_access") or {}).get("status") == "full_document_not_publicly_retrieved":
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
