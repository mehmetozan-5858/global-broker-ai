"""Ephemeral analysis of privately reviewed evidence; never writes approval or prices."""
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation

from .commercial_evidence_acceptance import process_payload
from .price_margin_gate import assess


def analyze(context: dict, today: date | None = None) -> dict:
    today = today or date.today()
    item = deepcopy(context['opportunity'])
    # Rebuild quote fields from current review events, never stale prior projections.
    for key in list(item):
        if key.startswith(('verified_unit_price', 'verified_selling', 'supplier_quote_', 'supplier_price_', 'supplier_quantity_', 'buyer_quote_', 'buyer_price_', 'buyer_quantity_')) or key in {'quote_currency', 'quote_valid_until', 'selling_currency', 'selling_quote_buyer', 'commercial_evidence_submissions'}:
            item.pop(key)
    by_party = {'supplier': [], 'buyer': []}
    excluded = {'expired_or_invalid': 0, 'not_reviewed': 0}
    for row in context.get('quotes', []):
        review, q = row.get('review') or {}, row.get('quote') or {}
        checks = review.get('checks') or {}
        if review.get('decision') != 'accepted_for_analysis' or not all(checks.get(k) is True for k in ('source_reviewed', 'identity_scope_checked', 'price_quantity_currency_checked')):
            excluded['not_reviewed'] += 1
            continue
        try:
            current = date.fromisoformat(q['valid_until']) >= today and date.fromisoformat(q['quote_date']) <= today
        except (KeyError, ValueError, TypeError):
            current = False
        if not current or q.get('party') not in by_party:
            excluded['expired_or_invalid'] += 1
            continue
        by_party[q['party']].append(q)
    submissions, ambiguous = [], []
    for party, quotes in by_party.items():
        if len(quotes) > 1:
            ambiguous.append(party)  # Never silently choose the first supplier/buyer quote.
            continue
        if not quotes:
            continue
        q = quotes[0]
        submissions.append({'kind': 'unit_price' if party == 'supplier' else 'selling_unit_price',
            'value': q['amount'], 'currency': q['currency'], 'source_url': q['source_url'],
            'supplier_name' if party == 'supplier' else 'buyer_name': q['counterparty'],
            'quote_reference': q['reference'], 'quote_date': q['quote_date'],
            'valid_until': q['valid_until'], 'quantity_basis': q['quantity'], 'price_unit': q['price_unit']})
    item['commercial_evidence_submissions'] = submissions
    process_payload({'opportunities': [item]})
    gate = assess(item, today)
    def quantity(value):
        try:
            result = Decimal(str(value))
            return result if result.is_finite() and result > 0 else None
        except (InvalidOperation, ValueError):
            return None
    scope_issues = []
    buy = by_party['supplier'][0] if len(by_party['supplier']) == 1 else None
    sell = by_party['buyer'][0] if len(by_party['buyer']) == 1 else None
    requested = quantity(item.get('quantity') or item.get('requested_quantity') or item.get('qty'))
    if buy and requested and quantity(buy.get('quantity')) != requested:
        scope_issues.append('supplier_quantity_scope_mismatch')
        gate['price_ready'] = False
    if buy and sell:
        if quantity(buy.get('quantity')) != quantity(sell.get('quantity')):
            scope_issues.append('quote_quantity_scope_mismatch')
        if str(buy.get('price_unit', '')).strip().casefold() != str(sell.get('price_unit', '')).strip().casefold():
            scope_issues.append('quote_price_unit_mismatch')
    if scope_issues:
        gate['missing_or_invalid'] += scope_issues
        gate['margin_ready'] = False
        gate['status'] = 'price_ready' if gate['price_ready'] else 'research_required'
        for key in list(gate):
            if key.startswith(('gross_', 'negative_spread')):
                gate.pop(key)
    return {'status': 'analysis_only', 'price_gate': gate,
        'evidence': item.get('commercial_evidence_acceptance', {'results': [], 'accepted_count': 0, 'rejected_count': 0}),
        'ambiguous_parties': ambiguous, 'excluded': excluded,
        'commercial_approval': False, 'external_actions_enabled': False, 'persisted_prices': False}
