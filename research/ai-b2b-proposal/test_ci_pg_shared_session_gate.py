"""Real PostgreSQL 16 disposable CI tests for cross-connection coordination.

No real data, OIDC, cloud DB, or production deployment. Uses CI fixture roles.
"""
import os
import hashlib
import threading
import unittest

import psycopg
from ci_external_recovery_witness import (
    issue_fixture_witness, consume_with_signed_witness, check_with_signed_witness
)

from ci_reviewer_read_gateway import GatewayRejected
from ci_signed_reviewer_session import issue_ci_token
from ci_pg_shared_session_gate import (
    setup_ci_coordinator, consume_once, revoke_nonce,
    rotate_key, disable_authority,
    check_external_recovery_floor, current_generation_for_ci_witness
)

ADMIN = os.getenv("B2B_CI_PG_DSN")
DB = "proposal_eval_ci"
A = "b2b_eval_ci_reviewer_a"
KEY1 = b"ephemeral_only_sharing_session_key_01234567"
KEY2 = b"ephemeral_only_rotation_session_key_01234567"
NOW = 1700000000

def jwt(nonce, key=KEY1):
    return issue_ci_token(role=A, now=NOW, nonce=nonce, signing_key=key)

@unittest.skipUnless(ADMIN, "disposable CI PG connection required")
class SharedSessionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.primary=psycopg.connect(ADMIN,autocommit=True)
        if cls.primary.info.dbname!=DB or cls.primary.info.user!="postgres":
            cls.primary.close()
            raise RuntimeError("REFUSE_NON_EPHEMERAL_DB")
        setup_ci_coordinator(cls.primary,signing_key=KEY1)
    @classmethod
    def tearDownClass(cls):
        if hasattr(cls,"primary"):cls.primary.close()
    def conn(self):
        return psycopg.connect(ADMIN,autocommit=True)
    def test_01_same_token_cannot_be_consumed_twice_across_connections(self):
        tok=jwt("shared-nonce-000001")
        with self.conn() as a, self.conn() as b:
            self.assertEqual(consume_once(a,tok,signing_key=KEY1,now=NOW+1),A)
            with self.assertRaisesRegex(GatewayRejected,"SESSION_REPLAY"):
                consume_once(b,tok,signing_key=KEY1,now=NOW+1)
    def test_02_revoke_from_peer_connection(self):
        tok=jwt("shared-revoke-00001")
        with self.conn() as a, self.conn() as b:
            revoke_nonce(a,"shared-revoke-00001")
            with self.assertRaisesRegex(GatewayRejected,"SESSION_REVOKED"):
                consume_once(b,tok,signing_key=KEY1,now=NOW+1)
    def test_03_revoke_after_spent_blocks_replay(self):
        tok=jwt("spent-then-revoke-01")
        with self.conn() as a, self.conn() as b:
            consume_once(a,tok,signing_key=KEY1,now=NOW+1)
            revoke_nonce(b,"spent-then-revoke-01")
            with self.assertRaisesRegex(GatewayRejected,"SESSION_REVOKED"):
                consume_once(a,tok,signing_key=KEY1,now=NOW+1)
    def test_04_concurrent_connections_exactly_one_wins(self):
        tok=jwt("concurrent-token-0001")
        gate=threading.Barrier(3)
        replies=[]
        lock=threading.Lock()
        def worker():
            try:
                with self.conn() as c:
                    gate.wait(timeout=10)
                    role=consume_once(c,tok,signing_key=KEY1,now=NOW+1)
                    value="OK:"+role
            except Exception as exc:
                value=str(exc)
            with lock:
                replies.append(value)
        t1=threading.Thread(target=worker)
        t2=threading.Thread(target=worker)
        t1.start();t2.start();gate.wait(timeout=10)
        t1.join(timeout=15);t2.join(timeout=15)
        self.assertFalse(t1.is_alive() or t2.is_alive())
        self.assertEqual(sorted(replies),["OK:"+A,"SESSION_REPLAY"])
    def test_05_wrong_signing_key_never_spends_nonce(self):
        tok=jwt("wrong-key-token-001")
        with self.conn() as a:
            with self.assertRaisesRegex(GatewayRejected,"SIGNATURE_INVALID"):
                consume_once(a,tok,signing_key=KEY2,now=NOW+1)
            self.assertEqual(consume_once(a,tok,signing_key=KEY1,now=NOW+1),A)
    def test_06_no_actual_customer_data_in_coordinator(self):
        with self.conn() as a:
            tables=a.execute("""SELECT tablename FROM pg_tables
                WHERE schemaname='b2b_eval_ci_control' ORDER BY tablename""").fetchall()
            self.assertEqual(tables,[("nonces",),("retired_keys",),("state",)])
    def test_07_public_role_has_no_schema_usage(self):
        with self.conn() as a:
            self.assertFalse(a.execute(
                "SELECT has_schema_privilege('b2b_eval_ci_reviewer_a','b2b_eval_ci_control','USAGE')"
            ).fetchone()[0])
    def test_08_rejected_noncanonical_nonce(self):
        with self.conn() as a:
            with self.assertRaisesRegex(GatewayRejected,"COORDINATOR_NONCE_INVALID"):
                revoke_nonce(a,"'OR1=1--")
    def test_09_rotation_invalidates_old_key_on_other_connection(self):
        tok=jwt("rotated-old-token01")
        with self.conn() as a, self.conn() as b:
            rotate_key(a,old_key=KEY1,new_key=KEY2)
            with self.assertRaisesRegex(GatewayRejected,"COORDINATOR_KEY_RETIRED"):
                consume_once(b,tok,signing_key=KEY1,now=NOW+1)
    def test_10_rotation_new_key_works_on_other_connection(self):
        tok=jwt("rotated-new-token01",key=KEY2)
        with self.conn() as a:
            self.assertEqual(consume_once(a,tok,signing_key=KEY2,now=NOW+1),A)
    def test_11_stale_key_cannot_rotate(self):
        with self.conn() as a:
            with self.assertRaisesRegex(GatewayRejected,"COORDINATOR_STALE_ROTATION"):
                rotate_key(a,old_key=KEY1,new_key=b"another_test_key_only_0123456789abc")
    def test_11b_retired_key_cannot_be_reactivated(self):
        with self.conn() as a:
            with self.assertRaisesRegex(GatewayRejected,"COORDINATOR_RETIRED_KEY_REUSE"):
                rotate_key(a,old_key=KEY2,new_key=KEY1)
        # State must remain on replacement key after rejected rollback.
        fresh=jwt("no-rollback-token-001",key=KEY2)
        with self.conn() as b:
            self.assertEqual(consume_once(b,fresh,signing_key=KEY2,now=NOW+1),A)
    def test_11c_external_floor_detects_simulated_stale_restore(self):
        # A trusted floor would be stored OUTSIDE this database. This CI
        # fixture preserves the number in process memory, not durable storage.
        with self.conn() as admin:
            floor = current_generation_for_ci_witness(admin)
            self.assertGreaterEqual(floor, 1)
            admin.execute("""UPDATE b2b_eval_ci_control.state
                SET generation=%s WHERE singleton=1""", (floor-1,))
        try:
            with self.conn() as reader:
                with self.assertRaisesRegex(GatewayRejected,"RECOVERY_ROLLBACK_DETECTED"):
                    check_external_recovery_floor(reader, trusted_min_generation=floor)
                pending=jwt("rollback-blocked-0001",key=KEY2)
                with self.assertRaisesRegex(GatewayRejected,"RECOVERY_ROLLBACK_DETECTED"):
                    consume_once(reader,pending,signing_key=KEY2,now=NOW+1,
                                 trusted_min_generation=floor)
        finally:
            # Fixture repair is admin-only and ONLY in the ephemeral CI DB.
            with self.conn() as admin:
                admin.execute("UPDATE b2b_eval_ci_control.state SET generation=%s WHERE singleton=1",(floor,))
        with self.conn() as reader:
            self.assertTrue(check_external_recovery_floor(reader,trusted_min_generation=floor))
            self.assertEqual(consume_once(reader,pending,signing_key=KEY2,now=NOW+1,
                             trusted_min_generation=floor),A)
    def test_11d_invalid_external_floor_fails_closed(self):
        with self.conn() as c:
            tok=jwt("invalid-floor-0001",key=KEY2)
            with self.assertRaisesRegex(GatewayRejected,"RECOVERY_FLOOR_INVALID"):
                consume_once(c,tok,signing_key=KEY2,now=NOW+1,
                             trusted_min_generation=True)
    def test_11e_connection_killed_before_commit_does_not_spend(self):
        # Kill the CI connection during an uncommitted nonce insert; PostgreSQL
        # must roll back rather than record a successful consume.
        nonce="killed-before-commit-001"
        hashed=hashlib.sha256(nonce.encode("ascii")).hexdigest()
        with self.conn() as victim, self.conn() as killer:
            with self.assertRaises(psycopg.OperationalError):
                with victim.transaction():
                    victim.execute("""SELECT generation FROM b2b_eval_ci_control.state
                                     WHERE singleton=1 FOR UPDATE""")
                    victim.execute("""INSERT INTO b2b_eval_ci_control.nonces
                        (nonce_digest,state) VALUES (%s,'SPENT')""",(hashed,))
                    killer.execute("SELECT pg_terminate_backend(%s)",(victim.info.backend_pid,))
                    victim.execute("SELECT 1")
        with self.conn() as reader:
            self.assertEqual(consume_once(reader,jwt(nonce,key=KEY2),
                 signing_key=KEY2,now=NOW+1),A)
    def test_11f_acknowledgement_loss_after_commit_retries_fail_closed(self):
        # Simulates lost client acknowledgement AFTER commit, not a real
        # network failure. Retry must never grant a second consumption.
        nonce="committed-no-ack-0001"
        tok=jwt(nonce,key=KEY2)
        with self.conn() as first:
            self.assertEqual(consume_once(first,tok,signing_key=KEY2,now=NOW+1),A)
        with self.conn() as second:
            with self.assertRaisesRegex(GatewayRejected,"SESSION_REPLAY"):
                consume_once(second,tok,signing_key=KEY2,now=NOW+1)
    def test_11g_signed_external_witness_allows_current_generation(self):
        witness_key=b"external_recovery_ci_witness_key_01234567"
        with self.conn() as c:
            current=current_generation_for_ci_witness(c)
            signed=issue_fixture_witness(current,signing_key=witness_key)
            self.assertTrue(check_with_signed_witness(c,witness=signed,
                    witness_key=witness_key,trusted_min_generation=current))
            result=consume_with_signed_witness(c,jwt("witness-signed-new-001",key=KEY2),
                    signing_key=KEY2,now=NOW+1,witness=signed,
                    witness_key=witness_key,trusted_min_generation=current)
            self.assertEqual(result,A)
    def test_11h_signed_witness_rejects_stale_db_state(self):
        witness_key=b"external_recovery_ci_witness_key_01234567"
        with self.conn() as c:
            current=current_generation_for_ci_witness(c)
            signed=issue_fixture_witness(current,signing_key=witness_key)
            c.execute("UPDATE b2b_eval_ci_control.state SET generation=%s WHERE singleton=1",(current-1,))
        try:
            with self.conn() as c:
                with self.assertRaisesRegex(GatewayRejected,"RECOVERY_ROLLBACK_DETECTED"):
                    consume_with_signed_witness(c,jwt("witness-rollback-0001",key=KEY2),
                         signing_key=KEY2,now=NOW+1,witness=signed,witness_key=witness_key,
                         trusted_min_generation=current)
        finally:
            with self.conn() as c:
                c.execute("UPDATE b2b_eval_ci_control.state SET generation=%s WHERE singleton=1",(current,))
    def test_11i_witness_rollback_does_not_unlock(self):
        witness_key=b"external_recovery_ci_witness_key_01234567"
        with self.conn() as c:
            current=current_generation_for_ci_witness(c)
            older=issue_fixture_witness(current-1,signing_key=witness_key)
            with self.assertRaisesRegex(GatewayRejected,"WITNESS_ROLLBACK_DETECTED"):
                consume_with_signed_witness(c,jwt("witness-outdated-001",key=KEY2),
                    signing_key=KEY2,now=NOW+1,witness=older,
                    witness_key=witness_key,trusted_min_generation=current)
    def test_11j_invalid_witness_denies_before_db_consume(self):
        witness_key=b"external_recovery_ci_witness_key_01234567"
        with self.conn() as c:
            current=current_generation_for_ci_witness(c)
            with self.assertRaisesRegex(GatewayRejected,"WITNESS_INVALID"):
                consume_with_signed_witness(c,jwt("witness-absent-0001",key=KEY2),
                    signing_key=KEY2,now=NOW+1,witness=None,
                    witness_key=witness_key,trusted_min_generation=current)
    def test_12_disabled_gate_blocks_peer_connection(self):
        with self.conn() as a, self.conn() as b:
            disable_authority(a)
            tok=jwt("disabled-token-0001",key=KEY2)
            with self.assertRaisesRegex(GatewayRejected,"COORDINATOR_DISABLED"):
                consume_once(b,tok,signing_key=KEY2,now=NOW+1)
    def test_13_coordinator_rejects_missing_connection(self):
        with self.assertRaisesRegex(GatewayRejected,"COORDINATOR_CONNECTION_MISSING"):
            revoke_nonce(None,"abcde12345abcde12345")
    def test_14_non_ephemeral_role_cannot_call_coordinator(self):
        with psycopg.connect(os.environ["B2B_CI_READER_DSN"],autocommit=True) as c:
            with self.assertRaisesRegex(GatewayRejected,"COORDINATOR_NOT_EPHEMERAL_ADMIN"):
                revoke_nonce(c,"role-reject-token01")
    def test_15_transactional_interface_rejects_implicit_txn_mode(self):
        with psycopg.connect(ADMIN,autocommit=False) as c:
            with self.assertRaisesRegex(GatewayRejected,"COORDINATOR_AUTOCOMMIT_REQUIRED"):
                revoke_nonce(c,"txn-mode-token-001")

if __name__=="__main__":
    unittest.main(verbosity=2)
