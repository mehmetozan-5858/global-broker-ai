"""Partial, citation-backed technical comparisons. Never exact-spec approval."""
from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from src.manufacturer_catalog import refresh
from src.technical_requirements import extract_document


def _fresh(value) -> bool:
    try:
        then = datetime.fromisoformat(value)
        age = (datetime.now(timezone.utc) - then).total_seconds()
        return -60 <= age <= 3600
    except (TypeError, ValueError):
        return False


def _current_scopes(item: dict) -> list[dict]:
    extraction = item.get('document_extraction') or {}
    if not isinstance(extraction, dict) or not isinstance(extraction.get('attempts'), list):
        return []
    if not _fresh(extraction.get('checked_at')):
        return []
    parsed = {a.get('url') for a in extraction.get('attempts', []) if isinstance(a, dict)
              and a.get('status') == 'parsed' and a.get('kind') in {'pdf', 'docx', 'text'}}
    for attempt in extraction['attempts']:
        if not isinstance(attempt, dict) or attempt.get('status') != 'parsed' or attempt.get('format') != 'world_bank_notice_json':
            continue
        try:
            url = urlsplit(attempt.get('url', ''))
            if (item.get('source') == 'WORLD_BANK' and attempt.get('notice_id') == item.get('id')
                    and url.scheme == 'https' and url.hostname == 'search.worldbank.org'
                    and not url.username and not url.password and url.port in (None, 443)
                    and url.path == '/api/v2/procnotices'
                    and parse_qs(url.query).get('qterm') == [item.get('id')]):
                parsed.add(attempt['url'])
        except (ValueError, TypeError):
            continue
    text = item.get('document_extracted_text') or ''
    if not isinstance(text, str):
        return []
    scopes = []
    # Recompute from current retained text; caller-provided clause values or
    # old scopes cannot silently alter the requirement or citation.
    for candidate in (item.get('technical_requirement_scopes') or [])[:12]:
        if not isinstance(candidate, dict) or not isinstance(candidate.get('clauses'), list) or not candidate['clauses']:
            continue
        if not isinstance(candidate['clauses'][0], dict):
            continue
        url = candidate['clauses'][0].get('source_url')
        if url not in parsed:
            continue
        for replay in extract_document(url, text):
            if candidate.get('scope') == replay['scope'] and candidate['clauses'] == replay['clauses']:
                scopes.append(replay)
    return scopes


def compare_clause(clause: dict, catalog: dict) -> dict:
    result = {'field': clause['field'], 'expected': clause['expected'],
              'requirement_source_url': clause['source_url'], 'requirement_quote': clause['quote'],
              'status': 'missing_evidence', 'catalog_evidence': []}
    if catalog.get('status') != 'read' or not _fresh(catalog.get('checked_at')):
        result['status'] = 'catalog_unavailable'
        return result
    facts = [f for f in catalog.get('facts', []) if isinstance(f, dict) and f.get('field') == clause['field']]
    result['catalog_evidence'] = facts
    if any(f.get('source_url') != catalog.get('url') or not isinstance(f.get('quote'), str) or not f['quote'].strip() for f in facts):
        result['status'] = 'invalid_catalog_evidence'
        return result
    if not facts:
        return result
    if len({json.dumps(f.get('value'), sort_keys=True) for f in facts}) != 1:
        result['status'] = 'conflicting_catalog_evidence'
        return result
    if any(f.get('evidence_level') != 'model' for f in facts):
        result['status'] = 'configuration_confirmation_required'
        return result
    value = facts[0].get('value')
    if clause['field'] == 'length_mm':
        if type(value) not in {int, float} or not math.isfinite(value):
            result['status'] = 'invalid_catalog_evidence'
            return result
        quote = re.fullmatch(r'OVERAL LENGHT\s+([\d ]{3,7})\s*mm', facts[0]['quote'])
        if not quote or int(quote.group(1).replace(' ', '')) != value:
            result['status'] = 'invalid_catalog_evidence'
            return result
        expected = clause['expected']
        result['status'] = 'source_supported' if expected['min'] <= value <= expected['max'] else 'conflict'
    else:
        result['status'] = 'source_supported' if value == clause['expected'] else 'conflict'
    return result


