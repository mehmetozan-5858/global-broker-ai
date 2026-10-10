import unittest

from src.qatar_monaqasat_feed import parse, merge_payload


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

    def test_merge_is_deduplicated(self):
        rows=parse(HTML)
        payload={'opportunities':[]}
        merge_payload(payload,rows)
        merge_payload(payload,rows)
        self.assertEqual(len(payload['opportunities']),1)
        self.assertTrue(payload['qatar_monaqasat_feed']['live_ingestion'])


if __name__=='__main__':
    unittest.main()
