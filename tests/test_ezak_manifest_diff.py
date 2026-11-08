"""Regression tests for E-ZAK revision detection."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "scripts" / "ezak_manifest_diff.py"
spec = importlib.util.spec_from_file_location("ezak_manifest_diff", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def manifest(items):
    return {"ezak_dbid": 47078, "source_index": "https://zakazky.krajbezkorupce.cz/contract_display_47078.html",
            "records": [{"source_url": u, "sha256": h} for u, h in items]}


class RevisionTests(unittest.TestCase):
    def test_unchanged(self):
        a = manifest([("a", "1")])
        self.assertEqual(mod.compare(a, a)["changed"], [])
        self.assertFalse(mod.compare(a, a)["technical_approval"])

    def test_added_removed_and_changed(self):
        result = mod.compare(manifest([("a", "1"), ("b", "2")]),
                             manifest([("a", "9"), ("c", "3")]))
        self.assertEqual(result["added"], ["c"])
        self.assertEqual(result["removed"], ["b"])
        self.assertEqual(result["changed"], ["a"])

    def test_incomplete_and_duplicate_fail_closed(self):
        for bad in (manifest([]), {"ezak_dbid": 47078, "source_index": "x", "records": []},
                    manifest([("a", "1"), ("a", "2")])):
            with self.assertRaises(ValueError):
                mod.compare(manifest([("a", "1")]), bad)

    def test_source_identity_change_rejected(self):
        other = manifest([("a", "1")])
        other["ezak_dbid"] = 99
        with self.assertRaises(ValueError):
            mod.compare(manifest([("a", "1")]), other)


if __name__ == "__main__":
    unittest.main()
