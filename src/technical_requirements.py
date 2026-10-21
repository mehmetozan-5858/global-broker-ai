"""Conservative extraction of explicitly scoped requirement tables.

The first supported layout is a two-column Italian bus specification. Unknown
layouts remain unstructured; this is partial clause extraction, never approval.
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit


def extract_document(url: str, text: str) -> list[dict]:
    try:
        p = urlsplit(url)
        if p.scheme != 'https' or not p.hostname or p.username or p.password:
            return []
    except ValueError:
        return []
    lines = [' '.join(s.split()) for s in text.splitlines() if s.strip()]
    headers = [s for s in lines if s.startswith('Caratteristica LOTTO ')]
    if len(headers) != 1 or len(re.findall(r'\bLOTTO\s+\d+', headers[0])) != 2:
        return []
    lot = re.match(r'Caratteristica LOTTO (\d+)\b', headers[0])
    patterns = {
        'length_mm': r'Lunghezza (\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?) metri \(autobus corto\) circa \d+(?:[.,]\d+)? metri',
        'passenger_capacity': r'Capienza complessiva (\d+) posti \(seduti \+ in piedi\) \d+/\d+ posti \(seduti \+ in piedi\)',
        'vehicle_class': r'Categoria veicolo M3, Classe I urbano M3, Classe I urbano',
    }
    matched = {}
    for field, pattern in patterns.items():
        hits = [(line, re.fullmatch(pattern, line)) for line in lines]
        hits = [(line, m) for line, m in hits if m]
        if len(hits) != 1:
            return []
        matched[field] = hits[0]
    # The two repeated values explicitly agree across the table columns.
    emissions = [s for s in lines if s.startswith('Standard emissivo ')]
    fuels = [s for s in lines if s.startswith('Alimentazione Metano (CNG), serbatoi omologati sul')]
    if len(emissions) != 1 or emissions[0].count('Euro 6 Step E') != 2 or len(fuels) != 1:
        return []
    lo, hi = [float(v.replace(',', '.')) * 1000 for v in matched['length_mm'][1].groups()]
    if not 1000 <= lo <= hi <= 20000:
        return []
    capacity = int(matched['passenger_capacity'][1].group(1))
    if not 1 <= capacity <= 200:
        return []
    def clause(field, value, quote):
        return {'field': field, 'expected': value, 'source_url': url, 'quote': quote}
    return [{
        'scope': 'LOTTO ' + lot.group(1), 'product_family': 'urban_cng_bus',
        'coverage': 'partial', 'scope_binding': 'explicit_two_column_first_lot',
        'other_columns_not_inferred': True,
        'document_text_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'clauses': [clause('length_mm', {'min': lo, 'max': hi}, matched['length_mm'][0]),
                    clause('passenger_capacity', capacity, matched['passenger_capacity'][0]),
                    clause('vehicle_class', 'M3_CLASS_I', matched['vehicle_class'][0]),
                    clause('emission', 'EURO6_STEP_E', emissions[0]),
                    clause('fuel', 'CNG', fuels[0])],
    }]
