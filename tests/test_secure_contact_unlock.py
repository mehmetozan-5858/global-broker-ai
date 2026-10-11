import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SecureContactUnlockTests(unittest.TestCase):
    def test_api_uses_private_supabase_rpc_not_public_feed(self):
        code = (ROOT / "api/contact_unlock.py").read_text(encoding="utf-8")
        self.assertIn("/rest/v1/rpc/unlock_opportunity_contact", code)
        self.assertNotIn("latest-opportunities.json", code)
        self.assertNotIn("stable_opportunity_id", code)
        self.assertIn('"quality_score"', code)
        self.assertIn('"route_type"', code)

    def test_rpc_checks_route_before_debit(self):
        sql = (ROOT / "sql/secure_private_contact_unlock_v2.sql").read_text(encoding="utf-8")
        route_idx = sql.index("contact_not_available")
        debit_idx = sql.index("contact_credits_remaining=contact_credits_remaining-1")
        self.assertLess(route_idx, debit_idx)
        self.assertIn("private.opportunities", sql)
        self.assertIn("private.contact_unlocks", sql)
        self.assertIn("quality_level", sql)
        self.assertIn("official_source_route", sql)

    def test_repeat_unlock_is_idempotent(self):
        sql = (ROOT / "sql/secure_private_contact_unlock_v2.sql").read_text(encoding="utf-8")
        self.assertIn("already_unlocked", sql)
        self.assertIn("select exists", sql.lower())
        self.assertIn("if already then", sql.lower())


if __name__ == "__main__":
    unittest.main()
