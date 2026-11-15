"""Real pg_dump/pg_restore rollback exercise in disposable PostgreSQL CI.

Orchestrated by the dedicated CI job; phases use a throwaway DB and synthetic
tokens only. Trust floor stays in runner process, not a real independent WORM
witness. NEVER run against Neon, production, or customer data.
"""
import os
import sys
import psycopg
from ci_reviewer_read_gateway import GatewayRejected
from ci_pg_shared_session_gate import (
    setup_ci_coordinator, consume_once, current_generation_for_ci_witness
)
from ci_external_recovery_witness import (
    issue_fixture_witness, consume_with_signed_witness
)
from ci_signed_reviewer_session import issue_ci_token

DSN = os.environ.get("B2B_CI_PG_DSN")
DB = "proposal_eval_ci"
KEY = b"ci_only_backup_restore_signing_key_0123456789"
WITNESS_KEY = b"ci_only_external_backup_witness_key_0123456"
ROLE = "b2b_eval_ci_reviewer_a"
NONCE = "backup-restored-token-001"
NOW = 1700000000


def _conn():
    if not DSN:
        raise RuntimeError("MISSING_EPHEMERAL_DSN")
    conn = psycopg.connect(DSN, autocommit=True)
    if conn.info.dbname != DB or conn.info.user != "postgres" or conn.info.host not in (
            "127.0.0.1", "localhost"):
        conn.close()
        raise RuntimeError("REFUSE_NON_EPHEMERAL_POSTGRES")
    return conn


def _token():
    return issue_ci_token(role=ROLE, now=NOW, nonce=NONCE, signing_key=KEY)


def initialize():
    with _conn() as conn:
        setup_ci_coordinator(conn, signing_key=KEY)
        assert current_generation_for_ci_witness(conn) == 0
        print("INITIALIZED_FRESH_EPHEMERAL_DB")


def advance():
    with _conn() as conn:
        assert consume_once(conn, _token(), signing_key=KEY, now=NOW+1) == ROLE
        assert current_generation_for_ci_witness(conn) == 1
        print("CONSUMED_AND_GENERATION_ADVANCED")


def before_restore():
    with _conn() as conn:
        assert current_generation_for_ci_witness(conn) == 1
        conn.execute("DROP SCHEMA b2b_eval_ci_control CASCADE")
        print("ISOLATED_TEST_SCHEMA_REMOVED_FOR_RESTORE")


def verify_restore():
    witness = issue_fixture_witness(1, signing_key=WITNESS_KEY)
    with _conn() as conn:
        assert current_generation_for_ci_witness(conn) == 0, "BACKUP_WAS_NOT_RESTORED"
        # The restored DB has forgotten the consumed nonce; the independent
        # witness pin is the ONLY reason the stale authorization is rejected.
        try:
            consume_with_signed_witness(
                conn, _token(), signing_key=KEY, now=NOW+1,
                witness=witness, witness_key=WITNESS_KEY,
                trusted_min_generation=1)
        except GatewayRejected as exc:
            assert str(exc) == "RECOVERY_ROLLBACK_DETECTED", str(exc)
        else:
            raise AssertionError("UNSAFE_RESTORED_DB_ACCEPTED_OLD_TOKEN")
        assert current_generation_for_ci_witness(conn) == 0
        print("RESTORED_OLD_TOKEN_REJECTED_WITH_EXTERNAL_PIN")


if __name__=="__main__":
    phases={"init":initialize,"advance":advance,"before_restore":before_restore,
            "verify":verify_restore}
    if len(sys.argv)!=2 or sys.argv[1] not in phases:
        raise SystemExit("EXPECTED_INIT_ADVANCE_BEFORE_RESTORE_OR_VERIFY")
    phases[sys.argv[1]]()
