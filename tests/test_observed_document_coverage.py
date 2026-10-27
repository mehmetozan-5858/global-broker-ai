import unittest
from unittest.mock import patch
from src import document_parser
from src.document_coverage import summarize, observe
from src.specification import analyze_opportunity
from src.public_opportunity_projection import project_public_opportunity
from src.ted_xml_enricher import enrich_opportunity as enrich_ted
from tests.test_ted_bulk import xml
from src.ted_bulk import BulkNotice


class ObservedCoverageTests(unittest.TestCase):
    def test_inventory_retains_skipped_unsupported_and_failed_links_before_budget(self):
        page = 'https://example.test/tender/1'
        html = ('<p>' + 'Source context. ' * 20 + '</p>' +
                ''.join(f'<a href="/annex{i}.txt">Technical requirements</a>' for i in range(4)) +
                '<a href="/bill.xlsx">Bill of quantities</a><a href="/drawings.zip">Drawings</a>').encode()
        def download(url, *args):
            if url == page: return html, 'text/html', page
            if url.endswith('annex1.txt'): raise TimeoutError('fixture')
            return ('Technical requirements: minimum quantity 20 units ISO 9001. ' * 5).encode(), 'text/plain', url
        row = {'document_url': page, 'technical-specification': 'Equipment quantity 20 units ISO 9001'}
        with patch.object(document_parser, '_download', side_effect=download):
            document_parser.enrich_opportunity(row)
        info = row['document_extraction']
        self.assertEqual(info['attachment_candidates_observed'], 6)
        self.assertEqual(info['attachment_candidates_omitted'], 3)
        self.assertEqual(info['attachment_candidates_unsupported'], 2)
        self.assertEqual(info['attachment_candidates_failed'], 1)
        self.assertEqual({x['status'] for x in info['attachment_inventory']}, {'parsed','failed','skipped','unsupported'})
        analyze_opportunity(row)
        self.assertFalse(row['specification_analysis']['supplier_sourcing_ready'])
        self.assertIn('attachment_downloads_failed', row['specification_analysis']['document_coverage_blockers'])
        public = project_public_opportunity(row)
        self.assertIn('attachment_downloads_failed', public['document_coverage_blockers'])
        self.assertNotIn('example.test', str(public))
        self.assertNotIn('attachment_inventory', str(public))

    def test_dated_annex_pair_requires_review_without_selecting_latest(self):
        base = 'https://zakazky.krajbezkorupce.cz'
        urls = [base + '/document_1/' + 'a'*32 + '-priloha-c-5-zd-technicka-specifikace-docx',
                base + '/document_2/' + 'b'*32 + '-priloha-c-5-zd-technicka-specifikace_27_10_2026-docx']
        inventory = {}
        observe([{'href': u} for u in urls + [urls[0]]], base, inventory)
        info = summarize(inventory, [{'url': u, 'source': 'attachment', 'status': 'parsed'} for u in urls])
        self.assertTrue(info['document_versions_review_required'])
        self.assertEqual(info['document_version_groups'][0]['urls'], urls)
        row = {'technical-specification': 'Technical equipment ISO 9001', 'document_extraction': info}
        analyze_opportunity(row)
        self.assertIn('document_versions_require_review', row['specification_analysis']['document_coverage_blockers'])
        self.assertFalse(row['specification_analysis']['supplier_sourcing_ready'])
        self.assertNotIn('selected_version', str(info))

    def test_different_families_or_origins_are_not_grouped_and_fresh_scan_clears(self):
        inventory = {}
        observe([{'href': 'https://a.test/technical.pdf'}, {'href': 'https://b.test/technical_27_10_2026.pdf'},
                 {'href': 'https://a.test/other_27_10_2026.pdf'}], '', inventory)
        self.assertFalse(summarize(inventory, [])['document_versions_review_required'])
        self.assertEqual(summarize({}, [])['attachment_candidates_omitted'], 0)

    def test_notice_enrichment_cannot_erase_existing_coverage_gates(self):
        info = {'attachment_candidates_omitted': 2, 'text_truncated': True,
                'document_versions_review_required': True, 'attachment_candidates_failed': 1}
        row = {'source': 'TED', 'publication-number': '123-2026', 'document_extraction': info}
        notice = BulkNotice('123-2026', '197/2026', xml(), 'a'*64)
        self.assertTrue(enrich_ted(row, bulk_notice=notice))
        self.assertEqual(row['document_extraction']['attachment_candidates_omitted'], 2)
        self.assertTrue(row['document_extraction']['text_truncated'])
        self.assertTrue(row['document_extraction']['document_versions_review_required'])
        self.assertEqual(row['document_extraction']['attachment_candidates_failed'], 1)


if __name__ == '__main__': unittest.main()
