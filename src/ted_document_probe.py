"""Bounded read-only live document probe; aggregate outcomes only."""
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from src.broker import ted_search
from src.ted_search_fields import apply_search_fields, notice_context
from src.ted_xml_enricher import enrich_opportunity
from src import document_parser


def main():
    end=date.today();start=end-timedelta(days=14)
    result=ted_search(f'publication-date >= {start:%Y%m%d} AND publication-date <= {end:%Y%m%d}',25)
    rows=[apply_search_fields(dict(row,source='TED')) for row in result.get('notices',result.get('results',[])) if isinstance(row,dict)]
    candidates=[row for row in rows if (notice_context(row) or {}).get('call_for_tenders') is True]
    selected=sorted(candidates,key=lambda row:bool(row.get('ted_document_link_count')),reverse=True)[:2]
    if not selected:raise RuntimeError('No current competition notices available for document probe')
    def read(row):
        document_parser.enrich_opportunity(row)
        if (row.get('document_extraction') or {}).get('parsed_count',0) > 0:
            return True
        return enrich_opportunity(row)
    with ThreadPoolExecutor(max_workers=2) as workers:
        success=list(workers.map(read,selected))
    counts=Counter()
    for row in selected:
        info=row.get('document_extraction') or {}
        for kind in ('xml','html','pdf'):
            counts[kind+'_parsed']+=int(info.get('ted_'+kind+'_parsed') is True)
        for attempt in info.get('attempts') or []:
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
    print('TED_DOCUMENT_SOURCE_PROBE',json.dumps({'attempted':len(selected),'selected_with_document_links':sum(bool(row.get('ted_document_link_count')) for row in selected),'parsed':sum(success),'no_text':len(selected)-sum(success),**dict(counts)},sort_keys=True))

if __name__=='__main__':main()
