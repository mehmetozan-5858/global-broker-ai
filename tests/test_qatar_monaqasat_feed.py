import unittest
from unittest.mock import patch

from src.qatar_monaqasat_feed import ALT_SOURCE_URL, SOURCE_URL, collect, merge_payload, parse


HTML='''
<html><body>
<div>4886/2026 SUPPLY OF MEDICAL CONSUMABLES</div>
<div>Publish date 27/09/2026</div>
<div>Requested Sector Type Suppliers / Service Providers</div>
<div>Tender Bond (QAR) 50,000.00</div>
<div>Documents value (QR) 500.00</div>
<div>Ministry Hamad Medical Corporation</div>
<div>Type Public Tender</div>
<div>Close date 26/10/2026 Purchase</div>
<div>4888/2026 Provision of Event Organization and Setup Services</div>
<div>Publish date 27/09/2026</div>
<div>Tender Bond (QAR) 8,000.00</div>
<div>Ministry Qatar University</div>
<div>Type Public Tender</div>
<div>Close date 07/10/2026 Purchase</div>
</body></html>
'''

AR_HTML='''
<html><body>
<div>4901/2026 توريد أجهزة مخبرية</div>
<div>تاريخ الطرح 08/10/2026</div>
<div>نوع القطاع المطلوب موردين / مقدمى خدمات</div>
<div>التأمين المؤقت 32,000.00</div>
<div>قيمة الوثائق 500.00</div>
<div>الجهة كلية المجتمع</div>
<div>النوع مناقصة عامة</div>
<div>تاريخ الإغلاق 02/11/2026 شراء</div>
</body></html>
'''


class QatarMonaqasatFeedTests(unittest.TestCase):
    def test_only_clear_goods_are_parsed(self):
        rows=parse(HTML)
        self.assertEqual(len(rows),1)
        row=rows[0]
        self.assertEqual(row['buyer-country'],'Qatar')
        self.assertEqual(row['contract-nature'],'supplies')
        self.assertIn('MEDICAL CONSUMABLES',row['title_original'])
        self.assertEqual(row['bid_bond'],'QAR 50,000.00')
        self.assertFalse(row.get('foreign_supplier_eligibility_assumed',False))

    def test_arabic_public_route_is_parseable(self):
        rows=parse(AR_HTML, ALT_SOURCE_URL)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['buyer-country'],'Qatar')
        self.assertIn('توريد',rows[0]['title_original'])
        self.assertEqual(rows[0]['source_provenance']['source'],ALT_SOURCE_URL)

    def test_collect_falls_back_to_alternate_public_route(self):
        def fake_fetch(url, timeout=18):
            if url == SOURCE_URL:
                raise OSError('blocked')
            return AR_HTML
        with patch('src.qatar_monaqasat_feed._fetch', side_effect=fake_fetch), patch('src.qatar_monaqasat_feed.time.sleep'):
            rows,meta=collect()
        self.assertEqual(len(rows),1)
        self.assertEqual(meta['successful_route'],ALT_SOURCE_URL)
        self.assertGreaterEqual(meta['attempts'],3)

    def test_merge_is_deduplicated(self):
        rows=parse(HTML)
        payload={'opportunities':[]}
        merge_payload(payload,rows,{'successful_route':SOURCE_URL,'attempts':1,'errors':[]})
        merge_payload(payload,rows,{'successful_route':SOURCE_URL,'attempts':1,'errors':[]})
        self.assertEqual(len(payload['opportunities']),1)
        self.assertTrue(payload['qatar_monaqasat_feed']['live_ingestion'])


if __name__=='__main__':
    unittest.main()
