"""Read at most two real notices via official daily packages; no writes."""
from datetime import date, timedelta
import json
from src.broker import ted_search
from src.ted_bulk import publication
from src.ted_search_fields import apply_search_fields, notice_context
from src.ted_xml_enricher import enrich_payload


def main():
    end = date.today()
    start = end - timedelta(days=14)
    result = ted_search(f'publication-date >= {start:%Y%m%d} AND publication-date <= {end:%Y%m%d}', 25)
    rows = [apply_search_fields(dict(row, source='TED')) for row in result.get('notices', []) if isinstance(row, dict)]
    rows = sorted([row for row in rows if (notice_context(row) or {}).get('call_for_tenders') is True],
                  key=lambda row: bool(row.get('ted_document_link_count')), reverse=True)[:2]
    if not rows:
        raise RuntimeError('no-bulk-probe-notices')
    payload = enrich_payload({'opportunities': rows}, bulk_enabled=True)
    outcomes = []
    for row in rows:
        identity = publication(row['publication-number'])
        info = row.get('document_extraction', {})
        parsed = [a for a in info.get('attempts', []) if a.get('status') == 'parsed']
        outcomes.append({'publication': identity, 'ojs': row.get('ojs-number'),
                         'official_xml_parsed': info.get('ted_xml_parsed') is True,
                         'text_chars': info.get('text_chars', 0),
                         'package_sha256': next((a['source_package_sha256'] for a in parsed if a.get('source_package_sha256')), None),
                         'linked_documents_parsed': sum(a.get('source') in {'attachment', 'linked_document'} for a in parsed),
                         'commercial_approval': row.get('buyer_verified') is True})
    passed = all(o['official_xml_parsed'] and not o['commercial_approval'] for o in outcomes)
    print('TED_BULK_NOTICE_PROBE', json.dumps({'official_notice_acceptance': passed,
          'technical_annex_acceptance': False, 'batch': payload['document_extraction'].get('ted_bulk_fallback'),
          'outcomes': outcomes}, sort_keys=True), flush=True)
    if not passed:
        raise SystemExit('Official bulk notice gate failed')


if __name__ == '__main__': main()
