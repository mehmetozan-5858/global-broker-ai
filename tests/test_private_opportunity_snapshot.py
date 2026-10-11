import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PrivateOpportunitySnapshotTests(unittest.TestCase):
    def test_snapshot_refuses_empty_payload_and_archives_stale_rows(self):
        sql = (ROOT / "sql/private_opportunity_snapshot.sql").read_text(encoding="utf-8")
        self.assertIn("gb_replace_private_opportunities", sql)
        self.assertIn("empty_snapshot_refused", sql)
        self.assertIn("private.opportunity_archive", sql)
        self.assertIn("stale_snapshot", sql)
        self.assertIn("delete from private.opportunities", sql.lower())

    def test_snapshot_preserves_rows_referenced_by_introductions(self):
        sql = (ROOT / "sql/private_opportunity_snapshot.sql").read_text(encoding="utf-8")
        self.assertIn("private.introduction_requests", sql)
        self.assertIn("r.opportunity_id=p.id", sql.replace(" ", ""))
        self.assertIn("preserved_referenced", sql)

    def test_snapshot_replace_is_service_only(self):
        sql = (ROOT / "sql/private_opportunity_snapshot.sql").read_text(encoding="utf-8").lower()
        self.assertIn("revoke all on function public.gb_replace_private_opportunities(jsonb) from public,anon,authenticated", sql)
        self.assertIn("grant execute on function public.gb_replace_private_opportunities(jsonb) to service_role", sql)


if __name__ == "__main__":
    unittest.main()