def process_payload(payload: dict, catalogs: list[dict] | None = None) -> dict:
    rows = [r for r in payload.get('opportunities', []) if isinstance(r, dict)]
    prepared = [(row, _current_scopes(row)) for row in rows]
    if catalogs is None:
        catalogs = refresh() if any(s.get('product_family') == 'urban_cng_bus' for _, scopes in prepared for s in scopes) else []
    task_counts = Counter()
    compared_scopes = 0
    structured_scopes = 0
    for row, scopes in prepared:
        results = []
        by_scope = {}
        for scope in scopes:
            by_scope.setdefault(scope['scope'], []).append(scope)
        for name, versions in by_scope.items():
            signatures = {json.dumps([(c['field'], c['expected']) for c in s['clauses']], sort_keys=True) for s in versions}
            if len(signatures) != 1:
                results.append({'scope': name, 'status': 'conflicting_requirements', 'models': []})
                continue
            scope = versions[0]
            models = []
            relevant_catalogs = [c for c in catalogs[:12] if c.get('product_family', 'urban_cng_bus') == scope.get('product_family')]
            for catalog in relevant_catalogs:
                clauses = [compare_clause(c, catalog) for c in scope['clauses']]
                models.append({'manufacturer': catalog['manufacturer'], 'model': catalog['model'],
                               'source_url': catalog['url'], 'checked_at': catalog.get('checked_at'),
                               'clause_results': clauses, 'exact_spec_match_verified': False,
                               'financial_evidence_eligible': False})
            has_catalog = any(c.get('status') == 'read' and _fresh(c.get('checked_at')) and c.get('facts') for c in relevant_catalogs)
            results.append({'scope': name, 'status': 'partial_research_only' if has_catalog else ('catalog_refresh_required' if relevant_catalogs else 'manufacturer_research_required'), 'coverage': 'partial',
                            'requirements': scope['clauses'], 'product_family': scope['product_family'],
                            'other_requirements_not_automated': True, 'models': models})
            structured_scopes += 1
            compared_scopes += bool(has_catalog)
        status = ('partial_research_only' if any(s['status'] == 'partial_research_only' for s in results) else
                  'catalog_refresh_required' if any(s['status'] == 'catalog_refresh_required' for s in results) else
                  'manufacturer_research_required' if results else 'requirements_not_structured')
        row['technical_comparison'] = {
            'status': status, 'scopes': results, 'human_review_required': True,
            'lot_selection_required': row.get('source_lot_selection_required') is True or row.get('ted_lot_selection_required') is True,
            'exact_spec_match_verified': False, 'external_contact_authorized': False,
            'next_action': ('find_official_product_family_catalog' if status == 'manufacturer_research_required' else
                            'review_clause_gaps_and_unmodeled_requirements' if results else 'structure_current_source_requirements'),
        }
        task_counts[status] += 1
    payload['technical_comparison_summary'] = {
        'opportunities': len(rows), 'structured_scopes': structured_scopes, 'compared_scopes': compared_scopes,
        'task_counts': dict(task_counts), 'catalog_pages_read': sum(c.get('status') == 'read' for c in catalogs),
        'catalog_pages_failed': sum(c.get('status') != 'read' for c in catalogs),
        'exact_spec_approvals': 0, 'external_actions_enabled': False,
        'supported_extractor': 'explicit_two_column_italian_urban_bus_first_lot_and_repeated_lot_goods_table',
        'supported_catalog_registry': 'two_rosero_models_and_indcar_cng_family',
    }
    return payload


def main() -> None:
    path = Path(sys.argv[1])
    payload = process_payload(json.loads(path.read_text()))
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print('TECHNICAL_COMPARISON_SUMMARY', json.dumps(payload['technical_comparison_summary']))


if __name__ == '__main__':
    main()
