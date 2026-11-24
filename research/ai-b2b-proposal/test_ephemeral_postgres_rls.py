"""Ephemeral PostgreSQL 16 authorization checks. NEVER connect this to Neon.

Requires B2B_CI_PG_DSN for throwaway GitHub Actions service only.
No customer data, no production credentials, no external database.
"""
import os
from pathlib import Path
import unittest
from uuid import UUID

import psycopg
from psycopg.errors import InsufficientPrivilege

ADMIN_DSN = os.environ.get("B2B_CI_PG_DSN")
READER_DSN = os.environ.get("B2B_CI_READER_DSN")
SQL = Path(__file__).with_name("private_eval_postgres.sql")
SAMPLE_ID = "00000000-0000-4000-8000-000000000001"

@unittest.skipUnless(ADMIN_DSN and READER_DSN, "isolated CI postgres DSNs not provided")
class PgDefaultDenyIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = psycopg.connect(ADMIN_DSN, autocommit=True)
        # A separate test-only database is mandatory; fail if misconfigured.
        db = cls.admin.execute("SELECT current_database()").fetchone()[0]
        if db != "proposal_eval_ci":
            cls.admin.close()
            raise RuntimeError("REFUSE_NON_EPHEMERAL_DB")
        cls.admin.execute(SQL.read_text(encoding="utf-8"), prepare=False)
        cls.admin.execute("CREATE ROLE b2b_eval_ci_reader LOGIN PASSWORD 'local_ci_only_reader'")
        # Grant table privileges ONLY in temporary CI DB to prove RLS still denies access.
        cls.admin.execute("GRANT USAGE ON SCHEMA b2b_research_eval TO b2b_eval_ci_reader")
        cls.admin.execute("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA b2b_research_eval TO b2b_eval_ci_reader")
        cls.admin.execute("""INSERT INTO b2b_research_eval.document_meta
            (document_id, source_sha256, manifest_sha256, assigned_reviewer, lifecycle_state)
            VALUES (%s, %s, %s, %s, %s)""",
            (SAMPLE_ID,"a"*64,"b"*64,"test_reviewer","RECEIVED"))
    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "admin"):
            cls.admin.close()
    def reader(self):
        return psycopg.connect(READER_DSN, autocommit=True)
    def test_01_rls_forced_on_all_three_tables(self):
        results=self.admin.execute("""SELECT relname, relrowsecurity, relforcerowsecurity
          FROM pg_class WHERE relnamespace='b2b_research_eval'::regnamespace
          AND relkind='r' ORDER BY relname""").fetchall()
        self.assertEqual(len(results),3)
        self.assertTrue(all(row[1] and row[2] for row in results),results)
    def test_02_no_rls_policies_exist(self):
        count=self.admin.execute("SELECT count(*) FROM pg_policies WHERE schemaname='b2b_research_eval'").fetchone()[0]
        self.assertEqual(count,0)
    def test_03_sample_visible_only_to_admin_test_fixture(self):
        self.assertEqual(self.admin.execute("SELECT count(*) FROM b2b_research_eval.document_meta").fetchone()[0],1)
        with self.reader() as c:
            self.assertEqual(c.execute("SELECT count(*) FROM b2b_research_eval.document_meta").fetchone()[0],0)
    def test_04_reader_cannot_insert_even_with_granted_privilege(self):
        with self.reader() as c:
            with self.assertRaises(InsufficientPrivilege):
                c.execute("""INSERT INTO b2b_research_eval.document_meta
                    (document_id,source_sha256,manifest_sha256,assigned_reviewer,lifecycle_state)
                    VALUES (%s,%s,%s,%s,%s)""",
                    ("00000000-0000-4000-8000-000000000002","a"*64,"b"*64,"fake","RECEIVED"))
    def test_05_reader_cannot_update_or_delete(self):
        with self.reader() as c:
            self.assertEqual(c.execute("UPDATE b2b_research_eval.document_meta SET assigned_reviewer='attacker'").rowcount,0)
            self.assertEqual(c.execute("DELETE FROM b2b_research_eval.document_meta").rowcount,0)
        self.assertEqual(self.admin.execute("SELECT count(*) FROM b2b_research_eval.document_meta").fetchone()[0],1)
    def test_06_spoofed_session_guc_does_not_unlock(self):
        with self.reader() as c:
            c.execute("SELECT set_config('b2b_eval.actor_role','custodian',false)")
            c.execute("SELECT set_config('b2b_eval.actor_id','test_reviewer',false)")
            self.assertEqual(c.execute("SELECT count(*) FROM b2b_research_eval.document_meta").fetchone()[0],0)
    def test_07_reader_not_bypass_rls_or_superuser(self):
        with self.reader() as c:
            result=c.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user").fetchone()
            self.assertEqual(result,(False,False))
    def test_08_insert_denied_on_review_and_audit(self):
        with self.reader() as c:
            with self.assertRaises(InsufficientPrivilege):
                c.execute("""INSERT INTO b2b_research_eval.review
                 (review_id,document_id,reviewer_id,outcome)
                 VALUES (%s,%s,%s,%s)""",
                 ("00000000-0000-4000-8000-000000000003",SAMPLE_ID,"fake","POSITIVE"))

if __name__ == "__main__":
    unittest.main(verbosity=2)
