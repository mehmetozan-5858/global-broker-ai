import hashlib
import json
import unittest
from independent_eval_gate import evaluate_external_gold, EvaluationRejected, wilson_upper

def dataset():
    records=[
        {"id":"H1","actual":"POSITIVE","expected":"POSITIVE","stratum":"tr","evidence_hash":"a"*64},
        {"id":"H2","actual":"REVIEW_SCOPE","expected":"NEGATIVE","stratum":"en","evidence_hash":"b"*64},
        {"id":"H3","actual":"POSITIVE","expected":"REVIEW_SCOPE","stratum":"conditional","evidence_hash":"c"*64},
    ]
    return records

def sealed(records):
    payload=json.dumps(records,sort_keys=True,ensure_ascii=False,separators=(",",":"))
    return {"origin":"independent_authorized_human_gold",
            "previously_used_for_development":False,"frozen_before_execution":True,
            "reviewer_id":"TEST_ONLY_REVIEWER",
            "sha256_canonical":hashlib.sha256(payload.encode("utf-8")).hexdigest()}

class IndependentEvaluationGateTests(unittest.TestCase):
    def reject(self, token, records=None, manifest=None):
        if records is None: records=dataset()
        if manifest is None: manifest=sealed(records)
        with self.assertRaisesRegex(EvaluationRejected,token):
            evaluate_external_gold(records,manifest)
    def test_01_report_separates_errors(self):
        rows=dataset();out=evaluate_external_gold(rows,sealed(rows))
        self.assertEqual(out["unsafe_positive"],1)
        self.assertEqual(out["missed_positive"],0)
        self.assertEqual(out["total"],3)
        self.assertEqual(out["status"],"RESEARCH_EVIDENCE_INCOMPLETE")
        self.assertFalse(out["commercial_approval"])
        self.assertFalse(out["production_ready"])
    def test_02_wilson_zero_not_zero_confidence(self):
        self.assertGreater(wilson_upper(0,10),0)
        self.assertIsNone(wilson_upper(0,0))
    def test_03_missing_gold_attestation(self):
        rows=dataset();m=sealed(rows);m["origin"]="model_generated"
        self.reject("INDEPENDENT_GOLD_NOT_ATTESTED",rows,m)
    def test_04_contaminated_set(self):
        rows=dataset();m=sealed(rows);m["previously_used_for_development"]=True
        self.reject("CONTAMINATED_OR_UNKNOWN_SET",rows,m)
    def test_05_missing_contamination_status(self):
        rows=dataset();m=sealed(rows);m.pop("previously_used_for_development")
        self.reject("CONTAMINATED_OR_UNKNOWN_SET",rows,m)
    def test_06_not_frozen(self):
        rows=dataset();m=sealed(rows);m["frozen_before_execution"]=False
        self.reject("DATASET_NOT_FROZEN",rows,m)
    def test_07_tampered_gold_labels(self):
        rows=dataset();m=sealed(rows);rows[0]["expected"]="NEGATIVE"
        self.reject("DATASET_HASH_MISMATCH",rows,m)
    def test_08_duplicate_case_ids(self):
        rows=dataset();rows[1]["id"]="H1"
        self.reject("CASE_ID_INVALID_OR_DUPLICATE",rows,sealed(rows))
    def test_09_invalid_decision(self):
        rows=dataset();rows[1]["actual"]="APPROVED"
        self.reject("LABEL_INVALID",rows,sealed(rows))
    def test_10_unverifiable_evidence(self):
        rows=dataset();rows[1]["evidence_hash"]="bad"
        self.reject("EVIDENCE_HASH_INVALID",rows,sealed(rows))
    def test_11_empty(self):
        self.reject("EMPTY_EVALUATION",[],sealed([]))
    def test_12_missing_reviewer(self):
        rows=dataset();m=sealed(rows);m.pop("reviewer_id")
        self.reject("REVIEWER_MISSING",rows,m)
    def test_13_missing_stratum(self):
        rows=dataset();rows[1].pop("stratum")
        self.reject("STRATUM_MISSING",rows,sealed(rows))
    def test_14_false_negative_separately(self):
        rows=dataset();rows[0]["actual"]="UNKNOWN"
        out=evaluate_external_gold(rows,sealed(rows))
        self.assertEqual(out["missed_positive"],1)
        self.assertEqual(out["unsafe_positive"],1)
    def test_15_full_synthetic_coverage_still_not_authorized(self):
        strata=["tr","en","multipage_pdf","conditional","counterparty"]
        rows=[{"id":str(i),"actual":"POSITIVE" if i%2==0 else "NEGATIVE",
               "expected":"POSITIVE" if i%2==0 else "NEGATIVE",
               "stratum":strata[i%len(strata)],"evidence_hash":"a"*64} for i in range(100)]
        out=evaluate_external_gold(rows,sealed(rows))
        self.assertEqual(out["status"],"RESEARCH_EVIDENCE_MEASURED")
        self.assertFalse(out["production_ready"])
        self.assertFalse(out["commercial_approval"])
        self.assertGreater(out["unsafe_positive_95pct_upper"],0)
    def test_16_missing_strata_no_go(self):
        rows=[{"id":str(i),"actual":"NEGATIVE","expected":"NEGATIVE",
               "stratum":"en","evidence_hash":"a"*64} for i in range(120)]
        out=evaluate_external_gold(rows,sealed(rows))
        self.assertEqual(out["status"],"RESEARCH_EVIDENCE_INCOMPLETE")
        self.assertIn("tr",out["missing_strata"])
    def test_17_missing_positive_gold_no_rate(self):
        rows=[{"id":str(i),"actual":"NEGATIVE","expected":"NEGATIVE",
               "stratum":"en","evidence_hash":"a"*64} for i in range(120)]
        out=evaluate_external_gold(rows,sealed(rows))
        self.assertIsNone(out["missed_positive_rate"])
        self.assertIsNone(out["missed_positive_95pct_upper"])

if __name__=="__main__":
    unittest.main(verbosity=2)
