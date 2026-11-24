import unittest
from ci_reviewer_read_gateway import read_assigned_document, GatewayRejected

DOC="00000000-0000-4000-8000-000000000011"
class FakeCursor:
    def __init__(self, value): self.value=value
    def fetchone(self): return self.value
class FakeConn:
    def __init__(self, identity=("proposal_eval_ci","b2b_eval_ci_reviewer_a"),
                 row=(DOC,"FROZEN")):
        self.identity=identity
        self.row=row
        self.queries=[]
    def execute(self, query, params=None):
        self.queries.append((query,params))
        if query=="SELECT current_database(), current_user":return FakeCursor(self.identity)
        if params is not None:return FakeCursor(self.row)
        raise AssertionError("unknown query")

class ReviewerGatewayUnitTests(unittest.TestCase):
    def rejected(self, code, conn, doc=DOC):
        with self.assertRaisesRegex(GatewayRejected,code):
            read_assigned_document(conn,document_id=doc)
    def test_01_valid_single_read(self):
        c=FakeConn()
        out=read_assigned_document(c,document_id=DOC)
        self.assertEqual(out["status"],"FOUND")
        self.assertFalse(out["commercial_approval"])
        self.assertEqual(c.queries[1][1],(DOC,))
    def test_02_missing_row_no_leak(self):
        out=read_assigned_document(FakeConn(row=None),document_id=DOC)
        self.assertEqual(out["status"],"NOT_VISIBLE")
        self.assertIsNone(out["document"])
    def test_03_neon_or_prod_db_rejected(self):
        self.rejected("NOT_EPHEMERAL_REVIEWER",FakeConn(identity=("neondb","b2b_eval_ci_reviewer_a")))
    def test_04_admin_role_rejected(self):
        self.rejected("NOT_EPHEMERAL_REVIEWER",FakeConn(identity=("proposal_eval_ci","postgres")))
    def test_05_unknown_reviewer_rejected(self):
        self.rejected("NOT_EPHEMERAL_REVIEWER",FakeConn(identity=("proposal_eval_ci","attacker")))
    def test_06_noncanonical_uuid_rejected(self):
        self.rejected("DOCUMENT_ID_NOT_CANONICAL",FakeConn(),"AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA")
    def test_07_sql_injection_id_rejected(self):
        self.rejected("DOCUMENT_ID_INVALID",FakeConn(),"x'; DROP TABLE foo; --")
    def test_08_nonstring_document_rejected(self):
        self.rejected("DOCUMENT_ID_INVALID",FakeConn(),42)
    def test_09_connection_missing_rejected(self):
        self.rejected("CONNECTION_INVALID",None)
    def test_10_mismatched_row_rejected(self):
        self.rejected("UNEXPECTED_RESULT",FakeConn(row=("00000000-0000-4000-8000-000000000012","FROZEN")))
    def test_11_unexpected_state_rejected(self):
        self.rejected("UNEXPECTED_RESULT",FakeConn(row=(DOC,"APPROVED")))
    def test_12_nonpositional_queries_forbidden(self):
        c=FakeConn()
        read_assigned_document(c,document_id=DOC)
        self.assertEqual(len(c.queries),2)
        self.assertEqual(c.queries[1][1],(DOC,))
        self.assertNotIn(DOC,c.queries[1][0])
    def test_13_identity_missing_rejected(self):
        self.rejected("NOT_EPHEMERAL_REVIEWER",FakeConn(identity=None))
    def test_14_no_request_provided_role_parameter(self):
        import inspect
        self.assertEqual(list(inspect.signature(read_assigned_document).parameters),["conn","document_id"])

if __name__=="__main__":
    unittest.main(verbosity=2)
