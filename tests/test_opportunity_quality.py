import unittest
from datetime import date
from src.opportunity_quality import parse_deadline, assess

TODAY = date(2026, 10, 9)

class OpportunityQualityTests(unittest.TestCase):
    def test_expired_notice(self):
        self.assertEqual(assess({"source":"TED","deadline-receipt-tender-date-lot":"2026-10-08"}, TODAY)["freshness_status"], "expired")
    def test_open_notice_is_not_guaranteed_open(self):
        x = assess({"source":"TED","deadline-receipt-tender-date-lot":"2026-10-20"}, TODAY)
        self.assertEqual(x["freshness_status"], "open_by_date_only")
        self.assertFalse(x["private_buyer_mandate_verified"])
    def test_unknown_deadline_requires_review(self):
        self.assertEqual(assess({"source":"WORLD_BANK"}, TODAY)["freshness_status"], "deadline_unknown_review")
    def test_iso_timestamp(self):
        self.assertEqual(parse_deadline("2026-10-19T18:00:00Z"), date(2026,10,19))
    def test_european_date(self):
        self.assertEqual(parse_deadline("19/10/2026"), date(2026,10,19))
    def test_multiple_lot_deadlines_earliest(self):
        self.assertEqual(parse_deadline(["2026-10-20","2026-10-18"]), date(2026,10,18))
    def test_official_tender_not_private_mandate(self):
        x = assess({"source":"SAM_GOV","source_url":"https://sam.gov/opportunities"}, TODAY)
        self.assertEqual(x["source_type"], "public_procurement_notice")
        self.assertFalse(x["private_buyer_mandate_verified"])
        self.assertEqual(x["outreach_status"], "shadow_not_sent")
    def test_invalid_source_link(self):
        self.assertEqual(assess({"source":"TED","source_url":"javascript:alert(1)"}, TODAY)["source_link_status"], "missing_or_invalid")

if __name__ == "__main__":
    unittest.main()
