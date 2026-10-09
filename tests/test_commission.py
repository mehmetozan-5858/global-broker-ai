import unittest
from datetime import date
from src.commission import CommissionTerms, assess_commission, money

class CommissionTests(unittest.TestCase):
    def terms(self, **kw):
        base = dict(payer="supplier", currency="USD", proposed_rate_percent="2.5")
        base.update(kw)
        return CommissionTerms(**base)

    def test_no_agreement_never_earned(self):
        x = assess_commission(self.terms(), transaction_amount="100000", transaction_evidence=True, payment_trigger_evidence=True)
        self.assertEqual(x["status"], "proposal_only")
        self.assertEqual(x["commission_amount_estimate"], "2500.00")
        self.assertTrue(x["estimate_is_not_receivable"])

    def test_no_rate_no_fabricated_commission(self):
        x = assess_commission(self.terms(proposed_rate_percent=None), transaction_amount="100000")
        self.assertIsNone(x["commission_amount_estimate"])

    def test_signed_without_legal_review_not_approved(self):
        x = assess_commission(self.terms(signed_agreement_id="A1", agreement_signed_on=date(2026, 1, 1)), transaction_evidence=True)
        self.assertEqual(x["status"], "proposal_only")

    def test_signed_without_payment_is_not_collected(self):
        x = assess_commission(self.terms(signed_agreement_id="A1", agreement_signed_on=date(2026, 1, 1), human_legal_review_approved=True), transaction_evidence=True)
        self.assertEqual(x["status"], "transaction_evidenced")

    def test_payment_trigger_not_same_as_collection(self):
        x = assess_commission(self.terms(signed_agreement_id="A1", agreement_signed_on=date(2026, 1, 1), human_legal_review_approved=True), transaction_evidence=True, payment_trigger_evidence=True)
        self.assertEqual(x["status"], "trigger_evidenced")

    def test_collection_requires_all_evidence(self):
        x = assess_commission(self.terms(signed_agreement_id="A1", agreement_signed_on=date(2026, 1, 1), human_legal_review_approved=True), transaction_evidence=True, payment_trigger_evidence=True, collection_evidence=True)
        self.assertEqual(x["status"], "collected")
        self.assertFalse(x["external_actions_allowed"])

    def test_repeat_transaction_not_automatically_covered(self):
        x = assess_commission(self.terms(signed_agreement_id="A1", agreement_signed_on=date(2026, 1, 1), human_legal_review_approved=True), repeat_transaction=True, transaction_evidence=True)
        self.assertFalse(x["transaction_in_scope"])
        self.assertEqual(x["status"], "proposal_only")

    def test_repeat_expired_protection(self):
        t = self.terms(signed_agreement_id="A1", agreement_signed_on=date(2026, 1, 15), human_legal_review_approved=True, repeat_transactions_in_scope=True, protection_months=12)
        x = assess_commission(t, repeat_transaction=True, transaction_date=date(2027, 1, 16), transaction_evidence=True)
        self.assertFalse(x["transaction_in_scope"])

    def test_repeat_inside_protection(self):
        t = self.terms(signed_agreement_id="A1", agreement_signed_on=date(2026, 1, 15), human_legal_review_approved=True, repeat_transactions_in_scope=True, protection_months=24)
        x = assess_commission(t, repeat_transaction=True, transaction_date=date(2027, 1, 15), transaction_evidence=True)
        self.assertTrue(x["transaction_in_scope"])
        self.assertEqual(x["status"], "transaction_evidenced")

    def test_reject_invalid_protection(self):
        with self.assertRaises(ValueError):
            assess_commission(self.terms(protection_months=18))

    def test_reject_invalid_rate(self):
        with self.assertRaises(ValueError):
            assess_commission(self.terms(proposed_rate_percent="NaN"))

    def test_reject_negative_transaction(self):
        with self.assertRaises(ValueError):
            assess_commission(self.terms(), transaction_amount="-1")

if __name__ == "__main__":
    unittest.main()
