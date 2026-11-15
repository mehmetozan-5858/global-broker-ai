import hashlib
import json
import unittest
from custodian_pinned_eval import evaluate_custodian_pinned
from independent_eval_gate import EvaluationRejected

REVIEWER = "CUSTODIAN_TEST"

def fixture():
    records = [
        {"id":"X1","actual":"REVIEW_SCOPE","expected":"REVIEW_SCOPE",
         "stratum":"tr","evidence_hash":"a"*64},
        {"id":"X2","actual":"POSITIVE","expected":"NEGATIVE",
         "stratum":"en","evidence_hash":"b"*64},
        {"id":"X3","actual":"POSITIVE","expected":"POSITIVE",
         "stratum":"conditional","evidence_hash":"c"*64},
    ]
    canon=json.dumps(records,sort_keys=True,ensure_ascii=False,separators=(",",":"))
    manifest={"origin":"independent_authorized_human_gold",
              "previously_used_for_development":False,
              "frozen_before_execution":True,
              "reviewer_id":REVIEWER,
              "sha256_canonical":hashlib.sha256(canon.encode()).hexdigest()}
    return records,manifest

def pin(m):
    return hashlib.sha256(json.dumps(m,sort_keys=True,ensure_ascii=False,
                                    separators=(",",":"),allow_nan=False).encode()).hexdigest()

class CustodianPinTests(unittest.TestCase):
    def check_rejected(self, code, rows=None, manifest=None, trusted_pin=None, reviewers=(REVIEWER,)):
        if rows is None or manifest is None:
            rows, manifest=fixture()
        if trusted_pin is None: trusted_pin=pin(manifest)
        with self.assertRaisesRegex(EvaluationRejected, code):
            evaluate_custodian_pinned(rows,manifest,
                trusted_manifest_sha256=trusted_pin,trusted_reviewers=reviewers)
    def test_01_valid_pin_measures_not_approves(self):
        rows,m=fixture()
        r=evaluate_custodian_pinned(rows,m,trusted_manifest_sha256=pin(m),trusted_reviewers=(REVIEWER,))
        self.assertEqual(r["unsafe_positive"],1)
        self.assertTrue(r["out_of_band_pin_matched"])
        self.assertFalse(r["trusted_custodian_identity_verified"])
        self.assertFalse(r["commercial_approval"])
        self.assertFalse(r["production_ready"])
    def test_02_no_pin(self):
        rows,m=fixture()
        self.check_rejected("OUT_OF_BAND_MANIFEST_PIN_MISSING",rows,m,trusted_pin="")
    def test_03_bad_pin(self):
        rows,m=fixture()
        self.check_rejected("OUT_OF_BAND_MANIFEST_PIN_MISSING",rows,m,trusted_pin="bad")
    def test_04_manifest_mutated(self):
        rows,m=fixture();old=pin(m);m["reviewer_id"]="ATTACKER"
        self.check_rejected("CUSTODIAN_MANIFEST_PIN_MISMATCH",rows,m,trusted_pin=old)
    def test_05_reviewer_not_authorized(self):
        rows,m=fixture()
        self.check_rejected("CUSTODIAN_REVIEWER_NOT_AUTHORIZED",rows,m,reviewers=("ANOTHER_REVIEWER",))
    def test_06_no_allowlist(self):
        rows,m=fixture()
        self.check_rejected("CUSTODIAN_REVIEWER_ALLOWLIST_MISSING",rows,m,reviewers=())
    def test_07_allowlist_invalid_type(self):
        rows,m=fixture()
        self.check_rejected("CUSTODIAN_REVIEWER_ALLOWLIST_MISSING",rows,m,reviewers=[REVIEWER])
    def test_08_allowlist_bad_identity(self):
        rows,m=fixture()
        self.check_rejected("CUSTODIAN_REVIEWER_ALLOWLIST_INVALID",rows,m,reviewers=("bad reviewer",))
    def test_09_changed_labels_after_seal(self):
        rows,m=fixture();old_pin=pin(m);rows[1]["expected"]="POSITIVE"
        self.check_rejected("DATASET_HASH_MISMATCH",rows,m,trusted_pin=old_pin)
    def test_10_self_signed_contaminated(self):
        rows,m=fixture();m["previously_used_for_development"]=True
        self.check_rejected("CONTAMINATED_OR_UNKNOWN_SET",rows,m,trusted_pin=pin(m))
    def test_11_removed_gold_attestation(self):
        rows,m=fixture();m["origin"]="synthetic"
        self.check_rejected("INDEPENDENT_GOLD_NOT_ATTESTED",rows,m,trusted_pin=pin(m))
    def test_12_no_frozen_state(self):
        rows,m=fixture();m["frozen_before_execution"]=False
        self.check_rejected("DATASET_NOT_FROZEN",rows,m,trusted_pin=pin(m))
    def test_13_missing_reviewer_in_manifest(self):
        rows,m=fixture();m.pop("reviewer_id")
        self.check_rejected("CUSTODIAN_REVIEWER_NOT_AUTHORIZED",rows,m,trusted_pin=pin(m))
    def test_14_non_serializable_manifest(self):
        rows,m=fixture();m["extra"]={1,2}
        self.check_rejected("CUSTODIAN_MANIFEST_UNSERIALIZABLE",rows,m,trusted_pin="a"*64)
    def test_15_no_custodian_bytes_authenticity(self):
        rows,m=fixture()
        out=evaluate_custodian_pinned(rows,m,trusted_manifest_sha256=pin(m),trusted_reviewers=(REVIEWER,))
        self.assertFalse(out["real_world_source_authenticity_verified"])

if __name__=="__main__":
    unittest.main(verbosity=2)
