"""Read at most two real notices via official daily packages; no writes."""
from datetime import date, timedelta
import json
from src.broker import ted_search
from src.ted_bulk import publication
from src.ted_search_fields import apply_search_fields, notice_context
from src.ted_xml_enricher import enrich_payload
from src.ted_bulk_gate import notice_only_acceptance, summarize_attempt_evidence, historic_attempt_offset


def main():
    end = date.today()
    start = end - timedelta(days=14)
    result = ted_search(f'publication-date >= {start:%Y%m%d} AND publication-date <= {end:%Y%m%d}', 25)
    rows = [apply_search_fields(dict(row, source='TED')) for row in result.get('notices', []) if isinstance(row, dict)]
    rows = sorted([row for row in rows if (notice_context(row) or {}).get('call_for_tenders') is True],
                  key=lambda row: bool(row.get('ted_document_link_count')), reverse=True)[:2]
    if not rows:
        raise RuntimeError('no-bulk-probe-notices')
    # Record the imported attempt boundary before any direct/bulk source work.
    # Imported rows must never contribute official evidence to this probe.
    prior_attempt_counts = []
    for row in rows:
        info = row.get('document_extraction')
        prior_attempt_counts.append(historic_attempt_offset(info))
    payload = enrich_payload({'opportunities': rows}, bulk_enabled=True)
    outcomes = []
    for row, prior_count in zip(rows, prior_attempt_counts):
        identity = publication(row['publication-number'])
        info = row.get('document_extraction')
        evidence = summarize_attempt_evidence(info, new_attempt_offset=prior_count)
        outcomes.append({'publication': identity, 'ojs': row.get('ojs-number'),
                         'official_xml_parsed': isinstance(info, dict) and info.get('ted_xml_parsed') is True,
                         'source_channel': evidence['source_channel'],
                         'text_chars': info.get('text_chars', 0) if isinstance(info, dict) else 0,
                         'package_sha256': evidence['package_sha256'],
                         'linked_documents_parsed': evidence['linked_documents_parsed'],
                         'commercial_approval': row.get('buyer_verified') is True})
    passed = notice_only_acceptance(outcomes)
    print('TED_BULK_NOTICE_PROBE', json.dumps({'official_notice_acceptance': passed,
          'technical_annex_acceptance': False, 'batch': payload['document_extraction'].get('ted_bulk_fallback'),
          'outcomes': outcomes}, sort_keys=True), flush=True)
    if not passed:
        raise SystemExit('Official bulk notice gate failed')


if __name__ == '__main__': main()
