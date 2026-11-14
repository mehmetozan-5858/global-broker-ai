import contextlib
import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.private_snapshot_diagnostic import diagnose_local_snapshot
from src.private_snapshot_identity_gate import PrivateSnapshotIdentityError


class NoWritePrivateDiagnosticTests(unittest.TestCase):
    def _row(self, identifier, source):
        return {
            "opportunity_id": identifier,
            "source": source,
            "export_goods_review": {"status": "goods_candidate"},
            "contact_email": "private@example.test",
        }

    def test_clean_snapshot_leaves_private_input_byte_identical(self):
        with TemporaryDirectory() as folder:
            private = Path(folder) / "private.json"
            aggregate = Path(folder) / "aggregate.json"
            private.write_text(json.dumps({"opportunities": [
                self._row("synthetic-a", "official-a"),
                self._row("synthetic-b", "official-b"),
            ]}), encoding="utf-8")
            original = private.read_bytes()
            capture = io.StringIO()
            with contextlib.redirect_stdout(capture):
                summary = diagnose_local_snapshot(private, aggregate)
            self.assertEqual(private.read_bytes(), original)
            self.assertEqual(summary["rows"], 2)
            self.assertEqual(summary["duplicate_groups"], 0)
            self.assertFalse(summary["accepted_for_remote_write"])
            output = aggregate.read_text(encoding="utf-8")
            for secret in ("private@example.test", "synthetic-a", "official-a"):
                self.assertNotIn(secret, output)
                self.assertNotIn(secret, capture.getvalue())

    def test_colliding_snapshot_fails_but_writes_only_safe_aggregate(self):
        with TemporaryDirectory() as folder:
            private = Path(folder) / "private.json"
            aggregate = Path(folder) / "aggregate.json"
            private.write_text(json.dumps({"opportunities": [
                self._row("private-duplicate", "official-a"),
                self._row("private-duplicate", "official-b"),
            ]}), encoding="utf-8")
            original = private.read_bytes()
            with self.assertRaisesRegex(PrivateSnapshotIdentityError, "duplicate_opportunity_id"):
                diagnose_local_snapshot(private, aggregate)
            self.assertEqual(original, private.read_bytes())
            report = json.loads(aggregate.read_text(encoding="utf-8"))
            self.assertEqual(report["duplicate_groups"], 1)
            self.assertEqual(report["cross_source_groups"], 1)
            self.assertFalse(report["accepted_for_remote_write"])
            for secret in ("private-duplicate", "private@example.test", "official-a"):
                self.assertNotIn(secret, aggregate.read_text(encoding="utf-8"))

    def test_invalid_primary_id_not_sanitized_by_preparation(self):
        with TemporaryDirectory() as folder:
            private = Path(folder) / "private.json"
            private.write_text(json.dumps({"opportunities": [
                dict(self._row("private-secret", "official-a"), opportunity_id="")
            ]}), encoding="utf-8")
            original = private.read_bytes()
            with self.assertRaisesRegex(PrivateSnapshotIdentityError, "invalid_opportunity_id"):
                diagnose_local_snapshot(private)
            self.assertEqual(original, private.read_bytes())

    def test_missing_snapshot_and_empty_rows_fail_closed(self):
        with TemporaryDirectory() as folder:
            private = Path(folder) / "private.json"
            for payload in ({"opportunities": []}, {"opportunities": None}, []):
                private.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaises(PrivateSnapshotIdentityError):
                    diagnose_local_snapshot(private)


if __name__ == "__main__":
    unittest.main()
