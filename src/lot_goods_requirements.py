"""Partial minimum tank requirements from explicit repeated lot/goods tables."""
import hashlib
import re

HEADER = ['Description of Goods', 'Unit', 'Amount']
LOT = re.compile(r'([A-Z0-9][A-Z0-9/-]{1,60}) LOT ([1-9][0-9]{0,2})')
PRODUCT = re.compile(r'MULTI-PURPOSE FIRE TRUCK WITH A CAPACITY OF AT LEAST ([1-9][0-9]{0,5}) LITERS')


def extract(url, text):
    if not isinstance(text, str) or len(text) > 40000:
        return []
    lines = [' '.join(s.split()) for s in text.splitlines() if s.strip()]
    starts = [i for i in range(len(lines)-3) if LOT.fullmatch(lines[i]) and lines[i+1:i+4] == HEADER]
    if not starts:
        return []
    cursor, reference, lot, products, scopes, rows = starts[0], None, 0, set(), [], 0
    digest = hashlib.sha256(text.encode()).hexdigest()
    while cursor < len(lines):
        line = lines[cursor]
        match = LOT.fullmatch(line)
        if match:
            if lines[cursor+1:cursor+4] != HEADER or int(match[2]) != lot+1:
                return []
            if reference is not None and (reference != match[1] or not products):
                return []
            reference, lot, products = match[1], int(match[2]), set()
            cursor += 4
            continue
        if re.match(r'\d+\.\s*\D', line):
            # All table blocks must belong to this one contiguous table.
            return scopes if products and cursor > starts[-1] else []
        if lot == 0 or cursor+3 > len(lines):
            return []
        product, unit, amount = lines[cursor:cursor+3]
        if (not 2 <= len(product) <= 180 or unit != 'Number'
                or not re.fullmatch(r'[1-9][0-9]{0,5}', amount)
                or product in products or any(s in product for s in ('@', '://', '<', '>'))):
            return []
        products.add(product)
        rows += 1
        if rows > 64:
            return []
        tank = PRODUCT.fullmatch(product)
        if tank:
            scopes.append({'scope': f'{reference} LOT {lot} / {product}',
                           'lot_id': str(lot), 'product': product,
                           'source_quantity': amount, 'source_unit': 'units',
                           'product_family': 'fire_truck', 'coverage': 'partial',
                           'scope_binding': 'explicit_repeated_lot_goods_table',
                           'document_text_sha256': digest,
                           'clauses': [{'field': 'tank_capacity_l', 'expected': {'min': int(tank[1])},
                                        'source_url': url, 'quote': product}]})
        cursor += 3
    # Missing table terminator could mean a truncated or damaged notice.
    return []
