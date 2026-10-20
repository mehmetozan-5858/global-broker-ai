import copy
from datetime import date
from decimal import Decimal
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from src.quote_review_analysis import analyze
from api.quote_analysis import preview


class QuoteReviewAnalysisTests(unittest.TestCase):
    def context(self, eligible=True):
        quote = {'party': 'supplier', 'counterparty': 'Fixture Maker', 'amount': '12.50', 'currency': 'USD',
            'source_url': 'https://example.invalid/quote', 'reference': 'FIXTURE', 'quote_date': '2026-10-19',
            'valid_until': '2026-11-01', 'quantity': '100', 'price_unit': 'piece'}
        review = {'decision': 'accepted_for_analysis', 'checks': {k: True for k in ('source_reviewed', 'identity_scope_checked', 'price_quantity_currency_checked')}}
        return {'opportunity': {'id': 'fixture', 'quantity': '100', 'supplier_research': {'candidate_suppliers': [
            {'name': 'Fixture Maker', 'verified': True, 'financial_evidence_eligible': eligible}]}},
            'quotes': [{'quote': quote, 'review': review}, {'quote': dict(quote, party='buyer', counterparty='Fixture Buyer', amount='18'), 'review': review}]}

    def test_reviewed_quotes_can_reach_analysis_without_persisting_or_approving(self):
        context = self.context(); original = copy.deepcopy(context)
        result = analyze(context, date(2026, 10, 20))
        self.assertTrue(result['price_gate']['margin_ready'])
        self.assertEqual(result['price_gate']['gross_product_spread'], '550.00')
        self.assertFalse(result['commercial_approval']); self.assertFalse(result['persisted_prices'])
        self.assertEqual(context, original)

    def test_capability_only_supplier_stays_blocked_after_human_document_review(self):
        result = analyze(self.context(False), date(2026, 10, 20))
        self.assertFalse(result['price_gate']['price_ready'])
        self.assertIn('financially_eligible_exact_spec_supplier', result['price_gate']['missing_or_invalid'])

    def test_revoked_or_unchecked_review_cannot_reuse_stale_verified_fields(self):
        for decision in ('rejected', 'needs_information'):
            context = self.context(); context['quotes'][0]['review'] = {'decision': decision}
            context['opportunity'].update(verified_unit_price='99', quote_currency='USD', quote_valid_until='2099-12-31')
            self.assertFalse(analyze(context, date(2026, 10, 20))['price_gate']['price_ready'])

    def test_duplicate_accepted_quotes_are_not_resolved_by_first_match(self):
        context = self.context(); context['quotes'].append(copy.deepcopy(context['quotes'][0]))
        result = analyze(context, date(2026, 10, 20))
        self.assertEqual(result['ambiguous_parties'], ['supplier'])
        self.assertFalse(result['price_gate']['price_ready'])

    def test_expired_buy_or_sell_is_excluded(self):
        for index in (0, 1):
            context = self.context(); context['quotes'][index]['quote']['valid_until'] = '2026-10-19'
            result = analyze(context, date(2026, 10, 20))
            self.assertFalse(result['price_gate']['margin_ready'])
            self.assertEqual(result['excluded']['expired_or_invalid'], 1)

    def test_api_forwards_user_token_and_retains_sql_authorization_denial(self):
        for status in (401, 403):
            with patch('api.quote_analysis.urlopen', side_effect=HTTPError('https://example.invalid', status, 'denied', {}, None)) as fetch:
                result = preview('synthetic-token', 'fixture')
                self.assertEqual(result[0], status)
                request = fetch.call_args.args[0]
                self.assertEqual(request.headers['Authorization'], 'Bearer synthetic-token')
                self.assertNotIn('synthetic-token', request.full_url)

    def test_mismatched_quote_quantities_or_units_never_produce_a_spread(self):
        for field, value in [('quantity', '50'), ('price_unit', 'kg')]:
            context = self.context(); context['quotes'][1]['quote'][field] = value
            result = analyze(context, date(2026, 10, 20))
            self.assertFalse(result['price_gate']['margin_ready'])
            self.assertNotIn('gross_product_spread', result['price_gate'])

    def test_quote_must_cover_requested_quantity_before_price_readiness(self):
        context = self.context(); context['opportunity']['quantity'] = '200'
        result = analyze(context, date(2026, 10, 20))
        self.assertFalse(result['price_gate']['price_ready'])
        self.assertIn('supplier_quantity_scope_mismatch', result['price_gate']['missing_or_invalid'])

    def freight_context(self):
        context = self.context()
        quote = dict(context['quotes'][0]['quote'], party='freight', amount='250', origin='Fixture origin',
                     destination='Fixture destination', incoterm='DAP', transport_mode='road', amount_basis='shipment_total')
        context['quotes'].append({'quote':quote, 'review':copy.deepcopy(context['quotes'][0]['review'])})
        return context

    def test_freight_is_a_shipment_total_and_never_net_profit(self):
        context = self.freight_context(); original = copy.deepcopy(context)
        gate = analyze(context, date(2026, 10, 20))['logistics_gate']
        self.assertTrue(gate['evidence_ready'])
        self.assertEqual(Decimal(gate['goods_plus_freight_subtotal']), Decimal('1500'))
        self.assertFalse(gate['landed_cost_ready']); self.assertFalse(gate['net_profit_calculated'])
        self.assertIn('insurance', gate['excluded_costs'])
        self.assertEqual(context, original)

    def test_freight_scope_must_match_without_currency_or_unit_conversion(self):
        for field, value in [('quantity','50'),('currency','EUR'),('price_unit','kg'),('amount_basis','unit')]:
            context = self.freight_context(); context['quotes'][2]['quote'][field] = value
            gate = analyze(context, date(2026, 10, 20))['logistics_gate']
            self.assertFalse(gate['evidence_ready'], field)
            self.assertNotIn('goods_plus_freight_subtotal', gate)

    def test_expired_revoked_or_ambiguous_freight_cannot_be_counted(self):
        for kind in ('expired','revoked','duplicate'):
            context = self.freight_context()
            if kind == 'expired': context['quotes'][2]['quote']['valid_until'] = '2026-10-19'
            elif kind == 'revoked': context['quotes'][2]['review']['decision'] = 'rejected'
            else: context['quotes'].append(copy.deepcopy(context['quotes'][2]))
            context['opportunity']['verified_freight'] = '999'
            gate = analyze(context, date(2026, 10, 20))['logistics_gate']
            self.assertFalse(gate['evidence_ready']); self.assertNotIn('goods_plus_freight_subtotal', gate)
