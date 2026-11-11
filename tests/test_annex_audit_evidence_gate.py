import copy
import hashlib
import unittest
from src.annex_audit_evidence_gate import reconcile_annex_audit


class AnnexAuditEvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.extraction = {
            "attachment_candidates_observed": 2,
            "attachment_inventory_entries_omitted": 0,
            "attachment_inventory": [
                {"kind": "pdf", "status": "parsed"},
                {"kind": "xlsx", "status": "unsupported", "url": "https://example.org/annex.xlsx"},
            ],
        }
        self.audit = {
            "ordinary_reader_parsed": 1,
            "ordinary_reader_limits_unchanged": True,
            "audited_remaining": [{
                "index": 1, "format": "xlsx", "status": "read_for_review",
                "sha256": "a" * 64,
                "source_url_sha256": hashlib.sha256(b"https://example.org/annex.xlsx").hexdigest(), "bytes": 100, "text_chars": 25,
                "text_truncated": False, "formula_cells": 13,
                "formula_evaluation_performed": False,
                "formula_approval": False, "formula_review_required": True,
            }],
            "commercial_approval": False, "supplier_sourcing_ready": False,
            "applicable_revision_selected": False,
            "all_mandatory_requirements_reviewed": False,
        }

    def test_valid_review_stays_commercially_blocked(self):
        result = reconcile_annex_audit(self.extraction, self.audit)
        self.assertTrue(result["audit_evidence_valid"])
        self.assertEqual(result["audit_reviewed_count"], 1)
        self.assertTrue(result["formula_review_required"])
        self.assertTrue(result["revision_review_required"])
        self.assertFalse(result["supplier_sourcing_ready"])
        self.assertFalse(result["commercial_approval"])

    def test_missing_spoofed_or_incomplete_evidence_fails_closed(self):
        for field, value in [
            ("commercial_approval", True), ("supplier_sourcing_ready", True),
            ("applicable_revision_selected", True),
            ("ordinary_reader_limits_unchanged", False),
            ("ordinary_reader_parsed", True),
            ("audited_remaining", []),
        ]:
            audit = copy.deepcopy(self.audit)
            audit[field] = value
            with self.subTest(field=field):
                self.assertFalse(reconcile_annex_audit(self.extraction, audit)["audit_evidence_valid"])
        for key, value in [("index", 2), ("index", True), ("format", "doc"), ("sha256", "no"),
                           ("formula_approval", True), ("text_truncated", True),
                           ("formula_evaluation_performed", True), ("source_url_sha256", "b" * 64)]:
            audit = copy.deepcopy(self.audit)
            audit["audited_remaining"][0][key] = value
            with self.subTest(key=key):
                self.assertFalse(reconcile_annex_audit(self.extraction, audit)["audit_evidence_valid"])


    def test_changed_source_url_cannot_reuse_old_audit_proof(self):
        extraction = copy.deepcopy(self.extraction)
        extraction["attachment_inventory"][1]["url"] = "https://example.org/replacement.xlsx"
        result = reconcile_annex_audit(extraction, self.audit)
        self.assertFalse(result["audit_evidence_valid"])
        self.assertFalse(result["supplier_sourcing_ready"])
        self.assertFalse(result["commercial_approval"])

    def test_valid_url_hash_is_not_commercial_or_content_attestation(self):
        result = reconcile_annex_audit(self.extraction, self.audit)
        self.assertTrue(result["audit_evidence_valid"])
        self.assertTrue(result["formula_review_required"])
        self.assertTrue(result["revision_review_required"])
        self.assertFalse(result["all_mandatory_requirements_reviewed"])
        self.assertFalse(result["commercial_approval"])

    def test_missing_inventory_and_mismatched_counts_rejected(self):
        self.assertFalse(reconcile_annex_audit({}, self.audit)["audit_evidence_valid"])
        extraction = copy.deepcopy(self.extraction)
        extraction["attachment_inventory_entries_omitted"] = 1
        self.assertFalse(reconcile_annex_audit(extraction, self.audit)["audit_evidence_valid"])


if __name__ == "__main__":
    unittest.main()
