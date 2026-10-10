import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from src.browser_render import dump_dom
from src.saudi_etimad_feed import _api_record, collect, discover_detail_links, parse_detail
from src.uae_mof_feed import AR_SOURCE_URL, BROWSER_USER_AGENT, SOURCE_URL
from src.uae_mof_feed import collect as collect_uae
from src.uae_mof_feed import discover_ministry_filters, filtered_page_url
from src.uae_mof_feed import parse as parse_uae

ROOT = Path(__file__).resolve().parents[1]

UAE_HTML = '''
<table><tr><th>RFQ Number</th><th>Entity Name</th><th>Title</th><th>Open Date</th><th>Close Date</th><th>Link</th></tr>
<tr><td>12583</td><td>Emirates Space Agency</td><td>Supply of event gifts and giveaway items</td><td>02/10/2026</td><td>25/10/2026</td><td><a href="https://procurement.gov.ae/rfx/12583">Click here</a></td></tr>
<tr><td>12601</td><td>Ministry</td><td>Leadership assessment services</td><td>05/10/2026</td><td>26/10/2026</td><td><a href="https://procurement.gov.ae/rfx/12601">Click here</a></td></tr>
</table>
'''

UAE_FILTER_HTML = '''
<select name="mof-dpp-ministry">
<option value="">All</option>
<option value="Emirates Space Agency - (286/9294)">Emirates Space Agency</option>
<option value="Ministry of Justice - (121/16896)">Ministry of Justice</option>
</select>
'''

UAE_CARD_HTML = '''
<div class="tender-card">
  <h3>RFP EMM gifts and giveaway for events, csr, and roadshows</h3>
  <div>12583</div>
  <div>Emirates Space Agency - (286/9294)</div>
  <p>Specialized suppliers in the field of gifts and giveaways are invited to participate.</p>
  <div>Open Date 02/10/2026 10:17:38 AM</div>
  <div>Close Date 25/10/2026 10:30:00 PM</div>
  <a href="https://procurement.gov.ae/rfx/12583">Click here</a>
</div>
'''

SAUDI_LIST = '''<html><body>
<a href="/Tender/DetailsForVisitor?STenderId=abc%3D%3D">تفاصيل المنافسة</a>
<a href="/Tender/DetailsForVisitor?STenderId=abc%3D%3D">duplicate</a>
</body></html>'''

SAUDI_RENDERED_URL = '''<html><body><button data-url="/Tender/DetailsForVisitor?STenderId=xyz%3D%3D">details</button></body></html>'''

SAUDI_DETAIL = '''<html><body>
<div>اسم المنافسة</div><div>توريد أجهزة قياس صناعية</div>
<div>رقم المنافسة</div><div>2026/55</div>
<div>الرقم المرجعي</div><div>260239009999</div>
<div>الغرض من المنافسة</div><div>توريد أجهزة للمختبر</div>
<div>حالة المنافسة</div><div>تقديم العروض</div>
<div>الجهة الحكوميه</div><div>وزارة الصناعة</div>
<div>الوقت المتبقى</div><div>5 أيام</div>
<div>قيمة وثائق المنافسة</div><div>500.00</div>
</body></html>'''

SAUDI_ENDED = SAUDI_DETAIL.replace('5 أيام','إنتهى')
SAUDI_API_ITEM = {
    'referenceNumber': '260239009999',
    'tenderName': 'توريد أجهزة قياس صناعية',
    'tenderNumber': '2026/55',
    'agencyName': 'وزارة الصناعة',
    'branchName': 'الرياض',
    'tenderTypeName': 'منافسة عامة',
    'submitionDate': '2026-10-01T12:00:00',
    'lastOfferPresentationDate': '2026-10-25T12:00:00',
}


