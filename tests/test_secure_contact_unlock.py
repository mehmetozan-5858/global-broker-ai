import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ControlledIntroductionTests(unittest.TestCase):
    def test_direct_contact_unlock_endpoint_is_disabled(self):
        code = (ROOT / "api/contact_unlock.py").read_text(encoding="utf-8")
        self.assertIn("DIRECT_CONTACT_UNLOCK_DISABLED", code)
        self.assertNotIn("unlock_opportunity_contact", code)

    def test_introduction_api_uses_request_rpc_and_returns_no_contact(self):
        code = (ROOT / "api/introduction.py").read_text(encoding="utf-8")
        self.assertIn("/rest/v1/rpc/request_introduction", code)
        self.assertIn('"request_id"', code)
        self.assertIn('"request_status"', code)
        self.assertNotIn('"contact"', code)
        self.assertNotIn("latest-opportunities.json", code)

    def test_intro_rpc_is_idempotent_and_refundable(self):
        sql = (ROOT / "sql/introduction_requests.sql").read_text(encoding="utf-8")
        self.assertIn("already_requested", sql)
        self.assertIn("introduction_credit_required", sql)
        self.assertIn("credit_refunded", sql)
        self.assertIn("buyer_consent_pending", sql)
        self.assertIn("set_introduction_status", sql)
        self.assertIn("revoke execute on function public.unlock_opportunity_contact", sql.lower())

    def test_intro_rpc_never_returns_raw_contact_fields(self):
        sql = (ROOT / "sql/introduction_requests.sql").read_text(encoding="utf-8")
        returned = sql[sql.index("create or replace function public.request_introduction"):sql.index("create or replace function public.my_introduction_requests")]
        self.assertNotIn("contact_email", returned)
        self.assertNotIn("contact_phone", returned)
        self.assertNotIn("buyer_website", returned)


if __name__ == "__main__":
    unittest.main()
