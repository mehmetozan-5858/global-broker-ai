"""Read at most two real notices via official daily packages; no writes."""
from datetime import date, timedelta
import json
from src.broker import ted_search
from src.ted_bulk import fetch_daily_notices, publication
from src.ted_search_fields import apply_search_fields, notice_context
from src.ted_xml_enricher import enrich_opportunity


def main():
    end = date.today()
    start = end - timedelta(days=14)
    result = ted_search(f'publication-date >= {start:%Y%m%d} AND publication-date <= {end:%Y%m%d}', 25)
    rows = [apply_search_fields(dict(row, source='TED')) for row in result.get('notices', []) if isinstance(row, dict)]
    rows = sorted([row for row in rows if (notice_context(row) or {}).get('call_for_tenders') is True],
                  key=lambda row: bool(row.get('ted_document_link_count')), reverse=True)[:2]
    if not rows:
        raise RuntimeError('no-bulk-probe-notices')
    groups = {}
    for row in rows:
        edition = row.get('ojs-number')
        if isinstance(edition, list) and len(edition) == 1:
            edition = edition[0]
        if not isinstance(edition, str):
            raise ValueError('missing-official-ojs-metadata')
        groups.setdefault(edition, []).append(row)
    outcomes = []
    for edition, members in groups.items():
        notices = fetch_daily_notices(edition, [row['publication-number'] for row in members])
        for row in members:
            identity = publication(row['publication-number'])
            notice = notices[identity]
            ok = enrich_opportunity(row, bulk_notice=notice)
            info = row.get('document_extraction', {})
            outcomes.append({'publication': identity, 'ojs': edition,
                             'official_xml_parsed': ok and info.get('ted_xml_parsed') is True,
                             'text_chars': info.get('text_chars', 0), 'package_sha256': notice.package_sha256,
                             'linked_documents_parsed': sum(a.get('status') == 'parsed' and a.get('source') in {'attachment', 'linked_document'}
                                                           for a in info.get('attempts', [])),
                             'commercial_approval': row.get('buyer_verified') is True})
    passed = all(o['official_xml_parsed'] and not o['commercial_approval'] for o in outcomes)
    print('TED_BULK_NOTICE_PROBE', json.dumps({'official_notice_acceptance': passed,
          'technical_annex_acceptance': False, 'outcomes': outcomes}, sort_keys=True), flush=True)
    if not passed:
        raise SystemExit('Official bulk notice gate failed')


if __name__ == '__main__': main()
