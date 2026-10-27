"""Read one notice-linked public technical annex; no auth, writes or approval."""
import json
from xml.etree import ElementTree as ET
from src import document_parser
from src.ted_bulk import fetch_daily_notices

PUBLICATION = '702997-2026'
PORTAL = 'https://zakazky.krajbezkorupce.cz/vz00047078'
LATEST_ANNEX = 'https://zakazky.krajbezkorupce.cz/document_254114/70456a8a24715db566d2cb2f10172d37-priloha-c-5-zd-technicka-specifikace_27_10_2026-docx'


def main():
    notice = fetch_daily_notices('197/2026', [PUBLICATION])[PUBLICATION]
    references = []
    for node in ET.fromstring(notice.data).iter():
        if node.tag.rsplit('}', 1)[-1] == 'CallForTendersDocumentReference':
            references.extend((n.text or '').strip() for n in node.iter() if n.tag.rsplit('}', 1)[-1] == 'URI')
    if PORTAL not in references:
        raise RuntimeError('notice-does-not-link-expected-portal')
    row = document_parser.enrich_opportunity({'document_url': PORTAL})
    info = row['document_extraction']
    attempts = info.get('attempts', [])
    annexes = [a for a in attempts if a.get('source') == 'attachment' and a.get('status') == 'parsed']
    latest = [a for a in annexes if a.get('url') == LATEST_ANNEX and a.get('kind') == 'docx'
              and a.get('discovered_from') == 'https://zakazky.krajbezkorupce.cz/contract_display_47078.html'
              and a.get('extracted_chars', 0) >= 80 and len(a.get('sha256', '')) == 64]
    main_pdf = any(a.get('kind') == 'pdf' for a in annexes)
    passed = len(latest) == 1 and main_pdf and not row.get('buyer_verified')
    # Technical read evidence only; never infer all portal attachments read,
    # authoritative version selection, specification compliance or commerce.
    print('TED_ANNEX_PROBE', json.dumps({'publication': PUBLICATION,
        'package_sha256': notice.package_sha256, 'notice_linked_portal': PORTAL,
        'sample_document_and_technical_annex_read': passed,
        'all_documents_read': False, 'commercial_approval': False,
        'attempts': attempts}, sort_keys=True), flush=True)
    if not passed:
        raise SystemExit('Notice-linked technical annex sample gate failed')


if __name__ == '__main__': main()
