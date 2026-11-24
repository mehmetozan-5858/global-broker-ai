"""CI-only reconciliation inspection after uncertain DB/witness outcome.

NEVER grants, retries, unspends, revokes, or advances a witness. Every
outcome is NO_GRANT. Requires independently authenticated durable witness,
which is not supplied by these test fixtures. DO NOT deploy to Neon/prod.
"""
from ci_reviewer_read_gateway import GatewayRejected
from ci_external_recovery_witness import verify_recovery_witness
from ci_pg_shared_session_gate import _guard_connection, _lock_state, _nonce_digest
from ci_signed_reviewer_session import verify_ci_token


def reconcile_without_authorizing(conn, token, *, signing_key, now,
                                  provider, witness_key):
    """Inspect the committed nonce state and signed external floor, fail closed.

    A 'repair needed' result is *not* evidence that a witness can safely be
    advanced; an independently attested operator must resolve uncertainty.
    """
    if provider is None or not callable(getattr(provider, "read", None)):
        raise GatewayRejected("RECONCILE_WITNESS_UNAVAILABLE")
    try:
        record = provider.read()
    except Exception as exc:
        raise GatewayRejected("RECONCILE_WITNESS_READ_FAILED") from exc
    if not isinstance(record, tuple) or len(record) != 2:
        raise GatewayRejected("RECONCILE_WITNESS_INVALID")
    witness, trusted_floor = record
    # Verify the witness before touching DB.
    witness_generation = verify_recovery_witness(
        witness, signing_key=witness_key, trusted_min_generation=trusted_floor)
    claims = verify_ci_token(token, signing_key=signing_key, now=now)
    nonce_digest = _nonce_digest(claims["jti"])
    _guard_connection(conn)
    with conn.transaction():
        _lock_state(conn)
        state = conn.execute("""SELECT generation FROM b2b_eval_ci_control.state
            WHERE singleton=1""").fetchone()
        if state is None:
            raise GatewayRejected("RECONCILE_DB_STATE_MISSING")
        generation = state[0]
        nonce_row = conn.execute("""SELECT state FROM b2b_eval_ci_control.nonces
            WHERE nonce_digest=%s""", (nonce_digest,)).fetchone()
    if generation < witness_generation:
        status = "BLOCKED_DB_ROLLBACK"
    elif nonce_row is None:
        status = "BLOCKED_NO_COMMITTED_NONCE"
    elif nonce_row[0] == "REVOKED":
        status = "BLOCKED_REVOKED"
    elif nonce_row[0] != "SPENT":
        status = "BLOCKED_UNEXPECTED_NONCE_STATE"
    elif witness_generation < generation:
        status = "BLOCKED_WITNESS_LAG_OPERATOR_REVIEW"
    else:
        status = "BLOCKED_SPENT_NO_REAUTHORIZATION"
    return {"status": status, "authorized": False, "retry_consumption": False,
            "auto_advance_witness": False, "db_generation": generation,
            "witness_generation": witness_generation}
