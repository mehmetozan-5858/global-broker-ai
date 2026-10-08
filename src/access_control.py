"""Server-side access gates for the Global Broker private data room.

This module is deliberately fail-closed. Authentication, verification, mutual
consent, signed brokerage terms and (when required) confirmed access payment
are independent gates. Payment can never override missing consent.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AccessRecord:
    authenticated: bool = False
    party_verified: bool = False
    buyer_consent: bool = False
    seller_consent: bool = False
    terms_signed: bool = False
    access_fee_required: bool = False
    access_paid: bool = False


def evaluate_access(record: AccessRecord) -> dict[str, Any]:
    missing: list[str] = []
    if not record.authenticated:
        missing.append("authentication")
    if not record.party_verified:
        missing.append("party_verification")
    if not record.buyer_consent:
        missing.append("buyer_consent")
    if not record.seller_consent:
        missing.append("seller_consent")
    if not record.terms_signed:
        missing.append("signed_brokerage_terms")
    if record.access_fee_required and not record.access_paid:
        missing.append("confirmed_access_payment")

    allowed = not missing
    return {
        "allowed": allowed,
        "status": "INTRODUCTION_ALLOWED" if allowed else "ACCESS_BLOCKED",
        "missing": missing,
        "can_reveal_contacts": allowed,
        "payment_overrides_consent": False,
    }


def public_view(opportunity: dict[str, Any]) -> dict[str, Any]:
    """Return only fields safe for an unauthenticated/public teaser."""
    allowed = {
        "id", "title_tr", "title_original", "categories", "market_region",
        "buyer-country", "source", "source_url", "generated", "scope",
        "opportunity_type", "commercial_priority", "scale_status",
    }
    return {k: v for k, v in opportunity.items() if k in allowed}


def private_view(opportunity: dict[str, Any], record: AccessRecord) -> dict[str, Any]:
    decision = evaluate_access(record)
    if not decision["allowed"]:
        return {"access": decision, "opportunity": public_view(opportunity)}
    return {"access": decision, "opportunity": dict(opportunity)}
