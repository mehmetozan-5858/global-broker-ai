import unittest

from ci_reviewer_read_gateway import GatewayRejected
from ci_external_recovery_witness import (
    issue_fixture_witness, verify_recovery_witness
)

KEY = b"synthetic_independent_recovery_witness_key_12345"
ALT = b"completely_different_test_only_witness_key_12345"


class RecoveryWitnessTests(unittest.TestCase):
    def verify(self, witness, floor=5, key=KEY):
        return verify_recovery_witness(witness, signing_key=key,
                                       trusted_min_generation=floor)
    def rejection(self, code, witness, floor=5, key=KEY):
        with self.assertRaisesRegex(GatewayRejected, code):
            self.verify(witness, floor=floor, key=key)
    def test_01_verified_floor(self):
        self.assertEqual(self.verify(issue_fixture_witness(5,signing_key=KEY)),5)
    def test_02_newer_floor(self):
        self.assertEqual(self.verify(issue_fixture_witness(9,signing_key=KEY)),9)
    def test_03_previous_signed_witness_rejected(self):
        self.rejection("WITNESS_ROLLBACK_DETECTED",issue_fixture_witness(4,signing_key=KEY))
    def test_04_wrong_signer_key(self):
        self.rejection("WITNESS_SIGNATURE_INVALID",issue_fixture_witness(5,signing_key=ALT))
    def test_05_tampered_payload(self):
        original=issue_fixture_witness(5,signing_key=KEY)
        self.rejection("WITNESS_SIGNATURE_INVALID",original[:-2]+"AA")
    def test_06_missing_witness(self):
        self.rejection("WITNESS_INVALID",None)
    def test_07_empty_witness(self):
        self.rejection("WITNESS_INVALID","")
    def test_08_untrusted_floor_missing(self):
        self.rejection("WITNESS_FLOOR_INVALID",issue_fixture_witness(5,signing_key=KEY),floor=None)
    def test_09_untrusted_floor_boolean(self):
        self.rejection("WITNESS_FLOOR_INVALID",issue_fixture_witness(5,signing_key=KEY),floor=True)
    def test_10_negative_generation_rejected_at_issuer(self):
        with self.assertRaisesRegex(GatewayRejected,"WITNESS_FLOOR_INVALID"):
            issue_fixture_witness(-1,signing_key=KEY)
    def test_11_small_secret_rejected(self):
        with self.assertRaisesRegex(GatewayRejected,"WITNESS_KEY_INVALID"):
            issue_fixture_witness(5,signing_key=b"short")
    def test_12_malformed_base64(self):
        self.rejection("WITNESS_INVALID","not-really+base64.signature")
    def test_13_nonstandard_token_parts(self):
        self.rejection("WITNESS_INVALID","one.two.three")
    def test_14_signer_signature_not_same_as_db(self):
        self.rejection("WITNESS_SIGNATURE_INVALID",issue_fixture_witness(5,signing_key=KEY),key=ALT)

if __name__=="__main__":
    unittest.main(verbosity=2)
