import unittest
from datetime import date

from src.agreement_ledger import AgreementRecord, build_ledger_entry, ledger_summary


class AgreementLedgerA11Tests(unittest.TestCase):
    def agreement(self, **kw):
        base = dict(
            agreement_id="AGR-1",
            opportunity_id="OPP-1",
            payer="supplier",
            currency="USD",
            commission_rate_percent="3.0",
            protection_months=12,
            payment_trigger="buyer_payment_received",
        )
        base.update(kw)
        return AgreementRecord(**base)

    def test_unsigned_agreement_stays_proposal_only(self):
        entry = build_ledger_entry(
            self.agreement(),
            transaction_amount="100000",
            transaction_evidence=True,
            payment_trigger_evidence=True,
            collection_evidence=True,
            collection_reference="BANK-1",
        )
        self.assertEqual(entry["commission_status"], "proposal_only")
        self.assertFalse(entry["collection_recorded"])
        self.assertIn("signed_agreement", entry["agreement_blockers"])

    def test_signed_but_without_consent_does_not_activate(self):
        entry = build_ledger_entry(
            self.agreement(
                signed_on=date(2026, 10, 10),
                human_legal_review_approved=True,
                active=True,
            ),
            transaction_amount="100000",
            transaction_evidence=True,
        )
        self.assertEqual(entry["agreement_state"], "counterparty_review")
        self.assertEqual(entry["commission_status"], "proposal_only")

    def test_active_contract_can_progress_to_trigger(self):
        entry = build_ledger_entry(
            self.agreement(
                signed_on=date(2026, 10, 10),
                human_legal_review_approved=True,
                both_parties_consented=True,
                active=True,
            ),
            transaction_amount="100000",
            transaction_evidence=True,
            payment_trigger_evidence=True,
        )
        self.assertEqual(entry["agreement_state"], "active")
        self.assertEqual(entry["commission_status"], "trigger_evidenced")
        self.assertEqual(entry["commission_amount_estimate"], "3000.00")
        self.assertFalse(entry["collection_recorded"])

    def test_collection_needs_reference(self):
        agreement = self.agreement(
            signed_on=date(2026, 10, 10),
            human_legal_review_approved=True,
            both_parties_consented=True,
            active=True,
        )
        entry = build_ledger_entry(
            agreement,
            transaction_amount="100000",
            transaction_evidence=True,
            payment_trigger_evidence=True,
            collection_evidence=True,
        )
        self.assertEqual(entry["commission_status"], "trigger_evidenced")
        self.assertFalse(entry["collection_recorded"])

    def test_collection_with_reference_is_recorded(self):
        entry = build_ledger_entry(
            self.agreement(
                signed_on=date(2026, 10, 10),
                human_legal_review_approved=True,
                both_parties_consented=True,
                active=True,
            ),
            transaction_amount="100000",
            transaction_evidence=True,
            payment_trigger_evidence=True,
            collection_evidence=True,
            collection_reference="BANK-OK-123",
        )
        self.assertEqual(entry["commission_status"], "collected")
        self.assertTrue(entry["collection_recorded"])
        self.assertEqual(entry["collection_reference"], "BANK-OK-123")
        self.assertFalse(entry["external_actions_allowed"])

    def test_repeat_trade_respects_contract_scope(self):
        entry = build_ledger_entry(
            self.agreement(
                signed_on=date(2026, 10, 10),
                human_legal_review_approved=True,
                both_parties_consented=True,
                active=True,
                repeat_transactions_in_scope=False,
            ),
            transaction_amount="50000",
            transaction_date=date(2027, 1, 10),
            repeat_transaction=True,
            transaction_evidence=True,
        )
        self.assertFalse(entry["repeat_transaction_in_scope"])
        self.assertEqual(entry["commission_status"], "proposal_only")

    def test_summary_is_evidence_based(self):
        entries = [
            {"commission_status": "proposal_only", "collection_recorded": False},
            {"commission_status": "trigger_evidenced", "collection_recorded": False},
            {"commission_status": "collected", "collection_recorded": True},
        ]
        summary = ledger_summary(entries)
        self.assertEqual(summary["entry_count"], 3)
        self.assertEqual(summary["collection_recorded_count"], 1)
        self.assertFalse(summary["external_actions_enabled"])


if __name__ == "__main__":
    unittest.main()
