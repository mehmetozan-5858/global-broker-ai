"""A reviewable source claim can never authorize resolving the TED hold."""
import copy
import hashlib
import tempfile
from pathlib import Path
import unittest
from scripts.ted_clarification_evidence_review import review_candidate, check_local_evidence_bytes, check_official_manifest_record


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

    def test_local_bytes_match_declared_hash_but_never_establish_authority(self):
        raw = b"synthetic clarification document; not an actual official record"
        row = synthetic()
        row["sha256"] = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            filepath = Path(directory) / "candidate.pdf"
            filepath.write_bytes(raw)
            result = check_local_evidence_bytes(row, filepath)
        self.assertTrue(result["local_bytes_checked"])
        self.assertTrue(result["claimed_sha256_matches_local_bytes"])
        self.assertEqual(result["status"], "NEEDS_INDEPENDENT_SOURCE_REVIEW")
        self.assertFalse(result["source_content_verified"])
        self.assertFalse(result["authoritative_revision_verified"])
        self.assertFalse(result["capacity_conflict_resolved"])
        self.assertFalse(result["quarantine_release_authorized"])

    def test_wrong_local_bytes_and_empty_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            filepath = Path(directory) / "candidate.pdf"
            filepath.write_bytes(b"content that differs")
            mismatch = check_local_evidence_bytes(synthetic(), filepath)
            self.assertEqual(mismatch["status"], "INVALID_OR_INCOMPLETE")
            self.assertIn("claimed_sha256_does_not_match_file", mismatch["errors"])
            filepath.write_bytes(b"")
            empty = check_local_evidence_bytes(synthetic(), filepath)
            self.assertEqual(empty["status"], "INVALID_OR_INCOMPLETE")
            self.assertIn("local_file_missing_or_invalid", empty["errors"])

    def test_oversized_local_bytes_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            filepath = Path(directory) / "too-big.pdf"
            with filepath.open("wb") as stream:
                stream.truncate(12_000_001)
            result = check_local_evidence_bytes(synthetic(), filepath)
            self.assertFalse(result["local_bytes_checked"])
            self.assertFalse(result["quarantine_release_authorized"])
            self.assertEqual(result["status"], "INVALID_OR_INCOMPLETE")

    def test_official_manifest_and_actual_bytes_can_match_without_approval(self):
        raw = b"synthetic document from allowed test host"
        row = synthetic()
        digest = hashlib.sha256(raw).hexdigest()
        row["sha256"] = digest
        filename = f"annex-001-{digest[:16]}.pdf"
        manifest = {
            "notice": "702997-2026",
            "amendment": "746528-2026",
            "ezak_dbid": 47078,
            "source_index": "https://zakazky.krajbezkorupce.cz/contract_display_47078.html",
            "revision_verified": False,
            "complete_annex_set_verified": False,
            "records": [{"source_url": row["official_url"], "sha256": digest, "file": filename,
                         "bytes": len(raw), "accepted": False}],
        }
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / filename).write_bytes(raw)
            result = check_official_manifest_record(row, manifest, directory)
            self.assertTrue(result["manifest_source_record_match"])
            self.assertTrue(result["manifest_file_sha256_match"])
            self.assertEqual(result["status"], "NEEDS_INDEPENDENT_SOURCE_REVIEW")
            self.assertFalse(result["authoritative_revision_verified"])
            self.assertFalse(result["quarantine_release_authorized"])
            altered = copy.deepcopy(manifest)
            altered["records"][0]["file"] = "../other.pdf"
            rejected = check_official_manifest_record(row, altered, directory)
            self.assertEqual(rejected["status"], "INVALID_OR_INCOMPLETE")
            self.assertFalse(rejected["manifest_file_sha256_match"])
            altered = copy.deepcopy(manifest)
            altered["ezak_dbid"] = 99999
            rejected = check_official_manifest_record(row, altered, directory)
            self.assertIn("incorrect_or_unbounded_manifest", rejected["errors"])
            (Path(directory) / filename).write_bytes(b"tampered")
            rejected = check_official_manifest_record(row, manifest, directory)
            self.assertFalse(rejected["manifest_file_sha256_match"])
            self.assertFalse(rejected["quarantine_release_authorized"])

    def test_wrong_document_hash_record_never_matches(self):
        row = synthetic()
        manifest = {
            "notice": "702997-2026", "amendment": "746528-2026", "ezak_dbid": 47078,
            "source_index": "https://zakazky.krajbezkorupce.cz/contract_display_47078.html",
            "revision_verified": False, "complete_annex_set_verified": False,
            "records": [{"source_url": row["official_url"], "sha256": "b" * 64,
                         "file": "annex-001-" + "b" * 16 + ".pdf",
                         "bytes": 9, "accepted": False}],
        }
        result = check_official_manifest_record(row, manifest, ".")
        self.assertEqual(result["status"], "INVALID_OR_INCOMPLETE")
        self.assertIn("unique_manifest_document_record_required", result["errors"])

    def test_user_supplied_approval_claims_do_not_change_decision(self):
        row = synthetic()
        row.update(technical_approval=True, commercial_approval=True, quarantine_release_authorized=True)
        result = review_candidate(row)
        self.assertFalse(result["technical_approval"])
        self.assertFalse(result["quarantine_release_authorized"])


if __name__ == "__main__":
    unittest.main()
