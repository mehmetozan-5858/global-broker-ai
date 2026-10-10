import subprocess
import unittest
from unittest.mock import patch

from src.browser_render import dump_dom
from src.saudi_etimad_feed import discover_detail_links, parse_detail
from src.uae_mof_feed import AR_SOURCE_URL
from src.uae_mof_feed import collect as collect_uae
from src.uae_mof_feed import parse as parse_uae


UAE_HTML = '''
<table><tr><th>RFQ Number</th><th>Entity Name</th><th>Title</th><th>Open Date</th><th>Close Date</th><th>Link</th></tr>
<tr><td>12583</td><td>Emirates Space Agency</td><td>Supply of event gifts and giveaway items</td><td>02/10/2026</td><td>25/10/2026</td><td><a href="https://procurement.gov.ae/rfx/12583">Click here</a></td></tr>
<tr><td>12601</td><td>Ministry</td><td>Leadership assessment services</td><td>05/10/2026</td><td>26/10/2026</td><td><a href="https://procurement.gov.ae/rfx/12601">Click here</a></td></tr>
</table>
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


class GulfLiveFeedTests(unittest.TestCase):
    def test_uae_table_extracts_official_rows_without_deciding_goods(self):
        rows = parse_uae(UAE_HTML)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['country'], 'United Arab Emirates')
        self.assertEqual(rows[0]['rfq_number'], '12583')
        self.assertNotIn('contract-nature', rows[0])
        self.assertTrue(rows[0]['source_url'].startswith('https://procurement.gov.ae/'))

    def test_uae_uses_headless_dom_when_server_html_has_no_rows(self):
        with patch('src.uae_mof_feed._fetch_url', return_value='<html></html>'), patch(
            'src.uae_mof_feed.dump_dom', return_value=UAE_HTML
        ):
            rows, meta = collect_uae(max_pages=1)
        self.assertEqual(len(rows), 2)
        self.assertTrue(meta['rendered_fallback_used'])
        self.assertEqual(meta['browser_fallback_pages'], ['en:1'])

    def test_uae_tries_arabic_official_route_when_english_is_empty(self):
        def fake_fetch(url):
            return UAE_HTML if url.startswith(AR_SOURCE_URL) else '<html></html>'
        with patch('src.uae_mof_feed._fetch_url', side_effect=fake_fetch), patch(
            'src.uae_mof_feed.dump_dom', return_value='<html></html>'
        ):
            rows, meta = collect_uae(max_pages=1)
        self.assertEqual(len(rows), 2)
        self.assertEqual(meta['successful_route'], 'ar')

    def test_browser_timeout_preserves_emitted_dom(self):
        timeout = subprocess.TimeoutExpired(['chrome'], 1, output='<html><body>ready</body></html>')
        with patch('src.browser_render.find_browser', return_value='/usr/bin/google-chrome'), patch(
            'src.browser_render.subprocess.run', side_effect=timeout
        ):
            self.assertIn('ready', dump_dom('https://example.invalid', timeout_seconds=1))

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
