import unittest
from unittest.mock import patch
from ci_reviewer_read_gateway import GatewayRejected
from ci_signed_reviewer_session import issue_ci_token
from ci_external_recovery_witness import issue_fixture_witness
from ci_uncertain_commit_reconciliation import reconcile_without_authorizing

KEY=b"synthetic_ci_reconcile_token_signer_key_12345"
WKEY=b"synthetic_ci_reconcile_witness_key_123456"
NOW=1700000000
ROLE="b2b_eval_ci_reviewer_a"
NONCE="uncertain-commit-unit-001"


def token():
    return issue_ci_token(role=ROLE,now=NOW,nonce=NONCE,signing_key=KEY)


class Provider:
    def __init__(self, gen=5, floor=5):
        self.gen=gen;self.floor=floor;self.reads=0
    def read(self):
        self.reads+=1
        return (issue_fixture_witness(self.gen,signing_key=WKEY),self.floor)


class Cursor:
    def __init__(self,val):self.val=val
    def fetchone(self):return self.val


class Transaction:
    def __enter__(self):return self
    def __exit__(self,*args):return False


class Conn:
    def __init__(self,gen=5,nonce_state="SPENT"):
        self.gen=gen;self.nonce_state=nonce_state
        self.reads=0;self.writes=0
    def transaction(self):return Transaction()
    def execute(self,sql,params=None):
        assert sql.lstrip().startswith("SELECT"), "reconciliation must never write"
        self.reads+=1
        if "SELECT generation FROM" in sql:return Cursor((self.gen,))
        if "SELECT state FROM" in sql:return Cursor(None if self.nonce_state is None else (self.nonce_state,))
        raise AssertionError(sql)


class ReconcileUnitTests(unittest.TestCase):
    def evaluate(self,conn=None,provider=None):
        c=conn if conn is not None else Conn()
        p=provider if provider is not None else Provider()
        with patch("ci_uncertain_commit_reconciliation._guard_connection"),patch(
             "ci_uncertain_commit_reconciliation._lock_state"):
            return reconcile_without_authorizing(c,token(),signing_key=KEY,
                now=NOW+1,provider=p,witness_key=WKEY)
    def test_01_spent_same_generation_no_reauth(self):
        result=self.evaluate()
        self.assertEqual(result["status"],"BLOCKED_SPENT_NO_REAUTHORIZATION")
        self.assertFalse(result["authorized"])
    def test_02_lag_needs_manual_review(self):
        result=self.evaluate(conn=Conn(gen=7),provider=Provider(gen=5))
        self.assertEqual(result["status"],"BLOCKED_WITNESS_LAG_OPERATOR_REVIEW")
        self.assertFalse(result["auto_advance_witness"])
    def test_03_db_rollback_denied(self):
        self.assertEqual(self.evaluate(conn=Conn(gen=4))["status"],"BLOCKED_DB_ROLLBACK")
    def test_04_missing_nonce_denied(self):
        self.assertEqual(self.evaluate(conn=Conn(nonce_state=None))["status"],"BLOCKED_NO_COMMITTED_NONCE")
    def test_05_revoked_nonce_denied(self):
        self.assertEqual(self.evaluate(conn=Conn(nonce_state="REVOKED"))["status"],"BLOCKED_REVOKED")
    def test_06_unexpected_nonce_denied(self):
        self.assertEqual(self.evaluate(conn=Conn(nonce_state="UNKNOWN"))["status"],"BLOCKED_UNEXPECTED_NONCE_STATE")
    def test_07_provider_missing_denied(self):
        with self.assertRaisesRegex(GatewayRejected,"RECONCILE_WITNESS_UNAVAILABLE"):
            self.evaluate(provider=object())
    def test_08_provider_read_failure_denied(self):
        class BadProvider:
            def read(self):raise TimeoutError("test")
        with self.assertRaisesRegex(GatewayRejected,"RECONCILE_WITNESS_READ_FAILED"):
            self.evaluate(provider=BadProvider())
    def test_09_old_signed_witness_denied(self):
        with self.assertRaisesRegex(GatewayRejected,"WITNESS_ROLLBACK_DETECTED"):
            self.evaluate(provider=Provider(gen=4,floor=5))
    def test_10_malformed_provider_denied(self):
        class BadProvider:
            def read(self):return ("only one",)
        with self.assertRaisesRegex(GatewayRejected,"RECONCILE_WITNESS_INVALID"):
            self.evaluate(provider=BadProvider())
    def test_11_all_outcomes_no_grant_or_retry(self):
        for c in [Conn(),Conn(gen=6),Conn(gen=4),Conn(nonce_state=None),
                  Conn(nonce_state="REVOKED")]:
            with self.subTest(c=c.nonce_state):
                result=self.evaluate(conn=c)
                self.assertFalse(result["authorized"])
                self.assertFalse(result["retry_consumption"])
                self.assertFalse(result["auto_advance_witness"])
    def test_12_diagnostic_never_writes(self):
        c=Conn(gen=8)
        self.evaluate(conn=c)
        self.assertEqual(c.writes,0)
        self.assertEqual(c.reads,2)

if __name__=="__main__":
    unittest.main(verbosity=2)
