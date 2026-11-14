import hashlib
import unittest
from datetime import date
from proposal_text_ingest import ingest_pinned_text, reject_pdf_or_unpinned, IngestionRejected, MAX_BYTES
from proposal_source_gate import verify_source_bound_v9

DAY = date(2026, 11, 14)

def fixture(body=b"We support English.\nISO 27001 expired\n"):
    return {"source_id": "DOC1", "sha256_raw": hashlib.sha256(body).hexdigest(),
            "company": "OUR_COMPANY", "region": "TR"}

class IngestionTests(unittest.TestCase):
    def assert_rejected(self, token, body=b"We support English.\n", manifest=None, source_id="DOC1"):
        if manifest is None: manifest = fixture(body)
        with self.assertRaisesRegex(IngestionRejected, token):
            ingest_pinned_text(body, source_id=source_id, trusted_manifest=manifest)
    def test_01_valid_snapshot_and_line_ids(self):
        body = b"We support English.\nISO 27001 expired\n"
        snap, rows = ingest_pinned_text(body, source_id="DOC1", trusted_manifest=fixture(body))
        self.assertEqual([r["line"] for r in rows], ["L1", "L2"])
        self.assertEqual(snap["DOC1"]["sha256_raw"], hashlib.sha256(body).hexdigest())
        self.assertFalse(snap["DOC1"]["real_world_authenticity_verified"])
    def test_02_source_gate_accepts_snapshot_consistency_only(self):
        body=b"We support English.\nISO 27001 expired\n"
        snap, rows=ingest_pinned_text(body, source_id="DOC1", trusted_manifest=fixture(body))
        result=verify_source_bound_v9("Do you support English?",rows,snap,region="TR",as_of=DAY)
        self.assertEqual(result["decision"],"POSITIVE")
        self.assertTrue(result["source_integrity_verified"])
        self.assertFalse(result["real_world_authenticity_verified"])
        self.assertFalse(result["automatic_offer"])
    def test_03_document_modified(self):
        body=b"We support English.\n"
        self.assert_rejected("RAW_HASH_MISMATCH",body,fixture(b"We support German.\n"))
    def test_04_source_id_changed(self):
        body=b"We support English.\n"
        self.assert_rejected("SOURCE_ID_MISMATCH",body,fixture(body),source_id="DOC2")
    def test_05_missing_manifest(self):
        body=b"We support English.\n"
        self.assert_rejected("MANIFEST_MISSING",body,manifest="no-manifest")
    def test_06_manifest_missing_company(self):
        body=b"We support English.\n"; m=fixture(body);m.pop("company")
        self.assert_rejected("MANIFEST_COMPANY_MISSING",body,m)
    def test_07_manifest_missing_region(self):
        body=b"We support English.\n"; m=fixture(body);m.pop("region")
        self.assert_rejected("MANIFEST_REGION_MISSING",body,m)
    def test_08_untrusted_hash(self):
        body=b"We support English.\n"; m=fixture(body);m["sha256_raw"]="INVALID"
        self.assert_rejected("EXPECTED_HASH_INVALID",body,m)
    def test_09_invalid_utf8(self):
        body=b"\xff\xfe";self.assert_rejected("ENCODING_INVALID",body)
    def test_10_bom_rejected(self):
        body=b"\xef\xbb\xbfWe support English.\n";self.assert_rejected("UNSUPPORTED_TEXT_FORMAT",body)
    def test_11_crlf_rejected(self):
        body=b"We support English.\r\n";self.assert_rejected("UNSUPPORTED_TEXT_FORMAT",body)
    def test_12_binary_null_rejected(self):
        body=b"We support English.\x00\n";self.assert_rejected("UNSUPPORTED_TEXT_FORMAT",body)
    def test_13_empty_rejected(self):
        self.assert_rejected("INPUT_BYTES_INVALID",b"")
    def test_14_whitespace_only_rejected(self):
        body=b"   \n  \n";self.assert_rejected("DOCUMENT_EMPTY",body)
    def test_15_oversized_rejected(self):
        body=b"x"*(MAX_BYTES+1)
        self.assert_rejected("INPUT_BYTES_INVALID",body)
    def test_16_nonbytes_rejected(self):
        self.assert_rejected("INPUT_BYTES_INVALID","We support English.",fixture(b"alternate"))
    def test_17_invalid_source_identifier(self):
        body=b"We support English.\n";m=fixture(body);m["source_id"]="../escape"
        self.assert_rejected("SOURCE_ID_INVALID",body,m,source_id="../escape")
    def test_18_pdf_rejected_without_pages(self):
        with self.assertRaisesRegex(IngestionRejected,"PDF_NOT_SUPPORTED"):
            reject_pdf_or_unpinned(b"%PDF-1.4")
    def test_19_blank_physical_line_keeps_stable_numbering(self):
        body=b"\nWe support English.\n"
        snap, rows=ingest_pinned_text(body,source_id="DOC1",trusted_manifest=fixture(body))
        self.assertEqual(rows[0]["line"],"L2")
        self.assertEqual(snap["DOC1"]["lines"]["L1"],"")
    def test_21_pdf_magic_rejected(self):
        body=b"%PDF-1.4\n1 0 obj\n"
        self.assert_rejected("UNSUPPORTED_DOCUMENT_TYPE",body)
    def test_22_control_byte_rejected(self):
        body=b"We support English.\x01\\n"
        self.assert_rejected("UNSUPPORTED_TEXT_FORMAT",body)
    def test_20_tampered_record_is_blocked_by_gate(self):
        body=b"We support English.\n"
        snap, rows=ingest_pinned_text(body,source_id="DOC1",trusted_manifest=fixture(body))
        rows[0]["text"]="We support English worldwide."
        result=verify_source_bound_v9("Do you support English?",rows,snap,region="TR",as_of=DAY)
        self.assertEqual(result["decision"],"REVIEW_SCOPE")

if __name__=="__main__":
    unittest.main(verbosity=2)
