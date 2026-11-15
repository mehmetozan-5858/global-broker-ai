"""Identity-scoped RLS proof in a throwaway CI PostgreSQL database only.

The CI fixture uses distinct PostgreSQL LOGIN principals and CURRENT_USER,
not spoofable application-defined session settings. It does NOT provide real
login/auth gateway, durable audit custody, Neon validation or production access.
"""
import os
import unittest
import psycopg
from psycopg.errors import InsufficientPrivilege
from ci_reviewer_read_gateway import read_assigned_document, GatewayRejected
from ci_signed_reviewer_session import issue_ci_token, read_with_verified_ci_session
from ci_session_revocation import CiSessionAuthority

ADMIN_DSN = os.environ.get("B2B_CI_PG_DSN")
DB = "proposal_eval_ci"
A = "b2b_eval_ci_reviewer_a"
B = "b2b_eval_ci_reviewer_b"
DOC_A = "00000000-0000-4000-8000-000000000011"
DOC_B = "00000000-0000-4000-8000-000000000012"

@unittest.skipUnless(ADMIN_DSN, "throwaway CI Postgres only")
class PgReviewerIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = psycopg.connect(ADMIN_DSN, autocommit=True)
        actual = cls.admin.execute("SELECT current_database()").fetchone()[0]
        if actual != DB:
            cls.admin.close()
            raise RuntimeError("REFUSE_NON_EPHEMERAL_DB")
        exists = cls.admin.execute("SELECT to_regclass('b2b_research_eval.document_meta')").fetchone()[0]
        if not exists:
            cls.admin.close()
            raise RuntimeError("DEFAULT_DENY_SETUP_MISSING")
        # Login roles are created ONLY inside the ephemeral CI container.
        cls.admin.execute("CREATE ROLE b2b_eval_ci_reviewer_a LOGIN PASSWORD 'local_ci_only_a'")
        cls.admin.execute("CREATE ROLE b2b_eval_ci_reviewer_b LOGIN PASSWORD 'local_ci_only_b'")
        for name in (A, B):
            cls.admin.execute("GRANT USAGE ON SCHEMA b2b_research_eval TO " + name)
            cls.admin.execute("GRANT SELECT ON b2b_research_eval.document_meta TO " + name)
        cls.admin.execute("""INSERT INTO b2b_research_eval.document_meta
             (document_id,source_sha256,manifest_sha256,assigned_reviewer,lifecycle_state)
             VALUES (%s,%s,%s,%s,%s),(%s,%s,%s,%s,%s)""",
             (DOC_A,"a"*64,"b"*64,A,"FROZEN", DOC_B,"c"*64,"d"*64,B,"FROZEN"))
        # Use PostgreSQL-authenticated login identity, not mutable custom GUCs.
        cls.admin.execute("""CREATE POLICY ci_reviewer_identity_read
          ON b2b_research_eval.document_meta FOR SELECT
          TO b2b_eval_ci_reviewer_a, b2b_eval_ci_reviewer_b
          USING (assigned_reviewer = current_user)""")
    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "admin"):
            cls.admin.close()
    def reviewer(self, role):
        if role == A:
            password = "local_ci_only_a"
        elif role == B:
            password = "local_ci_only_b"
        else:
            raise ValueError("unknown ephemeral test role")
        return psycopg.connect(
            "postgresql://" + role + ":" + password + "@127.0.0.1:5432/" + DB,
            autocommit=True)
    def test_01_a_sees_only_a(self):
        with self.reviewer(A) as c:
            self.assertEqual(c.execute("SELECT document_id::text FROM b2b_research_eval.document_meta").fetchall(), [(DOC_A,)])
    def test_02_b_sees_only_b(self):
        with self.reviewer(B) as c:
            self.assertEqual(c.execute("SELECT document_id::text FROM b2b_research_eval.document_meta").fetchall(), [(DOC_B,)])
    def test_03_a_cannot_read_b_by_id(self):
        with self.reviewer(A) as c:
            self.assertIsNone(c.execute(
                "SELECT document_id FROM b2b_research_eval.document_meta WHERE document_id=%s",(DOC_B,)).fetchone())
    def test_04_b_cannot_read_a_by_id(self):
        with self.reviewer(B) as c:
            self.assertIsNone(c.execute(
                "SELECT document_id FROM b2b_research_eval.document_meta WHERE document_id=%s",(DOC_A,)).fetchone())
    def test_05_spoofed_guc_does_not_unlock(self):
        with self.reviewer(A) as c:
            c.execute("SELECT set_config('b2b_eval.actor_id',%s,false)",(B,))
            c.execute("SELECT set_config('b2b_eval.actor_role','custodian',false)")
            self.assertEqual(c.execute("SELECT count(*) FROM b2b_research_eval.document_meta").fetchone()[0],1)
    def test_06_reviewer_b_cannot_edit(self):
        with self.reviewer(B) as c:
            with self.assertRaises(InsufficientPrivilege):
                c.execute("UPDATE b2b_research_eval.document_meta SET lifecycle_state='REVIEWED'")
    def test_07_reviewer_a_cannot_insert(self):
        with self.reviewer(A) as c:
            with self.assertRaises(InsufficientPrivilege):
                c.execute("""INSERT INTO b2b_research_eval.document_meta
                  (document_id,source_sha256,manifest_sha256,assigned_reviewer,lifecycle_state)
                  VALUES (%s,%s,%s,%s,%s)""",
                  ("00000000-0000-4000-8000-000000000013","a"*64,"b"*64,A,"RECEIVED"))
    def test_08_reviewer_cannot_read_review_table(self):
        with self.reviewer(A) as c:
            with self.assertRaises(InsufficientPrivilege):
                c.execute("SELECT count(*) FROM b2b_research_eval.review")
    def test_09_reviewer_cannot_read_audit_table(self):
        with self.reviewer(B) as c:
            with self.assertRaises(InsufficientPrivilege):
                c.execute("SELECT count(*) FROM b2b_research_eval.audit_event")
    def test_10_reviewer_cannot_bypass_rls(self):
        with self.reviewer(A) as c:
            self.assertEqual(c.execute(
                "SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user").fetchone(),
                (False,False))
    def test_11_reader_role_remains_default_deny(self):
        with psycopg.connect(os.environ["B2B_CI_READER_DSN"],autocommit=True) as c:
            self.assertEqual(c.execute("SELECT count(*) FROM b2b_research_eval.document_meta").fetchone()[0],0)
    def test_12_no_write_policies_even_after_read_policy(self):
        policies = self.admin.execute("""SELECT cmd,policyname FROM pg_policies
           WHERE schemaname='b2b_research_eval'""").fetchall()
        self.assertEqual(policies,[('SELECT','ci_reviewer_identity_read')])
    def test_13_reviewer_membership_not_cross_granted(self):
        with self.reviewer(A) as c:
            self.assertFalse(c.execute("SELECT pg_has_role(current_user,%s,'MEMBER')",(B,)).fetchone()[0])
    def test_14_ci_only_role_not_superuser(self):
        with self.reviewer(B) as c:
            self.assertEqual(c.execute("SELECT current_user").fetchone()[0],B)

    def test_15_set_role_other_reviewer_denied(self):
        with self.reviewer(A) as c:
            with self.assertRaises(InsufficientPrivilege):
                c.execute("SET ROLE " + B)
    def test_16_set_role_postgres_admin_denied(self):
        with self.reviewer(B) as c:
            with self.assertRaises(InsufficientPrivilege):
                c.execute("SET ROLE postgres")
    def test_17_cannot_create_rls_policy(self):
        with self.reviewer(A) as c:
            with self.assertRaises(InsufficientPrivilege):
                c.execute("""CREATE POLICY attacker_read ON b2b_research_eval.document_meta
                    FOR SELECT USING (true)""")
    def test_18_cannot_disable_rls(self):
        with self.reviewer(B) as c:
            with self.assertRaises(InsufficientPrivilege):
                c.execute("ALTER TABLE b2b_research_eval.document_meta DISABLE ROW LEVEL SECURITY")
    def test_19_cannot_grant_table_privileges(self):
        # PostgreSQL may issue a WARNING rather than error on an unauthorized
        # GRANT. Verify the EFFECTIVE privilege instead of an exception type.
        with self.reviewer(A) as c:
            before = c.execute(
                "SELECT has_table_privilege(%s,'b2b_research_eval.document_meta','INSERT')",
                (B,)).fetchone()[0]
            self.assertFalse(before)
            c.execute("GRANT INSERT ON b2b_research_eval.document_meta TO " + B)
            after = c.execute(
                "SELECT has_table_privilege(%s,'b2b_research_eval.document_meta','INSERT')",
                (B,)).fetchone()[0]
            self.assertFalse(after)
    def test_20_auth_principal_is_not_session_guc(self):
        with self.reviewer(A) as c:
            c.execute("SELECT set_config('b2b_eval.actor_id',%s,false)",(B,))
            self.assertEqual(c.execute("SELECT current_user").fetchone()[0], A)
            self.assertEqual(c.execute("SELECT document_id::text FROM b2b_research_eval.document_meta").fetchall(),[(DOC_A,)])
    def test_21_search_path_shadow_does_not_affect_qualified_query(self):
        with self.reviewer(A) as c:
            c.execute("SET search_path TO pg_temp, public")
            self.assertEqual(c.execute("SELECT document_id::text FROM b2b_research_eval.document_meta").fetchall(),[(DOC_A,)])
    def test_22_cross_tenant_count_is_still_one(self):
        with self.reviewer(B) as c:
            self.assertEqual(c.execute("SELECT count(*) FROM b2b_research_eval.document_meta").fetchone()[0],1)
    def test_23_cannot_delete_assigned_data(self):
        with self.reviewer(A) as c:
            with self.assertRaises(InsufficientPrivilege):
                c.execute("DELETE FROM b2b_research_eval.document_meta WHERE document_id=%s",(DOC_A,))
    def test_24_reviewer_cannot_switch_role_via_set_session_authorization(self):
        with self.reviewer(B) as c:
            with self.assertRaises(InsufficientPrivilege):
                c.execute("SET SESSION AUTHORIZATION " + A)

    def test_25_gateway_a_read_own_document(self):
        with self.reviewer(A) as c:
            result=read_assigned_document(c,document_id=DOC_A)
            self.assertEqual(result["status"],"FOUND")
            self.assertEqual(result["document"]["state"],"FROZEN")
            self.assertFalse(result["commercial_approval"])
    def test_26_gateway_a_peer_document_not_visible(self):
        with self.reviewer(A) as c:
            result=read_assigned_document(c,document_id=DOC_B)
            self.assertEqual(result["status"],"NOT_VISIBLE")
            self.assertIsNone(result["document"])
    def test_27_gateway_b_read_own_document(self):
        with self.reviewer(B) as c:
            self.assertEqual(read_assigned_document(c,document_id=DOC_B)["status"],"FOUND")
    def test_28_gateway_b_peer_document_not_visible(self):
        with self.reviewer(B) as c:
            self.assertEqual(read_assigned_document(c,document_id=DOC_A)["status"],"NOT_VISIBLE")
    def test_29_gateway_rejects_admin_connection(self):
        with self.assertRaisesRegex(GatewayRejected,"NOT_EPHEMERAL_REVIEWER"):
            read_assigned_document(self.admin,document_id=DOC_A)
    def test_30_gateway_rejects_injection_before_query(self):
        with self.reviewer(A) as c:
            with self.assertRaisesRegex(GatewayRejected,"DOCUMENT_ID_INVALID"):
                read_assigned_document(c,document_id="'; DELETE FROM x; --")
    def test_31_gateway_spoofed_guc_cannot_leak_peer(self):
        with self.reviewer(A) as c:
            c.execute("SELECT set_config('b2b_eval.actor_id',%s,false)",(B,))
            self.assertEqual(read_assigned_document(c,document_id=DOC_B)["status"],"NOT_VISIBLE")

    def test_32_signed_ci_session_a_reads_own_document(self):
        key=b"ci_fixture_key_strictly_not_for_production_12345"
        tok=issue_ci_token(role=A,now=1700000000,nonce="session-test-a-0001",signing_key=key)
        out=read_with_verified_ci_session(tok,signing_key=key,now=1700000001,
            replay_registry=set(),connect_for_role=self.reviewer,document_id=DOC_A)
        self.assertEqual(out["status"],"FOUND")
    def test_33_signed_ci_session_a_peer_document_hidden(self):
        key=b"ci_fixture_key_strictly_not_for_production_12345"
        tok=issue_ci_token(role=A,now=1700000000,nonce="session-test-a-0002",signing_key=key)
        out=read_with_verified_ci_session(tok,signing_key=key,now=1700000001,
            replay_registry=set(),connect_for_role=self.reviewer,document_id=DOC_B)
        self.assertEqual(out["status"],"NOT_VISIBLE")
    def test_34_signed_ci_session_b_peer_document_hidden(self):
        key=b"ci_fixture_key_strictly_not_for_production_12345"
        tok=issue_ci_token(role=B,now=1700000000,nonce="session-test-b-0003",signing_key=key)
        out=read_with_verified_ci_session(tok,signing_key=key,now=1700000001,
            replay_registry=set(),connect_for_role=self.reviewer,document_id=DOC_A)
        self.assertEqual(out["status"],"NOT_VISIBLE")
    def test_35_expired_session_never_opens_db_connection(self):
        key=b"ci_fixture_key_strictly_not_for_production_12345"
        tok=issue_ci_token(role=A,now=1700000000,nonce="session-test-a-0004",signing_key=key)
        called=[]
        with self.assertRaisesRegex(GatewayRejected,"TOKEN_EXPIRED_OR_NOT_YET_VALID"):
            read_with_verified_ci_session(tok,signing_key=key,now=1700000070,
                replay_registry=set(),connect_for_role=lambda role:called.append(role),document_id=DOC_A)
        self.assertEqual(called,[])

    def test_36_revoked_session_never_reads_database(self):
        authority=CiSessionAuthority(signing_key=b"ci_ephemeral_key_for_revocation_tests_1234")
        nonce="ci-live-revoked-0001"
        token=authority.issue_fixture(role=A,now=1700000000,nonce=nonce)
        authority.revoke_nonce(nonce)
        attempts=[]
        with self.assertRaisesRegex(GatewayRejected,"SESSION_REVOKED"):
            authority.read_once(token,now=1700000001,
                connect_for_role=lambda role:attempts.append(role),document_id=DOC_A)
        self.assertEqual(attempts,[])
    def test_37_rotated_session_old_token_rejected(self):
        authority=CiSessionAuthority(signing_key=b"ci_ephemeral_key_for_revocation_tests_1234")
        token=authority.issue_fixture(role=A,now=1700000000,nonce="ci-live-key-old-0001")
        authority.rotate_signing_key(b"ci_ephemeral_replacement_signing_key_1234")
        attempts=[]
        with self.assertRaisesRegex(GatewayRejected,"SIGNATURE_INVALID"):
            authority.read_once(token,now=1700000001,
                connect_for_role=lambda role:attempts.append(role),document_id=DOC_A)
        self.assertEqual(attempts,[])
    def test_38_rotated_new_session_reads_only_own_record(self):
        authority=CiSessionAuthority(signing_key=b"ci_ephemeral_key_for_revocation_tests_1234")
        authority.rotate_signing_key(b"ci_ephemeral_replacement_signing_key_1234")
        token=authority.issue_fixture(role=B,now=1700000000,nonce="ci-live-key-new-0002")
        result=authority.read_once(token,now=1700000001,
            connect_for_role=self.reviewer,document_id=DOC_A)
        self.assertEqual(result["status"],"NOT_VISIBLE")
    def test_39_disabled_authority_blocks_db_read(self):
        authority=CiSessionAuthority(signing_key=b"ci_ephemeral_key_for_revocation_tests_1234")
        token=authority.issue_fixture(role=A,now=1700000000,nonce="ci-live-disabled-0001")
        authority.disable()
        calls=[]
        with self.assertRaisesRegex(GatewayRejected,"AUTHORITY_DISABLED"):
            authority.read_once(token,now=1700000001,
                connect_for_role=lambda role:calls.append(role),document_id=DOC_A)
        self.assertEqual(calls,[])

if __name__ == "__main__":
    unittest.main(verbosity=2)
