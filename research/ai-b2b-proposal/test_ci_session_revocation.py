import threading
import unittest

from ci_session_revocation import CiSessionAuthority
from ci_reviewer_read_gateway import GatewayRejected

KEY1 = b"synthetic_session_key_one_0123456789012345"
KEY2 = b"synthetic_session_key_two_0123456789012345"
NOW = 1700000000
ROLE_A = "b2b_eval_ci_reviewer_a"
ROLE_B = "b2b_eval_ci_reviewer_b"
DOC = "00000000-0000-4000-8000-000000000011"

class Cursor:
    def __init__(self,value): self.value=value
    def fetchone(self): return self.value

class FakeConnection:
    def __init__(self,role=ROLE_A,document=(DOC,"FROZEN")):
        self.role=role
        self.document=document
        self.closed=False
    def execute(self,sql,params=None):
        if sql=="SELECT current_database(), current_user":
            return Cursor(("proposal_eval_ci",self.role))
        if params==(DOC,):
            return Cursor(self.document)
        raise RuntimeError("UNEXPECTED_SQL")
    def close(self): self.closed=True

class RevocationTests(unittest.TestCase):
    def setUp(self):
        self.authority=CiSessionAuthority(signing_key=KEY1)
    def issue(self,nonce="revocation-token-0001",role=ROLE_A):
        return self.authority.issue_fixture(role=role,now=NOW,nonce=nonce)
    def read(self,token, factory=None):
        return self.authority.read_once(token,now=NOW+1,
            connect_for_role=factory or (lambda role:FakeConnection(role=role)),
            document_id=DOC)
    def test_01_session_initially_works(self):
        self.assertEqual(self.read(self.issue())["status"],"FOUND")
    def test_02_revoked_token_denied_before_db(self):
        t=self.issue();self.authority.revoke_nonce("revocation-token-0001")
        called=[]
        with self.assertRaisesRegex(GatewayRejected,"SESSION_REVOKED"):
            self.read(t,lambda role:called.append(role))
        self.assertEqual(called,[])
    def test_03_revocation_blocks_future_issue_same_nonce(self):
        self.authority.revoke_nonce("revocation-token-0001")
        with self.assertRaisesRegex(GatewayRejected,"SESSION_NONCE_BLOCKED"):
            self.issue()
    def test_04_rotation_retires_old_token(self):
        t=self.issue()
        self.authority.rotate_signing_key(KEY2)
        with self.assertRaisesRegex(GatewayRejected,"SIGNATURE_INVALID"):
            self.read(t)
    def test_05_rotation_accepts_new_token(self):
        self.authority.rotate_signing_key(KEY2)
        self.assertEqual(self.read(self.issue(nonce="revocation-token-0002"))["status"],"FOUND")
    def test_06_old_key_cannot_be_used_after_rotation(self):
        old=self.issue()
        self.authority.rotate_signing_key(KEY2)
        self.authority.rotate_signing_key(KEY1)
        self.assertEqual(self.read(old)["status"],"FOUND")
    def test_07_rotation_same_key_forbidden(self):
        with self.assertRaisesRegex(GatewayRejected,"ROTATION_KEY_UNCHANGED"):
            self.authority.rotate_signing_key(KEY1)
    def test_08_rotation_short_key_forbidden(self):
        with self.assertRaisesRegex(GatewayRejected,"SIGNING_KEY_INVALID"):
            self.authority.rotate_signing_key(b"short")
    def test_09_disable_stops_requests(self):
        t=self.issue();self.authority.disable()
        with self.assertRaisesRegex(GatewayRejected,"AUTHORITY_DISABLED"):
            self.read(t)
    def test_10_disable_stops_issuance(self):
        self.authority.disable()
        with self.assertRaisesRegex(GatewayRejected,"AUTHORITY_DISABLED"):
            self.issue()
    def test_11_replay_denied(self):
        t=self.issue();self.read(t)
        with self.assertRaisesRegex(GatewayRejected,"SESSION_REPLAY"):
            self.read(t)
    def test_12_failed_db_access_still_consumes_nonce(self):
        t=self.issue()
        with self.assertRaisesRegex(GatewayRejected,"SESSION_DATABASE_ROLE_MISMATCH"):
            self.read(t,lambda role:FakeConnection(role=ROLE_B))
        with self.assertRaisesRegex(GatewayRejected,"SESSION_REPLAY"):
            self.read(t)
    def test_13_bad_signature_never_opens_db(self):
        t=self.issue();self.authority.rotate_signing_key(KEY2)
        seen=[]
        with self.assertRaisesRegex(GatewayRejected,"SIGNATURE_INVALID"):
            self.read(t,lambda role:seen.append(role))
        self.assertEqual(seen,[])
    def test_14_revocation_input_invalid(self):
        with self.assertRaisesRegex(GatewayRejected,"REVOCATION_NONCE_INVALID"):
            self.authority.revoke_nonce("x")
    def test_15_no_connection_factory_rejected(self):
        t=self.issue()
        with self.assertRaisesRegex(GatewayRejected,"SESSION_CONFIG_INVALID"):
            self.read(t,factory="not a function")
    def test_16_connection_closed_after_mismatch(self):
        c=FakeConnection(role=ROLE_B);t=self.issue()
        with self.assertRaisesRegex(GatewayRejected,"SESSION_DATABASE_ROLE_MISMATCH"):
            self.read(t,lambda role:c)
        self.assertTrue(c.closed)
    def test_17_wrong_principal_denied(self):
        t=self.issue(role=ROLE_B)
        with self.assertRaisesRegex(GatewayRejected,"SESSION_DATABASE_ROLE_MISMATCH"):
            self.read(t,lambda role:FakeConnection(role=ROLE_A))
    def test_18_atomic_one_time_consumption(self):
        t=self.issue();start=threading.Barrier(3);results=[]
        def worker():
            start.wait()
            try:
                self.read(t)
                results.append("FOUND")
            except GatewayRejected as exc:
                results.append(str(exc))
        a=threading.Thread(target=worker);b=threading.Thread(target=worker)
        a.start();b.start();start.wait();a.join();b.join()
        self.assertEqual(sorted(results),["FOUND","SESSION_REPLAY"])
    def test_19_rejected_token_no_connection(self):
        t=self.issue();self.authority.revoke_nonce("revocation-token-0001")
        factory_calls=[]
        with self.assertRaisesRegex(GatewayRejected,"SESSION_REVOKED"):
            self.read(t,lambda role:factory_calls.append(role))
        self.assertEqual(factory_calls,[])
    def test_20_no_real_customer_authorization(self):
        self.assertFalse(hasattr(self.authority,"production_ready"))

if __name__=="__main__":
    unittest.main(verbosity=2)
