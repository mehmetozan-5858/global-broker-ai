"""Synthetic PDFs only: tests parsing, not genuine document authenticity."""
import hashlib
import io
import unittest
from datetime import date
from pypdf import PdfWriter
from pypdf.generic import NameObject, DictionaryObject, DecodedStreamObject
from proposal_pdf_ingest import ingest_pinned_pdf, MAX_PDF_BYTES
from proposal_text_ingest import IngestionRejected
from proposal_source_gate import verify_source_bound_v9

def pdf_bytes(texts=("We support English.",)):
    writer = PdfWriter()
    for value in texts:
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                 NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})
        font_ref = writer._add_object(font)
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})})
        stream = DecodedStreamObject()
        if value is not None:
            escaped = value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream.set_data(("BT /F1 14 Tf 50 720 Td (" + escaped + ") Tj ET").encode("ascii"))
            page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()

def manifest(raw):
    return {"source_id": "PDF1", "sha256_raw": hashlib.sha256(raw).hexdigest(),
            "company": "OUR_COMPANY", "region": "TR"}

class PdfIngestionTests(unittest.TestCase):
    def rejects(self, expected, raw=None, metadata=None, source_id="PDF1"):
        if raw is None: raw = pdf_bytes()
        if metadata is None: metadata = manifest(raw)
        with self.assertRaisesRegex(IngestionRejected, expected):
            ingest_pinned_pdf(raw, source_id=source_id, trusted_manifest=metadata)

    def test_01_one_page_line(self):
        raw=pdf_bytes()
        snap,rows=ingest_pinned_pdf(raw,source_id="PDF1",trusted_manifest=manifest(raw))
        self.assertEqual(rows[0]["line"],"P1-L1")
        self.assertEqual(rows[0]["page"],1)
        self.assertEqual(rows[0]["text"],"We support English.")
        self.assertFalse(snap["PDF1"]["real_world_authenticity_verified"])

    def test_02_two_pages_line_identity(self):
        raw=pdf_bytes(("We support English.","We do not support English."))
        snap,rows=ingest_pinned_pdf(raw,source_id="PDF1",trusted_manifest=manifest(raw))
        self.assertEqual([r["line"] for r in rows],["P1-L1","P2-L1"])
        self.assertEqual(snap["PDF1"]["page_count"],2)

    def test_03_gate_matches_extracted_page(self):
        raw=pdf_bytes()
        snap,rows=ingest_pinned_pdf(raw,source_id="PDF1",trusted_manifest=manifest(raw))
        verdict=verify_source_bound_v9("Do you support English?",rows,snap,region="TR",as_of=date(2026,11,14))
        self.assertEqual(verdict["decision"],"POSITIVE")
        self.assertFalse(verdict["real_world_authenticity_verified"])

    def test_04_modified_bytes(self):
        raw=pdf_bytes(); self.rejects("PDF_RAW_HASH_MISMATCH",raw,manifest(pdf_bytes(("No.",))))

    def test_05_invalid_header(self):
        raw=b"not a pdf"; self.rejects("PDF_HEADER_INVALID",raw)

    def test_06_missing_manifest(self):
        self.rejects("PDF_MANIFEST_MISSING_OR_SCOPE",metadata={})

    def test_07_wrong_source_id(self):
        raw=pdf_bytes();self.rejects("PDF_MANIFEST_MISSING_OR_SCOPE",raw,manifest(raw),source_id="PDF2")

    def test_08_invalid_source_id(self):
        raw=pdf_bytes();self.rejects("PDF_SOURCE_ID_INVALID",raw,manifest(raw),source_id="../evil")

    def test_09_wrong_digest_format(self):
        raw=pdf_bytes();m=manifest(raw);m["sha256_raw"]="wrong"
        self.rejects("PDF_EXPECTED_HASH_INVALID",raw,m)

    def test_10_missing_company(self):
        raw=pdf_bytes();m=manifest(raw);m.pop("company")
        self.rejects("PDF_COMPANY_MISSING",raw,m)

    def test_11_missing_region(self):
        raw=pdf_bytes();m=manifest(raw);m.pop("region")
        self.rejects("PDF_REGION_MISSING",raw,m)

    def test_12_empty_bytes(self):
        self.rejects("PDF_INPUT_INVALID",b"")

    def test_13_wrong_type(self):
        self.rejects("PDF_INPUT_INVALID","%PDF-",manifest(b"bad-type"))

    def test_14_oversize(self):
        raw=b"%PDF-"+b"x"*MAX_PDF_BYTES
        self.rejects("PDF_INPUT_INVALID",raw)

    def test_15_malformed_pdf(self):
        raw=b"%PDF-1.7\nnot real pdf"
        self.rejects("PDF_PARSE_FAILED",raw)

    def test_16_image_or_textless_page_rejected(self):
        raw=pdf_bytes((None,))
        self.rejects("PDF_PAGE_TEXT_MISSING",raw)

    def test_17_one_textless_page_blocks_all(self):
        raw=pdf_bytes(("We support English.",None))
        self.rejects("PDF_PAGE_TEXT_MISSING",raw)

    def test_18_too_many_pages(self):
        raw=pdf_bytes(("OK",)*21)
        self.rejects("PDF_PAGE_COUNT_INVALID",raw)

    def test_19_record_tamper_rejected(self):
        raw=pdf_bytes()
        snap,rows=ingest_pinned_pdf(raw,source_id="PDF1",trusted_manifest=manifest(raw))
        rows[0]["text"]="Forged claim"
        result=verify_source_bound_v9("Do you support English?",rows,snap,region="TR",as_of=date(2026,11,14))
        self.assertEqual(result["decision"],"REVIEW_SCOPE")

    def test_20_encrypted_pdf_rejected(self):
        writer=PdfWriter();writer.add_blank_page(width=612,height=792);writer.encrypt("test")
        out=io.BytesIO();writer.write(out);raw=out.getvalue()
        self.rejects("PDF_ENCRYPTED",raw)

if __name__ == "__main__":
    unittest.main(verbosity=2)
