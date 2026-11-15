import unittest
from unittest.mock import patch

from ci_reviewer_read_gateway import GatewayRejected
from ci_external_recovery_witness import issue_fixture_witness
from ci_required_witness_gate import consume_with_required_provider

KEY=b"synthetic_ci_session_key_only_0123456789012345"
WKEY=b"synthetic_ci_witness_key_only_0123456789012345"
TOKEN="synthetic-token-for-mocked-coordinator"
NOW=1700000001
ROLE="b2b_eval_ci_reviewer_a"


class FakeConn:
    def __init__(self):self.closed=False
    def close(self):self.closed=True


class FakeWitnessProvider:
    def __init__(self, generation=5):
        self.generation=generation
        self.floor=generation
        self.read_error=None
        self.advance_error=None
        self.confirm=True
        self.stay_stale=False
        self.reads=0
        self.advances=[]
    def read(self):
        self.reads+=1
        if self.read_error:raise self.read_error
        return (issue_fixture_witness(self.generation,signing_key=WKEY),self.floor)
    def advance(self,generation):
        self.advances.append(generation)
        if self.advance_error:raise self.advance_error
        if not self.stay_stale:
            self.generation=max(self.generation,generation)
            self.floor=max(self.floor,generation)
        return self.confirm


class RequiredWitnessUnitTests(unittest.TestCase):
    def execute(self,provider,conn_factory, generation=6,consume_exception=None):
        def fake_consume(conn,*args,**kwargs):
            if consume_exception:raise consume_exception
            return ROLE
        with patch("ci_required_witness_gate.consume_with_signed_witness",
                   side_effect=fake_consume),patch(
                   "ci_required_witness_gate.current_generation_for_ci_witness",
                   return_value=generation):
            return consume_with_required_provider(
                conn_factory,TOKEN,signing_key=KEY,now=NOW,
                provider=provider,witness_key=WKEY)
    def rejection(self,code,provider,connection=None,**kwargs):
        created=[]
        def factory():
            c=connection or FakeConn()
            created.append(c)
            return c
        with self.assertRaisesRegex(GatewayRejected,code):
            self.execute(provider,factory,**kwargs)
        return created
    def test_01_valid_witness_acknowledged(self):
        provider=FakeWitnessProvider();conn=FakeConn()
        self.assertEqual(self.execute(provider,lambda:conn),ROLE)
        self.assertEqual(provider.advances,[6])
        self.assertTrue(conn.closed)
        self.assertGreaterEqual(provider.reads,2)
    def test_02_missing_provider_denied_before_connection(self):
        self.assertEqual(self.rejection("WITNESS_PROVIDER_UNAVAILABLE",None),[])
    def test_03_provider_read_exception_denied_before_connection(self):
        p=FakeWitnessProvider();p.read_error=TimeoutError("fixture timeout")
        self.assertEqual(self.rejection("WITNESS_PROVIDER_READ_FAILED",p),[])
    def test_04_malformed_provider_record(self):
        class Provider:
            def read(self):return ("wrong",)
        self.assertEqual(self.rejection("WITNESS_PROVIDER_MALFORMED",Provider()),[])
    def test_05_missing_trusted_floor(self):
        p=FakeWitnessProvider();p.floor=None
        self.assertEqual(self.rejection("WITNESS_FLOOR_INVALID",p),[])
    def test_06_older_witness(self):
        p=FakeWitnessProvider();p.floor=6
        self.assertEqual(self.rejection("WITNESS_ROLLBACK_DETECTED",p),[])
    def test_07_bad_signature(self):
        class Provider:
            def read(self):
                return (issue_fixture_witness(5,signing_key=b"other_ci_witness_key_only_012345678901"),5)
        self.assertEqual(self.rejection("WITNESS_SIGNATURE_INVALID",Provider()),[])
    def test_08_bad_connection_factory(self):
        with self.assertRaisesRegex(GatewayRejected,"COORDINATOR_CONNECTION_FACTORY_INVALID"):
            self.execute(FakeWitnessProvider(),None)
    def test_09_connection_failure(self):
        def factory():raise TimeoutError("no database")
        with self.assertRaisesRegex(GatewayRejected,"COORDINATOR_CONNECTION_FAILED"):
            self.execute(FakeWitnessProvider(),factory)
    def test_10_commit_uncertainty_denied_and_connection_closed(self):
        c=FakeConn()
        self.rejection("COORDINATOR_TRANSACTION_UNCERTAIN",FakeWitnessProvider(),
                       connection=c,consume_exception=ConnectionError("unknown commit"))
        self.assertTrue(c.closed)
    def test_11_witness_write_timeout_denies_after_db_commit(self):
        p=FakeWitnessProvider();p.advance_error=TimeoutError("disk unavailable")
        c=FakeConn()
        self.rejection("WITNESS_PERSISTENCE_FAILED",p,connection=c)
        self.assertEqual(p.advances,[6])
        self.assertTrue(c.closed)
    def test_12_write_unconfirmed_denied(self):
        p=FakeWitnessProvider();p.confirm=False
        self.rejection("WITNESS_PERSISTENCE_UNCONFIRMED",p)
    def test_13_write_ack_but_old_value_denied(self):
        p=FakeWitnessProvider();p.stay_stale=True
        self.rejection("WITNESS_PERSISTENCE_STALE",p)
    def test_14_witness_read_fails_after_commit(self):
        p=FakeWitnessProvider()
        old=p.read
        def read_twice():
            if p.reads>=1:raise TimeoutError("post-commit witness unavailable")
            return old()
        p.read=read_twice
        self.rejection("WITNESS_PROVIDER_READ_FAILED",p)
        self.assertEqual(p.advances,[6])
    def test_15_missing_advance_method_denied(self):
        class Provider:
            def read(self):return (issue_fixture_witness(5,signing_key=WKEY),5)
        self.rejection("WITNESS_PERSISTENCE_UNAVAILABLE",Provider())

if __name__=="__main__":
    unittest.main(verbosity=2)
