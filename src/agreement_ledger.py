"""A11 agreement and commission ledger controls.

This module records contract-backed brokerage state only. It does not sign contracts,
send invoices, move money, or infer commission entitlement without evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from src.commission import CommissionTerms, assess_commission

AGREEMENT_STATES = (
    "draft",
    "counterparty_review",
    "signed",
    "active",
    "expired",
)

LEDGER_STATES = (
    "proposal_only",
    "agreement_signed",
    "transaction_evidenced",
    "trigger_evidenced",
    "collected",
)


@dataclass(frozen=True)
class AgreementRecord:
    agreement_id: str
    opportunity_id: str
    payer: str
    currency: str
    commission_rate_percent: str | None
    protection_months: int
    payment_trigger: str
    repeat_transactions_in_scope: bool = False
    signed_on: date | None = None
    human_legal_review_approved: bool = False
    both_parties_consented: bool = False
    active: bool = False

    def blockers(self) -> list[str]:
        blockers: list[str] = []
        if not self.agreement_id.strip():
            blockers.append("agreement_id")
        if not self.opportunity_id.strip():
            blockers.append("opportunity_id")
        if self.signed_on is None:
            blockers.append("signed_agreement")
        if not self.human_legal_review_approved:
            blockers.append("legal_review")
        if not self.both_parties_consented:
            blockers.append("counterparty_consent")
        if not self.active:
            blockers.append("agreement_active")
        return blockers

    def state(self) -> str:
        if self.signed_on is None:
            return "draft"
        if not self.human_legal_review_approved or not self.both_parties_consented:
            return "counterparty_review"
        return "active" if self.active else "signed"


def build_ledger_entry(
    agreement: AgreementRecord,
    *,
    transaction_amount: str | None = None,
    transaction_date: date | None = None,
    repeat_transaction: bool = False,
    transaction_evidence: bool = False,
    payment_trigger_evidence: bool = False,
    collection_evidence: bool = False,
    collection_reference: str | None = None,
) -> dict[str, Any]:
    """Build an evidence-gated commission ledger entry.

    Collection is only recorded when the commission engine reaches ``collected`` and
    a concrete collection reference is supplied. External actions always remain off.
    """
    terms = CommissionTerms(
        payer=agreement.payer,
        currency=agreement.currency,
        proposed_rate_percent=agreement.commission_rate_percent,
        protection_months=agreement.protection_months,
        payment_trigger=agreement.payment_trigger,
        repeat_transactions_in_scope=agreement.repeat_transactions_in_scope,
        signed_agreement_id=agreement.agreement_id if agreement.signed_on else "",
        agreement_signed_on=agreement.signed_on,
        human_legal_review_approved=agreement.human_legal_review_approved,
    )
    assessment = assess_commission(
        terms,
        transaction_amount=transaction_amount,
        repeat_transaction=repeat_transaction,
        transaction_evidence=transaction_evidence,
        payment_trigger_evidence=payment_trigger_evidence,
        collection_evidence=collection_evidence,
        transaction_date=transaction_date,
    )

    agreement_blockers = agreement.blockers()
    if agreement_blockers and assessment["status"] != "proposal_only":
        assessment["status"] = "proposal_only"

    collected = assessment["status"] == "collected" and bool(collection_reference)
    if assessment["status"] == "collected" and not collection_reference:
        assessment["status"] = "trigger_evidenced"

    return {
        "agreement_id": agreement.agreement_id,
        "opportunity_id": agreement.opportunity_id,
        "agreement_state": agreement.state(),
        "agreement_blockers": agreement_blockers,
        "commission_status": assessment["status"],
        "commission_amount_estimate": assessment["commission_amount_estimate"],
        "estimate_is_not_receivable": assessment["status"] not in ("trigger_evidenced", "collected"),
        "payer": agreement.payer,
        "currency": agreement.currency,
        "payment_trigger": agreement.payment_trigger,
        "repeat_transaction": repeat_transaction,
        "repeat_transaction_in_scope": assessment["transaction_in_scope"],
        "protection_months": agreement.protection_months,
        "collection_recorded": collected,
        "collection_reference": collection_reference if collected else None,
        "human_approval_required": True,
        "external_actions_allowed": False,
        "mode": "shadow",
    }


def ledger_summary(entries: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {state: 0 for state in LEDGER_STATES}
    collected_count = 0
    for entry in entries:
        state = str(entry.get("commission_status") or "proposal_only")
        if state not in counts:
            state = "proposal_only"
        counts[state] += 1
        if entry.get("collection_recorded"):
            collected_count += 1
    return {
        "entry_count": len(entries),
        "status_counts": counts,
        "collection_recorded_count": collected_count,
        "external_actions_enabled": False,
        "human_approval_required": True,
    }
