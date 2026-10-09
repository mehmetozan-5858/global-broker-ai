import unittest
from src.build_ceo_report import build_report

class CeoReportTests(unittest.TestCase):
    def test_empty_feed_has_no_invented_sales(self):
        x = build_report({"opportunities":[]})
        self.assertEqual(x["count"],0)
        self.assertEqual(x["new_verified_sales"],0)
        self.assertIsNone(x["realized_commission"])

    def test_one_notice_is_review_not_sale(self):
        x = build_report({"opportunities":[{"source":"TED","id":"N1","title_original":"cable",
                             "buyer-name":"Example","buyer-country":"Germany"}]})
        self.assertEqual(x["count"],1)
        self.assertEqual(len(x["groups"]["route_pending"]),1)
        self.assertFalse(x["external_actions_allowed"])

if __name__ == "__main__":
    unittest.main()
