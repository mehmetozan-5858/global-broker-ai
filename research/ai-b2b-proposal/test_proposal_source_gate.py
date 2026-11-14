import unittest
from datetime import date
from proposal_source_gate import verify_source_bound_v9, sha256_text

DAY = date(2026, 11, 14)
QUESTION = "Do you support English?"

def fixture():
    lines = {"L1": "We support English.", "L2": "ISO 27001 expired"}
    canonical = "".join(k + "\t" + lines[k] + "\n" for k in sorted(lines))
    source = {"S1": {"company": "OUR_COMPANY", "region": "TR", "lines": lines, "sha256": sha256_text(canonical)}}
    record = {"line": "L1", "source_id": "S1", "company": "OUR_COMPANY",
              "region": "TR", "text": "We support English."}
    return record, source

class SourceBoundTests(unittest.TestCase):
    def check(self, expected, record=None, sources=None, reason=None):
        base, snap = fixture()
        rows = [base] if record is None else record
        trusted = snap if sources is None else sources
        result = verify_source_bound_v9(QUESTION, rows, trusted, region="TR", as_of=DAY)
        self.assertEqual(result["decision"], expected, result)
        self.assertFalse(result["real_world_authenticity_verified"])
        self.assertFalse(result["commercial_approval"])
        self.assertFalse(result["automatic_offer"])
        if reason:
            self.assertIn(reason, [x[1] for x in result["review"]])
        return result

    def test_01_valid_snapshot(self):
        self.assertTrue(self.check("POSITIVE")["source_integrity_verified"])
    def test_02_missing_source_id(self):
        row, sources = fixture(); row.pop("source_id")
        self.check("REVIEW_SCOPE", [row], sources, "SOURCE_REFERENCE_MISSING")
    def test_03_missing_line(self):
        row, sources = fixture(); row.pop("line")
        self.check("REVIEW_SCOPE", [row], sources, "SOURCE_REFERENCE_MISSING")
    def test_04_unknown_source(self):
        row, sources = fixture(); row["source_id"]="S2"
        self.check("REVIEW_SCOPE", [row], sources, "SOURCE_NOT_TRUSTED")
    def test_05_modified_claim(self):
        row, sources = fixture(); row["text"]="We support English. Always."
        self.check("REVIEW_SCOPE", [row], sources, "SOURCE_LINE_MISMATCH")
    def test_06_modified_snapshot(self):
        row, sources = fixture(); sources["S1"]["lines"]["L1"]="Changed without hash update."
        self.check("REVIEW_SCOPE", [row], sources, "SOURCE_HASH_MISMATCH")
    def test_07_claim_line_not_found(self):
        row, sources = fixture(); row["line"]="L999"
        self.check("REVIEW_SCOPE", [row], sources, "SOURCE_LINE_MISMATCH")
    def test_08_forged_company_record(self):
        row, sources = fixture(); row["company"]="RIVAL"
        self.check("REVIEW_SCOPE", [row], sources, "COMPANY_SCOPE_MISMATCH")
    def test_09_trusted_identity_missing(self):
        row, sources = fixture(); sources["S1"].pop("company")
        self.check("REVIEW_SCOPE", [row], sources, "TRUSTED_IDENTITY_MISSING")
    def test_10_trusted_region_mismatch(self):
        row, sources = fixture(); sources["S1"]["region"]="UK"
        self.check("REVIEW_SCOPE", [row], sources, "TRUSTED_REGION_MISMATCH")
    def test_11_missing_region_in_trusted(self):
        row, sources = fixture(); sources["S1"].pop("region")
        self.check("REVIEW_SCOPE", [row], sources, "TRUSTED_REGION_MISMATCH")
    def test_12_source_hash_missing(self):
        row, sources = fixture(); sources["S1"].pop("sha256")
        self.check("REVIEW_SCOPE", [row], sources, "TRUSTED_SNAPSHOT_INVALID")
    def test_13_malformed_line_contents(self):
        row, sources = fixture(); sources["S1"]["lines"]["L2"]=None
        self.check("REVIEW_SCOPE", [row], sources, "TRUSTED_LINES_INVALID")
    def test_14_empty_records(self):
        self.check("REVIEW_SCOPE", [], None, "SOURCE_INPUT_UNAVAILABLE")
    def test_15_mixed_valid_and_forged(self):
        row, sources = fixture()
        altered = dict(row); altered["source_id"]="FAKE"
        self.check("REVIEW_SCOPE", [row,altered], sources, "SOURCE_NOT_TRUSTED")
    def test_16_invalid_record_type(self):
        self.check("REVIEW_SCOPE", [42], None, "RECORD_INVALID")
    def test_17_metadata_flag_does_not_prove_real_world_authenticity(self):
        row, sources = fixture(); row["verified"]=True
        self.assertFalse(self.check("POSITIVE", [row],sources)["real_world_authenticity_verified"])
    def test_18_sibling_topic_ignored_only_after_integrity(self):
        row, sources = fixture()
        sibling = dict(row); sibling["line"]="L2"; sibling["text"]="ISO 27001 expired"
        result=self.check("POSITIVE",[row,sibling],sources)
        self.assertEqual(len(result["ignored"]),1)

if __name__ == "__main__":
    unittest.main(verbosity=2)
