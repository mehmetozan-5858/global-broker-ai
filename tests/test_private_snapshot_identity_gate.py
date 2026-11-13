import unittest

from src.private_snapshot_identity_gate import (
    PrivateSnapshotIdentityError, inspect_private_snapshot,
    require_unique_private_snapshot,
)


class PrivateSnapshotIdentityGateTests(unittest.TestCase):
    def test_unique_rows_pass(self):
        result = require_unique_private_snapshot([
            {"opportunity_id": "notice-1", "title": "Synthetic A"},
            {"opportunity_id": "notice-2", "title": "Synthetic B"},
        ])
        self.assertEqual(result["rows"], 2)
        self.assertEqual(result["duplicate_identity_count"], 0)

    def test_same_identity_same_content_is_not_silently_deduplicated(self):
        row = {"opportunity_id": "repeat", "title": "Synthetic"}
        report = inspect_private_snapshot([row, dict(row)])
        self.assertEqual(report["duplicate_identity_count"], 1)
        self.assertEqual(report["conflicting_identity_count"], 0)
        with self.assertRaisesRegex(PrivateSnapshotIdentityError, "duplicate_opportunity_id"):
            require_unique_private_snapshot([row, dict(row)])

    def test_conflicting_identity_blocks_snapshot_without_exposing_contact(self):
        rows = [
            {"opportunity_id": "repeat", "contact_email": "private@example.test"},
            {"opportunity_id": "repeat", "contact_email": "different@example.test"},
        ]
        report = inspect_private_snapshot(rows)
        self.assertEqual(report["conflicting_identity_count"], 1)
        with self.assertRaises(PrivateSnapshotIdentityError) as error:
            require_unique_private_snapshot(rows)
        self.assertNotIn("private@example.test", str(error.exception))
        self.assertNotIn("repeat", str(error.exception))

    def test_empty_missing_and_over_cap_fail_closed(self):
        for rows in ([], None, [{"title": "No ID"}], [{}] * 1001):
            with self.subTest(rows_type=type(rows).__name__):
                with self.assertRaises(PrivateSnapshotIdentityError):
                    require_unique_private_snapshot(rows)


if __name__ == "__main__":
    unittest.main()
