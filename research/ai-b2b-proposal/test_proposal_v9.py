import unittest
from datetime import date
from proposal_v9 import verify_v9

T = date(2026, 11, 14)

def rec(text=None, **fields):
    x = {"line": "L1", "company": "OUR_COMPANY"}
    if text is not None: x["text"] = text
    x.update(fields)
    return x

class V9Tests(unittest.TestCase):
    def check(self, expected, question, records, region=None):
        out = verify_v9(question, records, region=region, as_of=T)
        self.assertEqual(expected, out["decision"], out)
        self.assertFalse(out["commercial_approval"])
        self.assertFalse(out["automatic_offer"])
        return out
    def test_unrelated_malformed_nonempty(self):
        self.check("POSITIVE", "Do you support English?",
                   [rec("ISO 27001 expired", valid_from="2027-99-99"), rec("We support English.", line="L2")])
    def test_unknown_malformed_not_silently_ignored(self):
        self.check("REVIEW_SCOPE", "Do you support English?", [rec("We support English."), {"line":"L2", "company":"OUR_COMPANY"}])
    def test_unrelated_rival(self):
        self.check("POSITIVE", "Do you support English?", [rec("We do not support English.",company="RIVAL"),rec("We support English.",line="L2")])
    def test_related_company_missing(self):
        self.check("REVIEW_SCOPE", "Do you support English?", [rec("We support English."),{"line":"L2","text":"We support English."}])
    def test_related_bad_date(self):
        self.check("REVIEW_SCOPE", "Do you support English?", [rec("We support English.",valid_from="2027-99-99")])
    def test_related_region_missing(self):
        self.check("REVIEW_SCOPE", "Do you support English?", [rec("We support English.")],region="TR")
    def test_other_region(self):
        self.check("REVIEW_SCOPE", "Do you support English?", [rec("We support English.",region="UK")],region="TR")
    def test_future(self):
        self.check("REVIEW_SCOPE", "Do you support English?", [rec("We support English.",valid_from="2027-01-01")])
    def test_expired(self):
        self.check("REVIEW_SCOPE", "Do you support English?", [rec("We support English.",valid_until="2025-01-01")])
    def test_date_order(self):
        self.check("REVIEW_SCOPE", "Do you support English?", [rec("We support English.",valid_from="2026-02-01",valid_until="2025-02-01")])
    def test_conflict(self):
        self.check("CONFLICT", "Do you support English?", [rec("We support English."),rec("We do not support English.",line="L2")])
    def test_cert_unverified(self):
        self.check("REVIEW_SCOPE", "ISO 27001 belgeniz var mı?", [rec("ISO 27001 sertifikamız vardır.")])
    def test_cert_negative(self):
        self.check("NEGATIVE", "ISO 27001 belgeniz var mı?", [rec("ISO 27001 sertifikamız yoktur.")])
    def test_unsupported(self):
        self.check("REVIEW_SCOPE", "What is the price?", [rec("We support English.")])
    def test_relevant_unknown_status(self):
        self.check("REVIEW_SCOPE", "Do you support English?", [rec("English support is planned.")])
    def test_nonrelated_with_missing_company(self):
        self.check("POSITIVE","Do you support English?", [{"line":"L1","text":"ISO 27001 certified."},rec("We support English.",line="L2")])
    def test_provisional_positive(self):
        self.check("POSITIVE", "Do you support English?", [rec("We support English.",region="TR")],region="TR")
    def test_non_dict_record(self):
        self.check("REVIEW_SCOPE", "Do you support English?", [rec("We support English."), 42])

if __name__ == "__main__":
    unittest.main(verbosity=2)
