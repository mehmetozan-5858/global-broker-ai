import unittest

from src.private_snapshot_identity_gate import (
    PrivateSnapshotIdentityError, inspect_private_snapshot,
    require_unique_private_snapshot,
)


class PrivateSnapshotIdentityGateTests(unittest.TestCase):
    def test_unique_rows_pass(self):
        result = require_unique_private_snapshot([
            {"opportunity_id": "notice-1", "title": "Synthetic A", "source":"synthetic"},
            {"opportunity_id": "notice-2", "title": "Synthetic B", "source":"synthetic"},
        ])
        self.assertEqual(result["rows"], 2)
        self.assertEqual(result["duplicate_identity_count"], 0)

    def test_same_identity_same_content_is_not_silently_deduplicated(self):
        row = {"opportunity_id": "repeat", "title": "Synthetic", "source":"synthetic"}
        report = inspect_private_snapshot([row, dict(row)])
        self.assertEqual(report["duplicate_identity_count"], 1)
        self.assertEqual(report["conflicting_identity_count"], 0)
        self.assertEqual(report["same_or_unknown_source_duplicate_count"], 1)
        self.assertEqual(report["cross_source_collision_count"], 0)
        with self.assertRaisesRegex(PrivateSnapshotIdentityError, "duplicate_opportunity_id"):
            require_unique_private_snapshot([row, dict(row)])

    def test_conflicting_identity_blocks_snapshot_without_exposing_contact(self):
        rows = [
            {"opportunity_id": "private-id-94f", "contact_email": "private@example.test", "source":"synthetic"},
            {"opportunity_id": "private-id-94f", "contact_email": "different@example.test", "source":"synthetic"},
        ]
        report = inspect_private_snapshot(rows)
        self.assertEqual(report["conflicting_identity_count"], 1)
        with self.assertRaises(PrivateSnapshotIdentityError) as error:
            require_unique_private_snapshot(rows)
        self.assertNotIn("private@example.test", str(error.exception))
        self.assertNotIn("private-id-94f", str(error.exception))

    def test_empty_missing_and_over_cap_fail_closed(self):
        for rows in ([], None, [{"title": "No ID"}], [{}] * 1001):
            with self.subTest(rows_type=type(rows).__name__):
                with self.assertRaises(PrivateSnapshotIdentityError):
                    require_unique_private_snapshot(rows)

    def test_two_official_sources_with_same_notice_number_block_until_identity_review(self):
        # The legacy stable ID is not source-namespaced. This is a *risk
        # demonstration*, not permission to silently re-key existing records.
        from src.opportunity_identity import stable_opportunity_id
        a = {"source": "official-portal-A", "notice_id": "common-number", "title": "A"}
        b = {"source": "official-portal-B", "notice_id": "common-number", "title": "B"}
        self.assertEqual(stable_opportunity_id(a), stable_opportunity_id(b))
        for row in (a, b):
            row["opportunity_id"] = stable_opportunity_id(row)
        report=inspect_private_snapshot([a,b])
        self.assertEqual(report['cross_source_collision_count'],1)
        self.assertEqual(report['same_or_unknown_source_duplicate_count'],0)
        with self.assertRaises(PrivateSnapshotIdentityError):
            require_unique_private_snapshot([a, b])

    def test_source_missing_rejected_without_printing_private_identifiers(self):
        rows=[{"opportunity_id":"private-sensitive-id","title":"private notice"}]
        result=inspect_private_snapshot(rows)
        self.assertEqual(result['missing_source_provenance_count'],1)
        with self.assertRaises(PrivateSnapshotIdentityError) as exc:
            require_unique_private_snapshot(rows)
        self.assertIn('missing_source_provenance',str(exc.exception))
        self.assertNotIn('private-sensitive-id',str(exc.exception))

    def test_reject_overlong_or_nonstring_identity_without_leaking_value(self):
        for raw in ['x'*201, {'private':'sensitive'}, ['private'], 3]:
            with self.subTest(type=type(raw).__name__):
                rows=[{'opportunity_id':raw,'source':'synthetic'}]
                with self.assertRaisesRegex(PrivateSnapshotIdentityError,'invalid_opportunity_id') as err:
                    require_unique_private_snapshot(rows)
                self.assertNotIn('sensitive',str(err.exception))

    def test_payload_cap_is_not_bypassed_by_repeat_id(self):
        row = {"opportunity_id": "same-synthetic-notice"}
        with self.assertRaises(PrivateSnapshotIdentityError):
            require_unique_private_snapshot([row] * 1001)


if __name__ == "__main__":
    unittest.main()
