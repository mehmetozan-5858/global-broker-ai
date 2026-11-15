import base64
import hashlib
import hmac
import json
import unittest
from ci_signed_reviewer_session import (
    issue_ci_token, verify_ci_token, read_with_verified_ci_session
)
from ci_reviewer_read_gateway import GatewayRejected

KEY = b"synthetic_test_key_not_for_production_12345"
NOW = 1700000000
A = "b2b_eval_ci_reviewer_a"
B = "b2b_eval_ci_reviewer_b"
DOC = "00000000-0000-4000-8000-000000000011"

def token(role=A, nonce="fixture-nonce-0001", key=KEY, now=NOW):
    return issue_ci_token(role=role, now=now, nonce=nonce, signing_key=key)

def altered(claims):
    body=base64.urlsafe_b64encode(json.dumps(claims,sort_keys=True,separators=(",",":")).encode()).rstrip(b"=").decode()
    sig=base64.urlsafe_b64encode(hmac.new(KEY,body.encode(),hashlib.sha256).digest()).rstrip(b"=").decode()
    return body+"."+sig

class Cursor:
    def __init__(self,value):self.value=value
    def fetchone(self):return self.value

class Connection:
    def __init__(self,role=A,row=(DOC,"FROZEN")):
        self.role=role
        self.row=row
        self.closed=False
    def execute(self,query,params=None):
        if query=="SELECT current_database(), current_user":
            return Cursor(("proposal_eval_ci",self.role))
        if params==(DOC,):return Cursor(self.row)
        raise AssertionError("unexpected sql")
    def close(self):self.closed=True

class SignedSessionTests(unittest.TestCase):
    def reject(self,code,value,**kwargs):
        with self.assertRaisesRegex(GatewayRejected,code):
            verify_ci_token(value,signing_key=kwargs.get("key",KEY),now=kwargs.get("now",NOW))
    def test_01_valid_token(self):
        self.assertEqual(verify_ci_token(token(),signing_key=KEY,now=NOW)["role"],A)
    def test_02_wrong_key(self):
        self.reject("SIGNATURE_INVALID",token(),key=b"unrelated_signing_key_for_unit_test_123")
    def test_03_payload_tampered(self):
        raw=token().split(".")
        self.reject("SIGNATURE_INVALID",raw[0][:-1]+"A."+raw[1])
    def test_04_expired(self):
        self.reject("TOKEN_EXPIRED_OR_NOT_YET_VALID",token(),now=NOW+60)
    def test_05_not_yet_valid(self):
        self.reject("TOKEN_EXPIRED_OR_NOT_YET_VALID",token(),now=NOW-1)
    def test_06_malformed(self):
        self.reject("TOKEN_INVALID","junk")
    def test_07_no_key(self):
        self.reject("SIGNING_KEY_INVALID",token(),key=b"short")
    def test_08_wrong_audience(self):
        claims=verify_ci_token(token(),signing_key=KEY,now=NOW)
        claims["aud"]="production"
        self.reject("TOKEN_SCOPE_INVALID",altered(claims))
    def test_09_wrong_role(self):
        claims=verify_ci_token(token(),signing_key=KEY,now=NOW)
        claims["role"]="postgres"
        self.reject("TOKEN_SCOPE_INVALID",altered(claims))
    def test_10_overlong_lifetime(self):
        claims=verify_ci_token(token(),signing_key=KEY,now=NOW)
        claims["exp"]=NOW+999
        self.reject("TOKEN_LIFETIME_INVALID",altered(claims))
    def test_11_extra_claim(self):
        claims=verify_ci_token(token(),signing_key=KEY,now=NOW)
        claims["admin"]=True
        self.reject("TOKEN_CLAIMS_INVALID",altered(claims))
    def test_12_invalid_nonce(self):
        claims=verify_ci_token(token(),signing_key=KEY,now=NOW)
        claims["jti"]="../"
        self.reject("TOKEN_NONCE_INVALID",altered(claims))
    def test_13_reject_boolean_time(self):
        claims=verify_ci_token(token(),signing_key=KEY,now=NOW)
        claims["iat"]=True
        self.reject("TOKEN_TIME_INVALID",altered(claims))
    def test_14_replay_denied(self):
        registry=set(); calls=[]
        def factory(role):
            calls.append(role)
            return Connection(role=role)
        got=read_with_verified_ci_session(token(),signing_key=KEY,now=NOW,
                 replay_registry=registry,connect_for_role=factory,document_id=DOC)
        self.assertEqual(got["status"],"FOUND")
        self.assertEqual(calls,[A])
        with self.assertRaisesRegex(GatewayRejected,"SESSION_REPLAY"):
            read_with_verified_ci_session(token(),signing_key=KEY,now=NOW,
                 replay_registry=registry,connect_for_role=factory,document_id=DOC)
        self.assertEqual(calls,[A])
    def test_15_session_role_db_mismatch(self):
        registry=set(); c=Connection(role=B)
        with self.assertRaisesRegex(GatewayRejected,"SESSION_DATABASE_ROLE_MISMATCH"):
            read_with_verified_ci_session(token(),signing_key=KEY,now=NOW,
                 replay_registry=registry,connect_for_role=lambda role:c,document_id=DOC)
        self.assertTrue(c.closed)
        self.assertEqual(len(registry),1)
    def test_16_invalid_signature_never_connects(self):
        calls=[]
        with self.assertRaisesRegex(GatewayRejected,"SIGNATURE_INVALID"):
            read_with_verified_ci_session(token(),signing_key=b"wrong_key_01234567890123456789012345",
                now=NOW,replay_registry=set(),connect_for_role=lambda role:calls.append(role),document_id=DOC)
        self.assertEqual(calls,[])
    def test_17_missing_registry(self):
        with self.assertRaisesRegex(GatewayRejected,"SESSION_CONFIG_INVALID"):
            read_with_verified_ci_session(token(),signing_key=KEY,now=NOW,
                replay_registry=None,connect_for_role=lambda role:Connection(),document_id=DOC)
    def test_18_not_a_real_identity_provider(self):
        import inspect
        self.assertNotIn("oidc",str(inspect.signature(read_with_verified_ci_session)).lower())

if __name__=="__main__":
    unittest.main(verbosity=2)
