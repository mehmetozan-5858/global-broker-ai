"""Offline end-to-end contract for TED daily archive workflow."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

p = Path(__file__).resolve().parents[1] / "scripts" / "review_ted_daily_end_to_end.py"
import sys
sys.path.insert(0, str(p.parent))
spec = importlib.util.spec_from_file_location("review_ted_daily_end_to_end", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class DailyEndToEndTests(unittest.TestCase):
    def test_verified_archive_still_requires_source_completeness(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(mod, "fetch", return_value={"sha256": "a" * 64}) as fetch, patch.object(
                mod, "inspect", return_value={"package_sha256": "a" * 64,
                "publication_number": "718662-2026", "notice_xml_sha256": "b" * 64, "xml_parsed": True,
                "notice_identity_verified": True}) as inspect:
                result = mod.run(2026, 216, "718662-2026", Path(tmp))
                fetch.assert_called_once()
                inspect.assert_called_once()
                self.assertFalse(result["release_accepted"])
                self.assertFalse(result["source_completeness_verified"])
                self.assertTrue((Path(tmp) / "review-evidence.json").exists())

    def test_mismatched_archive_hash_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(mod, "fetch", return_value={"sha256": "a" * 64}), patch.object(
                mod, "inspect", return_value={"package_sha256": "b" * 64,
                "publication_number": "718662-2026", "notice_xml_sha256": "c" * 64, "xml_parsed": True,
                "notice_identity_verified": True}):
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    mod.run(2026, 216, "718662-2026", Path(tmp))
                self.assertFalse((Path(tmp) / "review-evidence.json").exists())

    def test_wrong_notice_identity_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(mod, "fetch", return_value={"sha256": "a" * 64}), patch.object(
                mod, "inspect", return_value={"package_sha256": "a" * 64,
                "publication_number": "718664-2026",
                "notice_xml_sha256": "b" * 64, "xml_parsed": True,
                "notice_identity_verified": True}):
                with self.assertRaisesRegex(ValueError, "identity"):
                    mod.run(2026, 216, "718662-2026", Path(tmp))
                self.assertFalse((Path(tmp) / "review-evidence.json").exists())

    def test_existing_evidence_json_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence_path = Path(tmp) / "review-evidence.json"
            evidence_path.write_text("previous-review", encoding="utf-8")
            with patch.object(mod, "fetch", return_value={"sha256": "a" * 64}), patch.object(
                mod, "inspect", return_value={"package_sha256": "a" * 64,
                "publication_number": "718662-2026", "notice_xml_sha256": "b" * 64,
                "xml_parsed": True, "notice_identity_verified": True}):
                with self.assertRaises(FileExistsError):
                    mod.run(2026, 216, "718662-2026", Path(tmp))
            self.assertEqual(evidence_path.read_text(encoding="utf-8"), "previous-review")

    def test_mismatched_year_rejected_before_network(self):
        with patch.object(mod, "fetch") as fetch:
            with self.assertRaisesRegex(ValueError, "year"):
                mod.run(2026, 216, "718662-2025", Path("/tmp/unused"))
            fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
