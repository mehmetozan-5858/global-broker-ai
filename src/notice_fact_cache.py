"""A public-safe cache of explicit single-lot source facts, never quote evidence."""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

PATHS = {
    'quantity': 'procurementproject/estimatedoverallcontractquantity',
    'estimated_value': 'procurementproject/requestedtendertotal/estimatedoverallcontractamount',
    'submission_deadline_date': 'tenderingprocess/tendersubmissiondeadlineperiod/enddate',
}


def _publication(row: dict) -> str:
    value = str(row.get('publication-number') or '')
    return value if row.get('source') == 'TED' and re.fullmatch(r'[0-9]{1,8}-[0-9]{4}', value) else ''


def _amount(value: Any) -> bool:
    try:
        number = Decimal(str(value))
        return not isinstance(value, bool) and number.is_finite() and number > 0
    except (InvalidOperation, ValueError):
        return False


def _fields(value: Any) -> dict:
    if not isinstance(value, dict):
        return {}
    result = {}
    quantity = value.get('quantity')
    if isinstance(quantity, str) and len(quantity) <= 100 and re.fullmatch(r'[0-9]+(?:\.[0-9]+)?(?: [A-Za-z0-9]+)?', quantity) and _amount(quantity.split()[0]):
        result['quantity'] = quantity
    if _amount(value.get('estimated_value')) and re.fullmatch(r'[A-Z]{3}', str(value.get('budget_currency') or '')):
        result['estimated_value'] = str(value['estimated_value'])
        result['budget_currency'] = value['budget_currency']
    deadline = value.get('submission_deadline_date')
    if isinstance(deadline, str):
        try:
            date.fromisoformat(deadline)
        except ValueError:
            pass
        else:
            result['submission_deadline_date'] = deadline
    return result


def process(rows: list[dict], cache: dict, now: str | None = None) -> dict:
    now = now or datetime.now(timezone.utc).isoformat()
    previous = cache.get('notices', {}) if isinstance(cache, dict) else {}
    previous = previous if isinstance(previous, dict) else {}
    # Rebuild entries from the allowlist; arbitrary/private JSON never survives.
    entries = {}
    for key, value in previous.items():
        if not re.fullmatch(r'[0-9]{1,8}-[0-9]{4}', str(key)) or not isinstance(value, dict):
            continue
        facts = _fields(value.get('fields'))
        observed = value.get('verified_at')
        try:
            datetime.fromisoformat(str(observed))
        except ValueError:
            continue
        if facts and value.get('lot_count') == 1:
            entries[key] = {'lot_count': 1, 'fields': facts, 'verified_at': observed}
    reused = refreshed = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        publication = _publication(row)
        if not publication:
            continue
        info = row.get('document_extraction') or {}
        if info.get('ted_xml_parsed') is True:
            # A newly read XML document replaces older facts, including deletion.
            entries.pop(publication, None)
            if row.get('ted_lot_count') != 1 or row.get('ted_lot_selection_required') is True:
                continue
            source = row.get('structured_source_evidence') or {}
            values = {key: row.get(key) for key, path in PATHS.items()
                      if isinstance(source.get(key), dict) and source[key].get('inferred') is False and source[key].get('source_path') == path}
            values['budget_currency'] = row.get('budget_currency')
            facts = _fields(values)
            if facts:
                entries[publication] = {'lot_count': 1, 'fields': facts, 'verified_at': now}
                row['notice_source_state'] = 'current_document'
                row['notice_source_verified_at'] = now
                refreshed += 1
            continue
        saved = entries.get(publication)
        if not saved or row.get('ted_lot_selection_required') is True or row.get('ted_lot_count') not in (None, 1):
            continue
        filled = []
        for key, value in saved['fields'].items():
            if row.get(key) in (None, '', [], {}):
                # Currency and budget form one fact; never mix contradictory values.
                if key in {'estimated_value','budget_currency'}:
                    if row.get('budget_currency') not in (None,'',saved['fields'].get('budget_currency')) or row.get('estimated_value') not in (None,'',saved['fields'].get('estimated_value')):
                        continue
                row[key] = value
                filled.append(key)
        if not filled:
            continue
        row['notice_source_state'] = 'previously_verified_document'
        row['notice_source_verified_at'] = saved['verified_at']
        row['notice_cached_fields'] = filled
        row['ted_lot_count'] = 1
        row['ted_lot_selection_required'] = False
        if row.get('estimated_value') == saved['fields'].get('estimated_value') and row.get('budget_currency') == saved['fields'].get('budget_currency'):
            row['public_source_terms'] = {'kind':'notice_estimate','estimated_budget':row['estimated_value'],'budget_currency':row['budget_currency']}
        reused += 1
    entries = dict(sorted(entries.items(), key=lambda pair: pair[1]['verified_at'], reverse=True)[:1000])
    return {'version': 1, 'notices': entries, 'last_scan': {'reused_notices': reused, 'refreshed_notices': refreshed}}
