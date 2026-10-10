import unittest
from datetime import date

from src.access_control import AccessRecord
from src.agreement_ledger import AgreementRecord
from src.deal_lifecycle import DealEvidence, evaluate


class DealLifecycleA12Tests(unittest.TestCase):
    def agreement(self, **overrides):
        values = dict(
            agreement_id="AGR-1",
            opportunity_id="OPP-1",
            payer="buyer",
            currency="USD",
            commission_rate_percent="4",
            protection_months=12,
            payment_trigger="buyer_payment_received",
            repeat_transactions_in_scope=True,
            signed_on=date(2026, 1, 1),
            human_legal_review_approved=True,
            both_parties_consented=True,
            active=True,
        )
        values.update(overrides)
        return AgreementRecord(**values)

    def access(self, **overrides):
        values = dict(
            authenticated=True,
            party_verified=True,
            buyer_consent=True,
            seller_consent=True,
            terms_signed=True,
            access_fee_required=False,
            access_paid=False,
        )
        values.update(overrides)
        return AccessRecord(**values)

    def evidence(self, **overrides):
        values = dict(
            match_reviewed=True,
            introduction_evidence=True,
            negotiation_evidence=True,
            transaction_evidence=True,
            payment_trigger_evidence=False,
            collection_evidence=False,
            actor="reviewer-1",
            source_reference="DOC-1",
        )
        values.update(overrides)
        return DealEvidence(**values)

    def test_missing_match_review_cannot_skip_to_signed_terms(self):
        result = evaluate(agreement=self.agreement(), access=self.access(), evidence=self.evidence(match_reviewed=False))
        self.assertEqual(result["state"], "match_reviewed")
        self.assertFalse(result["state_achieved"])
        self.assertIn("match_review", result["blockers"])

    def test_access_fee_requires_source_backed_provider_payment(self):
        access = self.access(access_fee_required=True, access_paid=True)
        result = evaluate(agreement=self.agreement(), access=access, evidence=self.evidence())
        self.assertEqual(result["state"], "terms_signed")
        self.assertEqual(result["provider_payment"]["status"], "unconfirmed")
        self.assertIn("confirmed_access_payment", result["blockers"])

    def test_confirmed_payment_never_overrides_missing_consent(self):
        access = self.access(access_fee_required=True, buyer_consent=False)
        result = evaluate(
            agreement=self.agreement(), access=access, evidence=self.evidence(),
            provider_reference="PAY-1", provider_amount="100", provider_currency="USD", provider_verified=True,
        )
        self.assertEqual(result["provider_payment"]["status"], "confirmed")
        self.assertEqual(result["state"], "terms_signed")
        self.assertIn("buyer_consent", result["blockers"])

    def test_deal_cannot_be_won_without_transaction_evidence(self):
        result = evaluate(agreement=self.agreement(), access=self.access(), evidence=self.evidence(transaction_evidence=False))
        self.assertEqual(result["state"], "deal_active")
        self.assertIn("transaction_evidence", result["blockers"])

    def test_loss_requires_explicit_reason(self):
        result = evaluate(
            agreement=self.agreement(), access=self.access(),
            evidence=self.evidence(transaction_evidence=False, loss_evidence=True, loss_reason=None),
        )
        self.assertEqual(result["state"], "introduced")
        self.assertIn("loss_reason", result["blockers"])

    def test_won_does_not_mean_commission_due_without_trigger(self):
        result = evaluate(
            agreement=self.agreement(), access=self.access(), evidence=self.evidence(),
            transaction_amount="10000", transaction_date=date(2026, 3, 1),
        )
        self.assertEqual(result["state"], "won")
        self.assertEqual(result["commission_ledger"]["commission_status"], "transaction_evidenced")

    def test_payment_trigger_moves_evidenced_win_to_commission_due(self):
        result = evaluate(
            agreement=self.agreement(), access=self.access(),
            evidence=self.evidence(payment_trigger_evidence=True),
            transaction_amount="10000", transaction_date=date(2026, 3, 1),
        )
        self.assertEqual(result["state"], "commission_due")
        self.assertEqual(result["commission_ledger"]["commission_status"], "trigger_evidenced")

    def test_collection_requires_reference(self):
        result = evaluate(
            agreement=self.agreement(), access=self.access(),
            evidence=self.evidence(payment_trigger_evidence=True, collection_evidence=True),
            transaction_amount="10000", transaction_date=date(2026, 3, 1),
        )
        self.assertEqual(result["state"], "commission_due")
        self.assertIn("collection_reference", result["blockers"])
        self.assertFalse(result["commission_ledger"]["collection_recorded"])

    def test_full_evidence_path_can_record_commission_settled(self):
        result = evaluate(
            agreement=self.agreement(), access=self.access(),
            evidence=self.evidence(payment_trigger_evidence=True, collection_evidence=True, collection_reference="COL-9"),
            transaction_amount="10000", transaction_date=date(2026, 3, 1),
        )
        self.assertEqual(result["state"], "commission_settled")
        self.assertTrue(result["commission_ledger"]["collection_recorded"])
        self.assertFalse(result["external_actions_allowed"])
        self.assertTrue(result["human_approval_required"])

    def test_repeat_order_outside_protection_never_creates_commission_due(self):
        result = evaluate(
            agreement=self.agreement(), access=self.access(),
            evidence=self.evidence(payment_trigger_evidence=True),
            transaction_amount="10000", transaction_date=date(2027, 2, 2), repeat_transaction=True,
        )
        self.assertEqual(result["state"], "won")
        self.assertFalse(result["commission_ledger"]["repeat_transaction_in_scope"])
        self.assertIn("commission_entitlement", result["blockers"])


if __name__ == "__main__":
    unittest.main()
