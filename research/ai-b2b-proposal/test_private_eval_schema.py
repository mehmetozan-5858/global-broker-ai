import unittest
from pathlib import Path
from check_private_eval_schema import SCHEMA, audit_sql

class PrivateSchemaReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql=SCHEMA.read_text(encoding="utf-8")
    def test_01_scoped_schema_structure(self):
        self.assertTrue(audit_sql(self.sql)["valid_structure"])
    def test_02_no_security_approval_claim(self):
        self.assertFalse(audit_sql(self.sql)["security_approved"])
        self.assertFalse(audit_sql(self.sql)["live_database_tested"])
    def test_03_no_connection_strings_or_secrets(self):
        self.assertNotIn("postgresql://",self.sql.lower())
        self.assertNotIn("password =",self.sql.lower())
    def test_04_no_role_creation_or_grants(self):
        text=self.sql.upper()
        self.assertNotIn("CREATE ROLE ",text)
        self.assertNotIn("GRANT SELECT",text)
        self.assertNotIn("GRANT INSERT",text)
    def test_05_detect_removed_rls(self):
        changed=self.sql.replace("ENABLE ROW LEVEL SECURITY","NOT ENABLED")
        self.assertFalse(audit_sql(changed)["valid_structure"])
    def test_06_detect_drop_database(self):
        self.assertFalse(audit_sql(self.sql+"\nDROP DATABASE customer;")["valid_structure"])
    def test_07_reject_unsupported_input(self):
        with self.assertRaisesRegex(ValueError,"SQL_INPUT_INVALID"):
            audit_sql(None)
    def test_08_customer_raw_text_not_in_schema(self):
        self.assertNotIn("document_body",self.sql.lower())
        self.assertNotIn("pdf_blob",self.sql.lower())
    def test_09_deny_insert_update_policies(self):
        self.assertNotIn("FOR INSERT ",self.sql.upper())
        self.assertNotIn("FOR UPDATE ",self.sql.upper())
        self.assertNotIn("FOR DELETE ",self.sql.upper())
    def test_11_spoofable_policy_forbidden(self):
        compromised = self.sql + "\\nCREATE POLICY bad ON x USING (current_setting('role')='admin');"
        self.assertFalse(audit_sql(compromised)["valid_structure"])
    def test_12_rbac_grants_forbidden(self):
        self.assertFalse(audit_sql(self.sql+"\\nGRANT SELECT ON x TO PUBLIC;")["valid_structure"])
    def test_10_isolation_caveat_present(self):
        self.assertIn("caller-controlled session settings",self.sql)
        self.assertIn("DO NOT EXECUTE IN PRODUCTION",self.sql)

if __name__ == "__main__":
    unittest.main(verbosity=2)
