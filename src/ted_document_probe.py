"""Bounded read-only live document probe; aggregate outcomes only."""
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from src.broker import ted_search
from src.ted_search_fields import apply_search_fields, notice_context
from src.ted_xml_enricher import enrich_opportunity


def main():
    end=date.today();start=end-timedelta(days=14)
    result=ted_search(f'publication-date >= {start:%Y%m%d} AND publication-date <= {end:%Y%m%d}',25)
    rows=[apply_search_fields(dict(row,source='TED')) for row in result.get('notices',result.get('results',[])) if isinstance(row,dict)]
    selected=[row for row in rows if (notice_context(row) or {}).get('call_for_tenders') is True][:2]
    if not selected:raise RuntimeError('No current competition notices available for document probe')
    with ThreadPoolExecutor(max_workers=2) as workers:
        success=list(workers.map(enrich_opportunity,selected))
    counts=Counter()
    for row in selected:
        info=row.get('document_extraction') or {}
        for kind in ('xml','html','pdf'):
            counts[kind+'_parsed']+=int(info.get('ted_'+kind+'_parsed') is True)
        for attempt in info.get('attempts') or []:
            if attempt.get('status')=='failed':
                raw=str(attempt.get('error') or 'unknown')
                code=re.search(r'HTTP Error ([0-9]{3})',raw)
                counts['error_'+('HTTP_'+code.group(1) if code else raw.split(':',1)[0])]+=1
        assert 'verified_unit_price' not in row and row.get('buyer_verified') is not True
    print('TED_DOCUMENT_SOURCE_PROBE',json.dumps({'attempted':len(selected),'parsed':sum(success),'no_text':len(selected)-sum(success),**dict(counts)},sort_keys=True))

if __name__=='__main__':main()
