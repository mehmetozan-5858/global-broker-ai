"""Identity-scoped RLS proof in a throwaway CI PostgreSQL database only.

The CI fixture uses distinct PostgreSQL LOGIN principals and CURRENT_USER,
not spoofable application-defined session settings. It does NOT provide real
login/auth gateway, durable audit custody, Neon validation or production access.
"""
import os
import unittest
import psycopg
from psycopg.errors import InsufficientPrivilege

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
        policies = self.admin.execute("""SELECT cmd,polname FROM pg_policies
           WHERE schemaname='b2b_research_eval'""").fetchall()
        self.assertEqual(policies,[('SELECT','ci_reviewer_identity_read')])
    def test_13_reviewer_membership_not_cross_granted(self):
        with self.reviewer(A) as c:
            self.assertFalse(c.execute("SELECT pg_has_role(current_user,%s,'MEMBER')",(B,)).fetchone()[0])
    def test_14_ci_only_role_not_superuser(self):
        with self.reviewer(B) as c:
            self.assertEqual(c.execute("SELECT current_user").fetchone()[0],B)

if __name__ == "__main__":
    unittest.main(verbosity=2)