class GulfLiveFeedTests(unittest.TestCase):
    def test_uae_module_entrypoint_executes_main(self):
        source = (ROOT / 'src/uae_mof_feed.py').read_text(encoding='utf-8')
        self.assertIn('if __name__ == "__main__":', source)
        self.assertIn('main(sys.argv[1])', source)

    def test_uae_table_extracts_official_rows_without_deciding_goods(self):
        rows = parse_uae(UAE_HTML)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['country'], 'United Arab Emirates')
        self.assertEqual(rows[0]['rfq_number'], '12583')
        self.assertNotIn('contract-nature', rows[0])
        self.assertTrue(rows[0]['source_url'].startswith('https://procurement.gov.ae/'))

    def test_uae_rendered_card_layout_is_parsed_from_source_text(self):
        rows = parse_uae(UAE_CARD_HTML)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['rfq_number'], '12583')
        self.assertEqual(rows[0]['buyer-name'], 'Emirates Space Agency - (286/9294)')
        self.assertEqual(rows[0]['title_original'], 'RFP EMM gifts and giveaway for events, csr, and roadshows')
        self.assertEqual(rows[0]['publication-date'], '02/10/2026 10:17:38 AM')
        self.assertEqual(rows[0]['deadline-receipt-tender-date-lot'], '25/10/2026 10:30:00 PM')
        self.assertTrue(rows[0]['source_provenance']['parsed_from_public_listing'])

    def test_uae_card_parser_rejects_unrelated_numbers_without_two_dates(self):
        self.assertEqual(parse_uae('<div>2026</div><div>Ministry of Finance</div><div>Open tenders</div>'), [])

    def test_uae_ministry_filter_values_are_discovered_from_official_form(self):
        values = discover_ministry_filters(UAE_FILTER_HTML)
        self.assertEqual(values, ['Emirates Space Agency - (286/9294)', 'Ministry of Justice - (121/16896)'])
        url = filtered_page_url(values[0])
        self.assertIn('mof-dpp-ministry=Emirates+Space+Agency', url)
        self.assertIn('mof-dpp-page=1', url)

    def test_uae_uses_server_side_ministry_filter_before_browser(self):
        requested = []
        def fake_fetch(url):
            requested.append(url)
            if 'mof-dpp-ministry=' in url:
                return UAE_HTML
            if url.startswith(SOURCE_URL):
                return UAE_FILTER_HTML
            return '<html></html>'
        with patch('src.uae_mof_feed._fetch_url', side_effect=fake_fetch), patch('src.uae_mof_feed.dump_dom') as browser:
            rows, meta = collect_uae(max_pages=1)
        self.assertEqual(len(rows), 2)
        self.assertEqual(meta['successful_route'], 'en:server_filter')
        self.assertEqual(meta['ministry_filters_discovered']['en'], 2)
        browser.assert_not_called()

    def test_uae_http_client_uses_normal_browser_identity(self):
        self.assertTrue(BROWSER_USER_AGENT.startswith('Mozilla/5.0'))
        self.assertIn('Chrome/', BROWSER_USER_AGENT)
        self.assertNotIn('GlobalBrokerAI', BROWSER_USER_AGENT)

    def test_uae_uses_headless_dom_when_server_html_has_no_rows(self):
        with patch('src.uae_mof_feed._fetch_url', return_value='<html></html>'), patch('src.uae_mof_feed.dump_dom', return_value=UAE_HTML):
            rows, meta = collect_uae(max_pages=1)
        self.assertEqual(len(rows), 2)
        self.assertTrue(meta['rendered_fallback_used'])
        self.assertEqual(meta['browser_fallback_pages'], ['en:1'])

    def test_uae_tries_arabic_official_route_when_english_is_empty(self):
        def fake_fetch(url):
            return UAE_HTML if url.startswith(AR_SOURCE_URL) else '<html></html>'
        with patch('src.uae_mof_feed._fetch_url', side_effect=fake_fetch), patch('src.uae_mof_feed.dump_dom', return_value='<html></html>'):
            rows, meta = collect_uae(max_pages=1)
        self.assertEqual(len(rows), 2)
        self.assertEqual(meta['successful_route'], 'ar')

    def test_uae_empty_first_page_stops_before_second_page(self):
        requested = []
        def fake_fetch(url):
            requested.append(url)
            return '<html></html>'
        with patch('src.uae_mof_feed._fetch_url', side_effect=fake_fetch), patch('src.uae_mof_feed.dump_dom', return_value='<html></html>'):
            rows, meta = collect_uae(max_pages=4)
        self.assertEqual(rows, [])
        self.assertFalse(any('mof-dpp-page=2' in url for url in requested))
        self.assertTrue(meta['rendered_fallback_used'])

    def test_browser_timeout_preserves_emitted_dom(self):
        timeout = subprocess.TimeoutExpired(['chrome'], 1, output='<html><body>ready</body></html>')
        with patch('src.browser_render.find_browser', return_value='/usr/bin/google-chrome'), patch('src.browser_render.subprocess.run', side_effect=timeout):
            self.assertIn('ready', dump_dom('https://example.invalid', timeout_seconds=1))

    def test_saudi_official_json_record_maps_only_source_fields(self):
        row = _api_record(SAUDI_API_ITEM, 'https://tenders.etimad.sa/Tender/AllSupplierTendersForVisitorAsync?PageNumber=1')
        self.assertEqual(row['reference_number'], '260239009999')
        self.assertEqual(row['country'], 'Saudi Arabia')
        self.assertEqual(row['buyer-name'], 'وزارة الصناعة')
        self.assertEqual(row['deadline-receipt-tender-date-lot'], '2026-10-25T12:00:00')
        self.assertTrue(row['source_provenance']['parsed_from_official_json_endpoint'])
        self.assertFalse(row['foreign_supplier_eligibility_assumed'])

    def test_saudi_collection_prefers_official_json_api(self):
        with patch('src.saudi_etimad_feed.collect_api', return_value=([_api_record(SAUDI_API_ITEM, 'https://tenders.etimad.sa/Tender/AllSupplierTendersForVisitorAsync?PageNumber=1')], {'api_records': 1})), patch('src.saudi_etimad_feed.collect_html') as html_fallback:
            rows, meta = collect()
        self.assertEqual(len(rows), 1)
        self.assertEqual(meta['collection_path'], 'official_json_api')
        html_fallback.assert_not_called()

    def test_saudi_listing_deduplicates_detail_links(self):
        links = discover_detail_links(SAUDI_LIST)
        self.assertEqual(len(links), 1)
        self.assertIn('DetailsForVisitor?STenderId=', links[0])

    def test_saudi_rendered_dom_recovers_detail_url_outside_anchor(self):
        links = discover_detail_links(SAUDI_RENDERED_URL)
        self.assertEqual(len(links), 1)
        self.assertIn('STenderId=xyz%3D%3D', links[0])

    def test_saudi_active_detail_is_parsed_but_ended_is_rejected(self):
        row = parse_detail(SAUDI_DETAIL, 'https://tenders.etimad.sa/Tender/DetailsForVisitor?STenderId=x')
        self.assertIsNotNone(row)
        self.assertEqual(row['country'], 'Saudi Arabia')
        self.assertEqual(row['reference_number'], '260239009999')
        self.assertIsNone(parse_detail(SAUDI_ENDED, 'https://tenders.etimad.sa/Tender/DetailsForVisitor?STenderId=x'))


if __name__ == '__main__':
    unittest.main()
