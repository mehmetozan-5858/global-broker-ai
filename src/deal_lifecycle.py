"""A12 evidence-gated deal and payment lifecycle.

The lifecycle is descriptive only. It never sends messages, submits bids, signs
contracts, moves money, or marks a deal won without explicit evidence.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
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


def _audit(event: str, *, actor: str, source_reference: str | None) -> dict[str, Any]:
    return {"event": event, "actor": actor, "source_reference": source_reference, "evidence_present": True}


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


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
    """Return the furthest defensible lifecycle state and blockers.

    Access-fee payment is source-backed through ``billing_gate.payment_record`` and
    never overrides consent. Commission states reuse A11, including repeat-order
    scope and protection windows.
    """
    blockers: list[str] = []
    audit: list[dict[str, Any]] = []
    state = "match_reviewed"
    state_achieved = False

    provider_payment = payment_record(
        provider_reference=provider_reference,
        amount=provider_amount,
        currency=provider_currency,
        provider_verified=provider_verified,
    )
    effective_access = access
    if access.access_fee_required:
        effective_access = replace(access, access_paid=provider_payment["status"] == "confirmed")

    if not evidence.match_reviewed:
        blockers.append("match_review")
    else:
        state_achieved = True
        audit.append(_audit("match_reviewed", actor=evidence.actor, source_reference=evidence.source_reference))

    agreement_blockers = agreement.blockers()
    if state_achieved:
        if agreement_blockers:
            blockers.extend(x for x in agreement_blockers if x not in blockers)
        else:
            state = "terms_signed"
            audit.append(_audit("terms_signed", actor=evidence.actor, source_reference=agreement.agreement_id))

    access_decision = evaluate_access(effective_access)
    if state == "terms_signed":
        if not access_decision["allowed"]:
            blockers.extend(x for x in access_decision["missing"] if x not in blockers)
        elif not evidence.introduction_evidence:
            blockers.append("introduction_evidence")
        else:
            state = "introduced"
            audit.append(_audit("introduced", actor=evidence.actor, source_reference=evidence.source_reference))

    if state == "introduced":
        if evidence.loss_evidence:
            if not (evidence.loss_reason or "").strip():
                blockers.append("loss_reason")
            else:
                state = "lost"
                audit.append(_audit("lost", actor=evidence.actor, source_reference=evidence.source_reference))
        elif evidence.negotiation_evidence:
            state = "deal_active"
            audit.append(_audit("deal_active", actor=evidence.actor, source_reference=evidence.source_reference))
        else:
            blockers.append("negotiation_evidence")

    if state == "deal_active":
        if evidence.loss_evidence:
            if not (evidence.loss_reason or "").strip():
                blockers.append("loss_reason")
            else:
                state = "lost"
                audit.append(_audit("lost", actor=evidence.actor, source_reference=evidence.source_reference))
        elif evidence.transaction_evidence:
            state = "won"
            audit.append(_audit("won", actor=evidence.actor, source_reference=evidence.source_reference))
        else:
            blockers.append("transaction_evidence")

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
            audit.append(_audit("commission_due", actor=evidence.actor, source_reference=evidence.source_reference))
        elif evidence.payment_trigger_evidence:
            blockers.append("commission_entitlement")

    if state == "commission_due":
        if ledger["collection_recorded"]:
            state = "commission_settled"
            audit.append(_audit("commission_settled", actor=evidence.actor, source_reference=evidence.collection_reference))
        elif evidence.collection_evidence and not evidence.collection_reference:
            blockers.append("collection_reference")

    return {
        "state": state,
        "state_achieved": state_achieved,
        "states": list(STATES),
        "blockers": blockers,
        "access": access_decision,
        "provider_payment": provider_payment,
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


def process_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate explicitly structured ``deal_cases`` and attach a fail-closed summary.

    No opportunity is silently converted into a deal. Only records deliberately
    placed in ``deal_cases`` are evaluated.
    """
    cases = [x for x in (payload.get("deal_cases") or []) if isinstance(x, dict)]
    results: list[dict[str, Any]] = []
    states: Counter[str] = Counter()

    for index, case in enumerate(cases):
        try:
            agreement_data = dict(case.get("agreement") or {})
            if "signed_on" in agreement_data:
                agreement_data["signed_on"] = _as_date(agreement_data.get("signed_on"))
            agreement = AgreementRecord(**agreement_data)
            access = AccessRecord(**dict(case.get("access") or {}))
            evidence = DealEvidence(**dict(case.get("evidence") or {}))
            payment = dict(case.get("provider_payment") or {})
            result = evaluate(
                agreement=agreement,
                access=access,
                evidence=evidence,
                transaction_amount=case.get("transaction_amount"),
                transaction_date=_as_date(case.get("transaction_date")),
                repeat_transaction=bool(case.get("repeat_transaction", False)),
                provider_reference=payment.get("provider_reference"),
                provider_amount=payment.get("amount"),
                provider_currency=payment.get("currency"),
                provider_verified=payment.get("provider_verified") is True,
            )
            result["case_id"] = str(case.get("case_id") or f"deal-{index + 1}")
        except (TypeError, ValueError) as exc:
            result = {
                "case_id": str(case.get("case_id") or f"deal-{index + 1}"),
                "state": "match_reviewed",
                "state_achieved": False,
                "blockers": ["invalid_deal_case"],
                "validation_error": str(exc),
                "human_approval_required": True,
                "external_actions_allowed": False,
                "mode": "shadow",
            }
        states[result["state"]] += 1
        results.append(result)

    summary = {
        "case_count": len(results),
        "state_counts": dict(states),
        "blocked_count": sum(1 for x in results if x.get("blockers")),
        "settled_count": sum(1 for x in results if x.get("state") == "commission_settled"),
        "human_approval_required": True,
        "external_actions_enabled": False,
        "mode": "shadow",
    }
    payload["deal_lifecycle_cases"] = results
    payload["deal_lifecycle_summary"] = summary
    return summary
