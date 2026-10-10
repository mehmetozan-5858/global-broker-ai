"""A12 evidence-gated deal and payment lifecycle.

The lifecycle is descriptive only. It never sends messages, submits bids, signs
contracts, moves money, or marks a deal won without explicit evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from src.access_control import AccessRecord, evaluate_access
from src.agreement_ledger import AgreementRecord, build_ledger_entry
from src.billing_gate import payment_record

STATES = (
    "match_reviewed",
    "terms_signed",
    "introduced",
    "deal_active",
    "won",
    "lost",
    "commission_due",
    "commission_settled",
)


@dataclass(frozen=True)
class DealEvidence:
    match_reviewed: bool = False
    introduction_evidence: bool = False
    negotiation_evidence: bool = False
    transaction_evidence: bool = False
    loss_evidence: bool = False
    loss_reason: str | None = None
    payment_trigger_evidence: bool = False
    collection_evidence: bool = False
    collection_reference: str | None = None
    actor: str = "system"
    source_reference: str | None = None


def _audit(event: str, *, actor: str, source_reference: str | None, evidence: bool) -> dict[str, Any]:
    return {
        "event": event,
        "actor": actor,
        "source_reference": source_reference,
        "evidence_present": bool(evidence),
    }


def evaluate(
    *,
    agreement: AgreementRecord,
    access: AccessRecord,
    evidence: DealEvidence,
    transaction_amount: str | None = None,
    transaction_date: date | None = None,
    repeat_transaction: bool = False,
    provider_reference: str | None = None,
    provider_amount: str | None = None,
    provider_currency: str | None = None,
    provider_verified: bool = False,
) -> dict[str, Any]:
    """Return the furthest defensible lifecycle state and its blockers.

    Payment confirmation never overrides access/consent gates. ``won`` requires
    transaction evidence; ``lost`` requires explicit closure evidence. Commission
    states reuse the A11 agreement/commission engine and therefore respect repeat
    transaction protection windows.
    """
    blockers: list[str] = []
    audit: list[dict[str, Any]] = []

    if not evidence.match_reviewed:
        blockers.append("match_review")
        state = "match_reviewed"
    else:
        state = "match_reviewed"
        audit.append(_audit("match_reviewed", actor=evidence.actor, source_reference=evidence.source_reference, evidence=True))

    agreement_blockers = agreement.blockers()
    if agreement_blockers:
        blockers.extend(x for x in agreement_blockers if x not in blockers)
    else:
        state = "terms_signed"
        audit.append(_audit("terms_signed", actor=evidence.actor, source_reference=agreement.agreement_id, evidence=True))

    access_decision = evaluate_access(access)
    if not access_decision["allowed"]:
        blockers.extend(x for x in access_decision["missing"] if x not in blockers)
    elif not evidence.introduction_evidence:
        blockers.append("introduction_evidence")
    else:
        state = "introduced"
        audit.append(_audit("introduced", actor=evidence.actor, source_reference=evidence.source_reference, evidence=True))

    if state == "introduced":
        if evidence.negotiation_evidence:
            state = "deal_active"
            audit.append(_audit("deal_active", actor=evidence.actor, source_reference=evidence.source_reference, evidence=True))
        else:
            blockers.append("negotiation_evidence")

    if evidence.loss_evidence:
        if not (evidence.loss_reason or "").strip():
            blockers.append("loss_reason")
        elif state in ("introduced", "deal_active"):
            state = "lost"
            audit.append(_audit("lost", actor=evidence.actor, source_reference=evidence.source_reference, evidence=True))

    if state == "deal_active" and evidence.transaction_evidence:
        state = "won"
        audit.append(_audit("won", actor=evidence.actor, source_reference=evidence.source_reference, evidence=True))
    elif state == "deal_active" and not evidence.loss_evidence:
        blockers.append("transaction_evidence")

    payment = payment_record(
        provider_reference=provider_reference,
        amount=provider_amount,
        currency=provider_currency,
        provider_verified=provider_verified,
    )

    ledger = build_ledger_entry(
        agreement,
        transaction_amount=transaction_amount,
        transaction_date=transaction_date,
        repeat_transaction=repeat_transaction,
        transaction_evidence=evidence.transaction_evidence,
        payment_trigger_evidence=evidence.payment_trigger_evidence,
        collection_evidence=evidence.collection_evidence,
        collection_reference=evidence.collection_reference,
    )

    if state == "won":
        if ledger["commission_status"] in ("trigger_evidenced", "collected"):
            state = "commission_due"
            audit.append(_audit("commission_due", actor=evidence.actor, source_reference=evidence.source_reference, evidence=True))
        elif evidence.payment_trigger_evidence:
            blockers.append("commission_entitlement")

    if state == "commission_due":
        if ledger["collection_recorded"]:
            state = "commission_settled"
            audit.append(_audit("commission_settled", actor=evidence.actor, source_reference=evidence.collection_reference, evidence=True))
        elif evidence.collection_evidence and not evidence.collection_reference:
            blockers.append("collection_reference")

    return {
        "state": state,
        "states": list(STATES),
        "blockers": blockers,
        "access": access_decision,
        "provider_payment": payment,
        "commission_ledger": ledger,
        "audit": audit,
        "repeat_transaction": repeat_transaction,
        "human_approval_required": True,
        "external_actions_allowed": False,
        "mode": "shadow",
        "policy": {
            "send_message": False,
            "submit_offer": False,
            "submit_order": False,
            "sign_contract": False,
            "initiate_payment": False,
            "mark_won_without_evidence": False,
        },
    }
