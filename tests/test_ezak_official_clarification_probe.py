"""Offline metadata-only E-ZAK clarification checks."""
import unittest
from scripts.ezak_official_clarification_probe import summarize


class ClarificationProbeTests(unittest.TestCase):
    def test_extracts_section_dates_without_exposing_document_content(self):
        sample = """<html><body>
          <h2>Vysvětlení, doplnění, změny zadávací dokumentace</h2>
          <table><tr><td>29.10.2026</td><td>Private technical text</td></tr>
          <tr><td>12.11.2026</td><td>Another technical note</td></tr></table>
          <h2>Veřejné dokumenty</h2><p>13.11.2026</p></body></html>"""
        result = summarize(sample.encode())
        self.assertTrue(result["official_page_section_detected"])
        self.assertEqual(result["dated_explanation_entries_observed"], 2)
        self.assertEqual(result["observed_dates"], ["12.11.2026", "29.10.2026"])
        self.assertNotIn("Private", str(result))
        self.assertFalse(result["authoritative_revision_verified"])
        self.assertFalse(result["clarifications_complete"])

    def test_missing_section_is_unknown_not_zero_approved(self):
        result = summarize(b"<html><body>index only</body></html>")
        self.assertFalse(result["official_page_section_detected"])
        self.assertEqual(result["dated_explanation_entries_observed"], 0)
        self.assertFalse(result["technical_approval"])


if __name__ == "__main__":
    unittest.main()
