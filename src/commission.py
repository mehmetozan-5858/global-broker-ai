"""Shadow-mode brokerage commission planning, not an invoice or payment engine.

Rates are negotiable proposals, never inferred market facts. A commission
entitlement requires a signed agreement and evidence of a qualifying transaction.
Legal enforceability and tax treatment always require human review.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

PROTECTION_MONTHS = frozenset((12, 24, 36))
PAYMENT_TRIGGERS = frozenset(("buyer_payment_received", "supplier_payment_received", "invoice_paid"))
STATUSES = frozenset(("proposal_only", "agreement_signed", "transaction_evidenced", "trigger_evidenced", "collected"))

def money(value: str | int | Decimal) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("invalid monetary amount") from None
    if not amount.is_finite() or amount < 0:
        raise ValueError("amount must be finite and nonnegative")
    return amount

@dataclass(frozen=True)
class CommissionTerms:
    payer: str
    currency: str
    proposed_rate_percent: Optional[str] = None
    protection_months: int = 12
    payment_trigger: str = "buyer_payment_received"
    first_transaction_in_scope: bool = True
    repeat_transactions_in_scope: bool = False
    non_circumvention_proposed: bool = True
    signed_agreement_id: str = ""
    agreement_signed_on: Optional[date] = None
    human_legal_review_approved: bool = False

    def validate(self) -> None:
        if self.protection_months not in PROTECTION_MONTHS:
            raise ValueError("protection must be 12, 24, or 36 months")
        if self.payment_trigger not in PAYMENT_TRIGGERS:
            raise ValueError("unsupported payment trigger")
        if not self.payer.strip() or not self.currency.strip():
            raise ValueError("payer and currency required")
        if self.proposed_rate_percent is not None:
            rate = money(self.proposed_rate_percent)
            if rate > 100:
                raise ValueError("rate cannot exceed 100 percent")
        if bool(self.signed_agreement_id) != bool(self.agreement_signed_on):
            raise ValueError("signed agreement ID and signing date must be provided together")

def assess_commission(
    terms: CommissionTerms,
    *,
    transaction_amount: Optional[str] = None,
    repeat_transaction: bool = False,
    transaction_evidence: bool = False,
    payment_trigger_evidence: bool = False,
    collection_evidence: bool = False,
    transaction_date: Optional[date] = None,
) -> dict:
    terms.validate()
    signed = bool(terms.signed_agreement_id and terms.agreement_signed_on)
    in_scope = terms.repeat_transactions_in_scope if repeat_transaction else terms.first_transaction_in_scope
    if signed and transaction_date and transaction_date < terms.agreement_signed_on:
        in_scope = False
    if repeat_transaction and (not signed or transaction_date is None):
        in_scope = False  # Never assume protection without a dated qualifying repeat sale.
    if repeat_transaction and signed and transaction_date:
        months = (transaction_date.year - terms.agreement_signed_on.year) * 12 + transaction_date.month - terms.agreement_signed_on.month
        if months > terms.protection_months or (months == terms.protection_months and transaction_date.day > terms.agreement_signed_on.day):
            in_scope = False
    rate = money(terms.proposed_rate_percent) if terms.proposed_rate_percent is not None else None
    amount = money(transaction_amount) if transaction_amount is not None else None
    indicative = str((amount * rate / Decimal("100")).quantize(Decimal("0.01"))) if amount is not None and rate is not None else None
    if not signed or not terms.human_legal_review_approved or not in_scope:
        status = "proposal_only"
    elif not transaction_evidence:
        status = "agreement_signed"
    elif not payment_trigger_evidence:
        status = "transaction_evidenced"
    elif not collection_evidence:
        status = "trigger_evidenced"
    else:
        status = "collected"
    return {
        "status": status,
        "commission_amount_estimate": indicative,
        "estimate_is_not_receivable": True,
        "rate_basis": "negotiable_proposal_not_market_benchmark",
        "payer": terms.payer,
        "currency": terms.currency,
        "protection_months": terms.protection_months,
        "repeat_transaction": repeat_transaction,
        "repeat_transactions_contractually_in_scope": terms.repeat_transactions_in_scope,
        "transaction_in_scope": in_scope,
        "payment_trigger": terms.payment_trigger,
        "agreement_signed": signed,
        "legal_review_approved": terms.human_legal_review_approved,
        "payment_trigger_evidenced": payment_trigger_evidence,
        "collection_evidenced": collection_evidence,
        "non_circumvention_requires_legal_review": terms.non_circumvention_proposed,
        "mode": "shadow",
        "external_actions_allowed": False,
    }
