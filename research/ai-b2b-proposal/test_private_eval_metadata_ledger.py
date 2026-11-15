import os
import sqlite3
import stat
import tempfile
import unittest
from pathlib import Path
from private_eval_metadata_ledger import (
    open_metadata_ledger, intake_metadata, transition_metadata,
    verify_audit_chain, sanitized_summary, LedgerRejected
)

def create_record(conn, rid="DOC1", reviewer="REV1"):
    intake_metadata(conn,record_id=rid,source_digest="a"*64,manifest_digest="b"*64,
                    reviewer_id=reviewer,actor_id="CUST1",role="custodian")

class MetadataLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"eval.sqlite3"
        self.conn=open_metadata_ledger(self.path)
    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()
    def rejected(self, code, fn):
        with self.assertRaisesRegex(LedgerRejected,code):fn()
    def test_01_new_file_owner_only(self):
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode),0o600)
    def test_02_record_is_metadata_only(self):
        create_record(self.conn)
        out=sanitized_summary(self.conn)
        self.assertEqual(out["states"],{"RECEIVED":1})
        self.assertEqual(out["audit_events"],1)
        self.assertTrue(out["audit_chain_valid"])
        self.assertFalse(out["real_customer_data_authorized"])
    def test_03_custodian_can_freeze(self):
        create_record(self.conn)
        transition_metadata(self.conn,record_id="DOC1",new_state="FROZEN",
                            actor_id="CUST1",role="custodian")
        self.assertEqual(sanitized_summary(self.conn)["states"],{"FROZEN":1})
    def test_04_only_assigned_reviewer_can_review(self):
        create_record(self.conn)
        transition_metadata(self.conn,record_id="DOC1",new_state="FROZEN",
                            actor_id="CUST1",role="custodian")
        self.rejected("REVIEWER_NOT_ASSIGNED",lambda:transition_metadata(
            self.conn,record_id="DOC1",new_state="REVIEWED",actor_id="REV2",role="reviewer"))
        transition_metadata(self.conn,record_id="DOC1",new_state="REVIEWED",
                            actor_id="REV1",role="reviewer")
        self.assertTrue(verify_audit_chain(self.conn))
    def test_05_non_custodian_cannot_intake(self):
        self.rejected("CUSTODIAN_REQUIRED",lambda:intake_metadata(
            self.conn,record_id="DOC2",source_digest="a"*64,manifest_digest="b"*64,
            reviewer_id="REV1",actor_id="REV1",role="reviewer"))
    def test_06_duplicate_record(self):
        create_record(self.conn)
        self.rejected("DUPLICATE_RECORD",lambda:create_record(self.conn))
    def test_07_bad_digest(self):
        self.rejected("DIGEST_INVALID",lambda:intake_metadata(
            self.conn,record_id="DOC1",source_digest="bad",manifest_digest="b"*64,
            reviewer_id="REV1",actor_id="CUST1",role="custodian"))
    def test_08_reject_sql_injection_in_id(self):
        self.rejected("IDENTIFIER_INVALID",lambda:create_record(self.conn,"' OR 1=1 --"))
    def test_09_illegal_skip_to_reviewed(self):
        create_record(self.conn)
        self.rejected("ILLEGAL_STATE_TRANSITION",lambda:transition_metadata(
            self.conn,record_id="DOC1",new_state="REVIEWED",actor_id="REV1",role="reviewer"))
    def test_10_quarantined_does_not_reopen(self):
        create_record(self.conn)
        transition_metadata(self.conn,record_id="DOC1",new_state="QUARANTINED",
                            actor_id="CUST1",role="custodian")
        self.rejected("ILLEGAL_STATE_TRANSITION",lambda:transition_metadata(
            self.conn,record_id="DOC1",new_state="FROZEN",actor_id="CUST1",role="custodian"))
    def test_11_reviewer_cannot_freeze(self):
        create_record(self.conn)
        self.rejected("ILLEGAL_STATE_TRANSITION",lambda:transition_metadata(
            self.conn,record_id="DOC1",new_state="FROZEN",actor_id="REV1",role="reviewer"))
    def test_12_unknown_record(self):
        self.rejected("RECORD_UNKNOWN",lambda:transition_metadata(
            self.conn,record_id="UNKNOWN",new_state="FROZEN",actor_id="CUST1",role="custodian"))
    def test_13_bad_actor_role(self):
        self.rejected("ACTOR_OR_ROLE_INVALID",lambda:intake_metadata(
            self.conn,record_id="DOC1",source_digest="a"*64,manifest_digest="b"*64,
            reviewer_id="REV1",actor_id="NO ROLE",role="superuser"))
    def test_14_audit_sql_update_blocked(self):
        create_record(self.conn)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE audit SET event='FORGED'")
    def test_15_audit_sql_delete_blocked(self):
        create_record(self.conn)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM audit")
    def test_16_intake_sql_delete_blocked(self):
        create_record(self.conn)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM intake")
    def test_17_hash_chain_detects_injected_bad_audit_row(self):
        create_record(self.conn)
        self.conn.execute("""INSERT INTO audit(record_id,actor_id,actor_role,event,event_digest,previous_digest)
                           VALUES('DOC1','CUST1','custodian','FORGED',?,?)""",("f"*64,"0"*64))
        self.assertFalse(verify_audit_chain(self.conn))
    def test_18_reopen_owner_only_db(self):
        self.conn.close()
        self.conn=open_metadata_ledger(self.path)
        self.assertTrue(verify_audit_chain(self.conn))
    def test_19_reject_world_readable_existing_db(self):
        self.conn.close();os.chmod(self.path,0o644)
        self.rejected("FILE_PERMISSIONS_TOO_BROAD",lambda:open_metadata_ledger(self.path))
        os.chmod(self.path,0o600)
        self.conn=open_metadata_ledger(self.path)
    def test_20_reject_relative_path(self):
        self.rejected("ABSOLUTE_PATH_REQUIRED",lambda:open_metadata_ledger("relative.sqlite3"))
    def test_21_reject_symlink(self):
        other=Path(self.tmp.name)/"link.sqlite3"
        other.symlink_to(self.path)
        self.rejected("FILE_NOT_REGULAR",lambda:open_metadata_ledger(other))
    def test_22_summary_no_case_ids_or_document_text(self):
        create_record(self.conn,"SENSITIVE_CASE_MARKER")
        public=str(sanitized_summary(self.conn))
        self.assertNotIn("SENSITIVE_CASE_MARKER",public)
        self.assertFalse(sanitized_summary(self.conn)["commercial_approval"])

if __name__=="__main__":
    unittest.main(verbosity=2)
