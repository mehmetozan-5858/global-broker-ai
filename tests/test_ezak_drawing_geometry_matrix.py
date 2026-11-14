"""Offline structural checks for manually transcribed official E-ZAK geometry.
These tests verify consistency, not source accuracy or supplier compliance.
"""
import json
from pathlib import Path
import unittest

MATRIX = Path(__file__).resolve().parents[1] / "reviews" / "ted-702997-2026-drawing-geometry-matrix.json"


class DrawingGeometryMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(MATRIX.read_text(encoding="utf-8"))

    def test_twelve_site_rows_and_27_new_tanks(self):
        rows = self.data["rows"]
        self.assertEqual(len(rows), 12)
        self.assertEqual(sum(row["count"] for row in rows), 27)
        self.assertEqual(sum(row["min_volume_l"] * row["count"] for row in rows), 417_000)
        self.assertEqual({row["page"] for row in rows}, set(range(1, 13)))

    def test_drawing_dimension_envelopes_only(self):
        for row in self.data["rows"]:
            with self.subTest(site=row["site"]):
                self.assertEqual(row["drawn_new_tanks"], row["count"])
                self.assertLessEqual(row["drawing_diameter_mm"], row["max_diameter_mm"])
                self.assertLessEqual(row["drawing_height_mm"], row["max_height_mm"])
                self.assertFalse(row["capacity_verified"])

    def test_acceptance_is_explicitly_closed(self):
        self.assertFalse(self.data["technical_approval"])
        self.assertFalse(self.data["commercial_approval"])


if __name__ == "__main__":
    unittest.main()
