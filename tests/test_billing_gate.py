import unittest
from src.billing_gate import decide, payment_record


class BillingGateTests(unittest.TestCase):
    def record(self, **changes):
        args = dict(provider_reference='PAY-FIXTURE', amount='100.50', currency='USD', provider_verified=True)
        args.update(changes)
        return payment_record(**args)

    def test_exact_provider_confirmation_and_positive_amount_are_required(self):
        self.assertEqual(self.record()['status'], 'confirmed')
        for flag in [False, None, 'true', 'false', 1, {}, []]:
            self.assertEqual(self.record(provider_verified=flag)['status'], 'unconfirmed')
        for value in ['0', '0.000000', '-100', 'NaN', 'Infinity', '1e2', '1,50', '', ' 100 ', '1000000000000', '1.0000001', None, 100, True]:
            result = self.record(amount=value)
            self.assertFalse(result['source_backed'], repr(value))
            self.assertTrue(all(result[k] is None for k in ['provider_reference','amount','currency']))
        for value in ['0.000001', '999999999999.999999']:
            self.assertEqual(self.record(amount=value)['status'], 'confirmed')

    def test_invalid_reference_or_currency_cannot_open_paid_access(self):
        for reference in ['', '  ', 'x'*201, 'PAY\nINJECT', None, True]:
            self.assertEqual(self.record(provider_reference=reference)['status'], 'unconfirmed')
        for currency in ['', 'usd', 'US', 'USDT', '123', 'USD ', None, True]:
            self.assertEqual(self.record(currency=currency)['status'], 'unconfirmed')
        self.assertEqual(self.record(provider_reference=' PAY-FIXTURE ')['provider_reference'], 'PAY-FIXTURE')

    def test_business_acceptance_flags_require_literal_true(self):
        args = dict(provider_verified=True, legal_entity_verified=True, invoice_flow_verified=True,
                    refund_terms_reviewed=True, customer_terms_accepted=True)
        self.assertTrue(decide(**args).payment_allowed)
        for name in args:
            for value in ['true', 'false', 1, None, False]:
                self.assertFalse(decide(**dict(args, **{name:value})).payment_allowed, name)
