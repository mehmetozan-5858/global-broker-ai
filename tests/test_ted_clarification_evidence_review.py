"""A reviewable source claim can never authorize resolving the TED hold."""
import copy
import unittest
from scripts.ted_clarification_evidence_review import review_candidate


def synthetic():
    return {
        "notice": "746528-2026",
        "site": "Slavkov u Brna",
        "official_url": "https://zakazky.krajbezkorupce.cz/document_download_123456.html",
        "sha256": "a" * 64,
        "official_publication_date": "2026-11-14",
        "reviewer": "Independent Engineer",
        "corrected_requirements": {
            "minimum_volume_l": 15000,
            "maximum_diameter_mm": 2450,
            "maximum_height_mm": 3500,
        },
    }


class ClarificationIntakeTests(unittest.TestCase):
    def test_perfect_looking_claim_never_approves_or_releases(self):
        for site in ("Slavkov u Brna", "Veselí nad Moravou"):
            row = synthetic()
            row["site"] = site
            result = review_candidate(row)
            self.assertEqual(result["status"], "NEEDS_INDEPENDENT_SOURCE_REVIEW")
            self.assertTrue(result["metadata_complete"])
            for flag in ("source_content_verified", "authoritative_revision_verified",
                         "capacity_conflict_resolved", "technical_approval",
                         "commercial_approval", "quarantine_release_authorized"):
                self.assertFalse(result[flag])

    def test_missing_or_forged_claims_are_incomplete(self):
        base = synthetic()
        cases = [
            {"official_url": "https://zakazky.krajbezkorupce.cz.attacker.invalid/file"},
            {"official_url": "http://zakazky.krajbezkorupce.cz/file"},
            {"notice": "000000-2026"},
            {"site": "Unknown town"},
            {"sha256": "not-a-sha"},
            {"reviewer": ""},
            {"corrected_requirements": {"minimum_volume_l": 15000}},
            {"corrected_requirements": dict(base["corrected_requirements"], maximum_height_mm=True)},
        ]
        for alteration in cases:
            with self.subTest(alteration=alteration):
                row = copy.deepcopy(base)
                row.update(alteration)
                result = review_candidate(row)
                self.assertEqual(result["status"], "INVALID_OR_INCOMPLETE")
                self.assertFalse(result["quarantine_release_authorized"])

    def test_user_supplied_approval_claims_do_not_change_decision(self):
        row = synthetic()
        row.update(technical_approval=True, commercial_approval=True, quarantine_release_authorized=True)
        result = review_candidate(row)
        self.assertFalse(result["technical_approval"])
        self.assertFalse(result["quarantine_release_authorized"])


if __name__ == "__main__":
    unittest.main()
