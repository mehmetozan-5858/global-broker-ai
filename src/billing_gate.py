from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BillingDecision:
    status: str
    payment_allowed: bool
    invoice_required: bool
    refund_policy_required: bool
    blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "payment_allowed": self.payment_allowed,
            "invoice_required": self.invoice_required,
            "refund_policy_required": self.refund_policy_required,
            "blockers": list(self.blockers),
        }


def decide(*, provider_verified: bool, legal_entity_verified: bool, invoice_flow_verified: bool,
           refund_terms_reviewed: bool, customer_terms_accepted: bool) -> BillingDecision:
    blockers: list[str] = []
    if not provider_verified:
        blockers.append("payment_provider")
    if not legal_entity_verified:
        blockers.append("legal_entity")
    if not invoice_flow_verified:
        blockers.append("invoice_flow")
    if not refund_terms_reviewed:
        blockers.append("refund_terms")
    if not customer_terms_accepted:
        blockers.append("customer_terms")
    return BillingDecision(
        status="ready" if not blockers else "blocked",
        payment_allowed=not blockers,
        invoice_required=True,
        refund_policy_required=True,
        blockers=tuple(blockers),
    )


def payment_record(*, provider_reference: str | None, amount: str | None, currency: str | None,
                   provider_verified: bool) -> dict[str, Any]:
    """Record only externally confirmed payment facts; never fabricate paid status."""
    confirmed = bool(provider_verified and provider_reference and amount and currency)
    return {
        "status": "confirmed" if confirmed else "unconfirmed",
        "provider_reference": provider_reference if confirmed else None,
        "amount": amount if confirmed else None,
        "currency": currency if confirmed else None,
        "source_backed": confirmed,
    }
