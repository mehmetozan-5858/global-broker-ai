import unittest
from unittest.mock import patch

from src.uae_mof_ssr_fallback import apply

HTML='''
<table><tr><th>RFQ Number</th><th>Entity Name</th><th>Title</th><th>Open Date</th><th>Close Date</th><th>Link</th></tr>
<tr><td>12670</td><td>Ministry of Community Empowerment</td><td>Winter programme materials</td><td>09/10/2026 9:15:05 AM</td><td>30/10/2026 2:30:00 PM</td><td><a href="https://procurement.gov.ae/rfx/12670">Click here</a></td></tr>
</table>
'''


class UaeMofSsrFallbackTests(unittest.TestCase):
    def test_skips_fallback_when_primary_is_live(self):
        payload={'uae_mof_feed':{'live_ingestion':True},'opportunities':[]}
        with patch('src.uae_mof_ssr_fallback._fetch') as fetch:
            apply(payload)
        fetch.assert_not_called()
        self.assertFalse(payload['uae_mof_feed']['ssr_fallback_attempted'])

    def test_marks_success_as_partial_official_coverage(self):
        payload={'uae_mof_feed':{'live_ingestion':False,'added':0},'opportunities':[]}
        with patch('src.uae_mof_ssr_fallback._fetch',return_value=HTML):
            apply(payload)
        feed=payload['uae_mof_feed']
        self.assertTrue(feed['live_ingestion'])
        self.assertEqual(feed['parsed_opportunities'],1)
        self.assertEqual(feed['coverage_scope'],'partial_official_listing')
        self.assertFalse(feed['coverage_complete'])
        self.assertEqual(payload['opportunities'][0]['rfq_number'],'12670')

    def test_network_failure_does_not_fake_live_status(self):
        payload={'uae_mof_feed':{'live_ingestion':False},'opportunities':[]}
        with patch('src.uae_mof_ssr_fallback._fetch',side_effect=OSError('blocked')):
            apply(payload)
        self.assertFalse(payload['uae_mof_feed']['live_ingestion'])
        self.assertEqual(payload['uae_mof_feed']['ssr_fallback_status'],'source_unavailable')


if __name__=='__main__':
    unittest.main()
