"""Research-only fail-closed witness dependency for disposable PostgreSQL CI.

The caller supplies an independently managed witness provider. This module
DOES NOT implement a real immutable/durable provider or distributed 2PC.
No access authorization is returned unless both PG consume and witness
persistence complete. A failed persistence burns a token (safe denial).
"""
from ci_reviewer_read_gateway import GatewayRejected
from ci_external_recovery_witness import (
    verify_recovery_witness, consume_with_signed_witness,
)
from ci_pg_shared_session_gate import current_generation_for_ci_witness


def _snapshot(provider):
    if provider is None or not callable(getattr(provider, "read", None)):
        raise GatewayRejected("WITNESS_PROVIDER_UNAVAILABLE")
    try:
        record = provider.read()
    except Exception as exc:
        raise GatewayRejected("WITNESS_PROVIDER_READ_FAILED") from exc
    if (not isinstance(record, tuple) or len(record) != 2):
        raise GatewayRejected("WITNESS_PROVIDER_MALFORMED")
    return record


def consume_with_required_provider(
        conn_factory, token, *, signing_key, now, provider, witness_key):
    """Fail closed if trusted witness unavailable, malformed or uncommitted.

    A provider must independently preserve a monotonic lower bound. The
    fixture is NOT a strong independent source of truth. A DB commit followed
    by a failed witness write leaves consumed token but returns no authority.
    """
    if not callable(conn_factory):
        raise GatewayRejected("COORDINATOR_CONNECTION_FACTORY_INVALID")
    witness, trusted_floor = _snapshot(provider)
    # Validate before opening any DB connection.
    verify_recovery_witness(witness, signing_key=witness_key,
                            trusted_min_generation=trusted_floor)
    try:
        conn = conn_factory()
    except Exception as exc:
        raise GatewayRejected("COORDINATOR_CONNECTION_FAILED") from exc
    if conn is None:
        raise GatewayRejected("COORDINATOR_CONNECTION_FAILED")
    try:
        role = consume_with_signed_witness(
            conn, token, signing_key=signing_key, now=now,
            witness=witness, witness_key=witness_key,
            trusted_min_generation=trusted_floor)
        committed_generation = current_generation_for_ci_witness(conn)
    except GatewayRejected:
        raise
    except Exception as exc:
        raise GatewayRejected("COORDINATOR_TRANSACTION_UNCERTAIN") from exc
    finally:
        conn.close()
    # A POST-COMMIT failure is fail-closed but cannot roll back consumption.
    if not callable(getattr(provider, "advance", None)):
        raise GatewayRejected("WITNESS_PERSISTENCE_UNAVAILABLE")
    try:
        acknowledged = provider.advance(committed_generation)
    except Exception as exc:
        raise GatewayRejected("WITNESS_PERSISTENCE_FAILED") from exc
    if acknowledged is not True:
        raise GatewayRejected("WITNESS_PERSISTENCE_UNCONFIRMED")
    # Recheck the provider, do not trust an acknowledgement by itself.
    after, floor_after = _snapshot(provider)
    verified = verify_recovery_witness(
        after, signing_key=witness_key, trusted_min_generation=floor_after)
    if verified < committed_generation or floor_after < committed_generation:
        raise GatewayRejected("WITNESS_PERSISTENCE_STALE")
    return role
