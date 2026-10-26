"""Bounded read-only live document probe; aggregate outcomes only."""
import json
import os
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from src.broker import ted_search
from src.ted_search_fields import apply_search_fields, notice_context
from src.ted_xml_enricher import enrich_opportunity
from src import document_parser


def probe_rows(rows):
    """Probe a bounded sample; portal context is never official notice evidence."""
    candidates=[row for row in rows if (notice_context(row) or {}).get('call_for_tenders') is True]
    selected=sorted(candidates,key=lambda row:bool(row.get('ted_document_link_count')),reverse=True)[:2]
    if not selected:raise RuntimeError('No current competition notices available for document probe')
    def read(row):
        document_parser.enrich_opportunity(row)
        # A parsed portal page must not skip the official-notice reader.
        return enrich_opportunity(row)
    with ThreadPoolExecutor(max_workers=2) as workers:
        success=list(workers.map(read,selected))
    counts=Counter()
    for row in selected:
        info=row.get('document_extraction') or {}
        for kind in ('xml','html','pdf'):
            counts[kind+'_parsed']+=int(info.get('ted_'+kind+'_parsed') is True)
        attempts=info.get('attempts')
        for attempt in attempts if isinstance(attempts,list) else []:
            if not isinstance(attempt,dict):
                continue
            if attempt.get('status')=='parsed':
                counts['linked_documents_parsed']+=int(attempt.get('source')=='linked_document')
                counts['portal_pages_parsed']+=int(attempt.get('source')=='source_page')
            if attempt.get('status')=='failed':
                raw=str(attempt.get('error') or 'unknown')
                code=re.search(r'HTTP Error ([0-9]{3})',raw)
                kind=raw.split(':',1)[0]
                reason=raw.split(':',1)[1] if ':' in raw else ''
                safe_reasons={'non_public_or_unresolvable_url','redirected_to_non_public_url','document_too_large','ted_source_not_xml','ted_html_download_not_html','ted_pdf_download_not_pdf','ted_document_origin_changed','ted_pdf_notice_url_changed','ted_document_notice_identity_or_text_missing','insufficient_ted_xml_text'}
                if kind=='ValueError' and reason in safe_reasons:
                    kind+='_'+reason
                counts['error_'+('HTTP_'+code.group(1) if code else kind)]+=1
        assert 'verified_unit_price' not in row and row.get('buyer_verified') is not True
    official=sum(bool(ok) and any((row.get('document_extraction') or {}).get('ted_'+kind+'_parsed') is True
                                 for kind in ('xml','html','pdf')) for row,ok in zip(selected,success))
    return {'attempted':len(selected),'sample_publications':[row.get('publication-number') for row in selected],
            'selected_with_document_links':sum(bool(row.get('ted_document_link_count')) for row in selected),
            'parsed':official,'official_notices_parsed':official,'official_notices_failed':len(selected)-official,
            'acceptance_passed':official==len(selected),**dict(counts)}


def main():
    end=date.today();start=end-timedelta(days=14)
    result=ted_search(f'publication-date >= {start:%Y%m%d} AND publication-date <= {end:%Y%m%d}',25)
    rows=[apply_search_fields(dict(row,source='TED')) for row in result.get('notices',result.get('results',[])) if isinstance(row,dict)]
    summary=probe_rows(rows)
    print('TED_DOCUMENT_SOURCE_PROBE',json.dumps(summary,sort_keys=True),flush=True)
    if summary['acceptance_passed'] is not True and os.environ.get('TED_RESPONSE_DIAGNOSTICS')=='1':
        from src.ted_response_probe import inspect_official_response
        publication=next((p for p in summary.get('sample_publications',[]) if isinstance(p,str) and re.fullmatch(r'[0-9]{1,8}-[0-9]{4}',p)),None)
        if publication:
            for fmt in ('xml','html','pdf'):
                print('TED_OFFICIAL_RESPONSE',json.dumps(inspect_official_response(publication,fmt),sort_keys=True),flush=True)
    if summary['acceptance_passed'] is not True:
        raise SystemExit('Official TED notice documents unavailable: release evidence gate failed')

if __name__=='__main__':main()

