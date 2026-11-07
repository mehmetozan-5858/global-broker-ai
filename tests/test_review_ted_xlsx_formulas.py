"""Offline fail-closed checks for the TED 702997-2026 workbook review tool."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "review_ted_xlsx_formulas.py"
spec = importlib.util.spec_from_file_location("review_ted_xlsx_formulas", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WorkbookIdentityTests(unittest.TestCase):
    def test_missing_workbook_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "Missing or oversized"):
                module.inspect(Path(directory) / "missing.xlsx")

    def test_different_workbook_is_rejected_before_openpyxl(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "annex.xlsx"
            path.write_bytes(b"not the authoritative workbook")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                module.inspect(path)

    def test_oversized_workbook_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oversized.xlsx"
            with path.open("wb") as handle:
                handle.truncate(module.MAX_BYTES + 1)
            with self.assertRaisesRegex(ValueError, "Missing or oversized"):
                module.inspect(path)

    def test_expected_identity_and_formula_count_are_pinned(self):
        self.assertEqual(len(module.EXPECTED_SHA256), 64)
        self.assertEqual(module.EXPECTED_FORMULAS, 13)


if __name__ == "__main__":
    unittest.main()
