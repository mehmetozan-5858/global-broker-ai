from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import re


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
    if provider_verified is not True:
        blockers.append("payment_provider")
    if legal_entity_verified is not True:
        blockers.append("legal_entity")
    if invoice_flow_verified is not True:
        blockers.append("invoice_flow")
    if refund_terms_reviewed is not True:
        blockers.append("refund_terms")
    if customer_terms_accepted is not True:
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
    reference = provider_reference.strip() if isinstance(provider_reference, str) else ''
    valid_reference = bool(reference and len(reference) <= 200 and not any(ord(c) < 32 or ord(c) == 127 for c in reference))
    valid_amount = bool(isinstance(amount, str) and re.fullmatch(r"[0-9]{1,12}(?:\.[0-9]{1,6})?", amount)
                        and any(c in "123456789" for c in amount))
    valid_currency = bool(isinstance(currency, str) and re.fullmatch(r"[A-Z]{3}", currency))
    confirmed = provider_verified is True and valid_reference and valid_amount and valid_currency
    return {
        "status": "confirmed" if confirmed else "unconfirmed",
        "provider_reference": reference if confirmed else None,
        "amount": amount if confirmed else None,
        "currency": currency if confirmed else None,
        "source_backed": confirmed,
    }
