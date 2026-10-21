"""Refresh a bounded registry of official model pages; never supplier approval."""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import urlsplit

from src import document_parser

PROFILES = (
    {'manufacturer': 'Rošero', 'model': 'First FCLEI', 'url': 'https://rosero.sk/en/portfolio/1163-2/'},
    {'manufacturer': 'Rošero', 'model': 'First FCLLI', 'url': 'https://rosero.sk/en/portfolio/1164-2/'},
    {'manufacturer': 'INDCAR', 'model': 'Mobi City CNG family', 'url': 'https://indcar.es/en/urban-minibus-mobi-city-gnc/'},
)


def parse(profile: dict, text: str) -> list[dict]:
    model = profile['model']
    flat = ' '.join(text.split())
    def fact(field, value, quote, level='model'):
        return {'field': field, 'value': value, 'quote': quote,
                'source_url': profile['url'], 'evidence_level': level}
    if model.startswith('First '):
        # Require the table's actual model row, not a model name in navigation.
        if not re.search(r'\bMODEL\s+' + re.escape(model) + r'\s+MAX\. TOTAL WEIGHT\b', flat, re.I):
            return []
        facts = []
        hits = list(re.finditer(r'\bOVERAL LENGHT\s+([\d ]{3,7})\s*mm\b', flat))
        if len(hits) == 1:
            mm = int(hits[0].group(1).replace(' ', ''))
            if 1000 <= mm <= 20000:
                facts.append(fact('length_mm', mm, hits[0].group(0)))
        marker = 'CNG or electric motor drive'
        if marker in flat and 'Optional equipment:' in flat and flat.index(marker) > flat.index('Optional equipment:'):
            facts.append(fact('fuel', 'CNG', marker, 'option'))
        return facts
    if model == 'Mobi City CNG family' and 'Mobi city GNC' in text:
        # Family-level availability is deliberately not model/configuration proof.
        return [fact('fuel', 'CNG', 'Mobi city GNC', 'family')]
    return []


def _read(profile: dict) -> dict:
    result = {**profile, 'product_family': 'urban_cng_bus', 'facts': [], 'status': 'unavailable',
              'checked_at': datetime.now(timezone.utc).isoformat()}
    try:
        data, kind, final_url = document_parser._download(profile['url'], 1024 * 1024)
        expected, actual = urlsplit(profile['url']), urlsplit(final_url)
        if (actual.scheme, actual.netloc, actual.path.rstrip('/')) != (expected.scheme, expected.netloc, expected.path.rstrip('/')) or actual.query:
            raise ValueError('catalog_origin_or_model_path_changed')
        if 'html' not in kind:
            raise ValueError('catalog_not_html')
        text, _ = document_parser._parse_html_page(data, final_url)
        result['facts'] = parse(profile, text)
        result['status'] = 'read' if result['facts'] else 'no_supported_model_facts'
    except Exception as exc:
        result['error'] = type(exc).__name__ + ':' + str(exc)[:120]
    return result


def refresh() -> list[dict]:
    with ThreadPoolExecutor(max_workers=3) as executor:
        return list(executor.map(_read, PROFILES))
