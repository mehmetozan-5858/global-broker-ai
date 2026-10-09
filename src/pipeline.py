"""Global Broker shadow CEO pipeline: traceable, non-binding commercial reviews."""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Any, Optional

from src.opportunity_quality import assess
from src.verification import buyer_is_verified
from src.matching import TradeIntent, match
from src.sales_pack import DealBrief, prepare_sales_pack
from src.commission import CommissionTerms, assess_commission

TURKEY = {"TR", "TUR", "TURKEY", "TÜRKIYE", "TÜRKİYE"}

def _country(value: str) -> str:
    return (value or "").strip().upper()

def trade_route(buyer_country: str, supplier_country: str) -> str:
    buyer_tr = _country(buyer_country) in TURKEY
    supplier_tr = _country(supplier_country) in TURKEY
    if supplier_tr and not buyer_tr:
        return "turkey_export"
    if buyer_tr and not supplier_tr:
        return "turkey_import"
    if buyer_tr and supplier_tr:
        return "domestic_turkey_review"
    if not buyer_country or not supplier_country:
        return "route_pending"
    return "third_country_brokerage"

def build_ceo_case(
    opportunity: dict[str, Any],
    *,
    seller: Optional[TradeIntent] = None,
    deal: Optional[DealBrief] = None,
    commission_terms: Optional[CommissionTerms] = None,
    today: Optional[date] = None,
) -> dict[str, Any]:
    quality = assess(opportunity, today=today)
    buyer_verified = buyer_is_verified(opportunity)
    buyer_country = str(opportunity.get("buyer-country") or "")
    buyer_name = str(opportunity.get("buyer-name") or "")
    product = str(opportunity.get("title_original") or opportunity.get("product") or "")
    opportunity_id = str(opportunity.get("publication-number") or opportunity.get("id") or "")
    source_url = str(opportunity.get("source_url") or "")
    if deal is None:
        deal = DealBrief(opportunity_id=opportunity_id, product=product,
                         buyer_company=buyer_name, buyer_country=buyer_country,
                         source_url=source_url, buyer_verified=buyer_verified)
    else:
        # Buyer identity must be verified from independent evidence, not user-set flags.
        deal = replace(deal, buyer_verified=buyer_verified)
    matching = None
    if seller is not None:
        buyer_intent = TradeIntent(id=opportunity_id, side="BUY", product=deal.product,
                                   country=deal.buyer_country,
                                   company_verified=buyer_verified)
        matching = match(buyer_intent, seller)
        # Matching never grants verification or authorization to contact.
        deal = replace(deal, supplier_verified=bool(deal.supplier_verified and seller.company_verified),
                       counterparty_contact_consent=False)
    sales = prepare_sales_pack(deal)
    commission = assess_commission(commission_terms) if commission_terms else {
        "status": "not_configured", "commission_amount_estimate": None,
        "mode": "shadow", "external_actions_allowed": False
    }
    blockers = list(sales["missing_evidence"])
    if quality["freshness_status"] == "expired":
        blockers.append("deadline_expired")
    if quality["freshness_status"] == "deadline_unknown_review":
        blockers.append("deadline_unconfirmed")
    if quality["source_link_status"] != "present_unverified":
        blockers.append("source_link_missing")
    if matching is None:
        blockers.append("supplier_matching_pending")
    elif matching["status"] == "INCOMPATIBLE":
        blockers.append("supplier_incompatible")
    else:
        blockers.extend("matching_" + str(x) for x in matching["missing"])
    if commission["status"] in ("not_configured", "proposal_only"):
        blockers.append("commission_agreement_pending")
    # A published tender is not a signed buyer mandate.
    if quality["source_type"] == "public_procurement_notice":
        blockers.append("public_tender_not_private_buyer_mandate")
    return {
        "opportunity_id": opportunity_id or None,
        "source": opportunity.get("source"),
        "source_url": source_url or None,
        "route": trade_route(deal.buyer_country, deal.supplier_country),
        "quality": quality,
        "buyer_verified": buyer_verified,
        "matching": matching,
        "sales_pack": sales,
        "commission": commission,
        "blockers": sorted(set(blockers)),
        "ceo_priority": "ARCHIVE_EXPIRED" if quality["freshness_status"] == "expired" else "HUMAN_REVIEW",
        "mode": "shadow",
        "external_actions_allowed": False,
        "contract_signature_allowed": False,
        "payment_execution_allowed": False,
    }

def ceo_summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    groups = {k: [] for k in ("turkey_export", "turkey_import", "third_country_brokerage",
                              "domestic_turkey_review", "route_pending")}
    for case in cases:
        groups.get(case.get("route"), groups["route_pending"]).append(case)
    return {
        "mode": "shadow",
        "count": len(cases),
        "groups": groups,
        "new_verified_sales": 0,  # Never infer sales from tenders or lead counts.
        "realized_commission": None,  # Requires financial evidence.
        "external_actions_allowed": False,
    }
