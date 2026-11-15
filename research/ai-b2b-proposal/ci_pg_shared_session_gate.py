"""Research-only shared session coordination with disposable PostgreSQL 16.

Uses a transaction-scoped control-row lock to serialize consume/revoke/rotate
across independent database connections. Only synthetic identities and
ephemeral CI database; NOT a real authentication service.
"""
import hashlib
import re

from ci_reviewer_read_gateway import GatewayRejected
from ci_signed_reviewer_session import verify_ci_token

_DB = "proposal_eval_ci"
_NONCE = re.compile(r"^[A-Za-z0-9_-]{16,100}$")


def _guard_connection(conn):
    if conn is None or not callable(getattr(conn, "execute", None)):
        raise GatewayRejected("COORDINATOR_CONNECTION_MISSING")
    # Use psycopg's authenticated connection metadata, avoiding an implicit
    # transaction before the explicit context manager below.
    identity = (getattr(getattr(conn, "info", None), "dbname", None),
                getattr(getattr(conn, "info", None), "user", None))
    if identity != (_DB, "postgres"):
        raise GatewayRejected("COORDINATOR_NOT_EPHEMERAL_ADMIN")
    if not conn.autocommit:
        raise GatewayRejected("COORDINATOR_AUTOCOMMIT_REQUIRED")


def _fingerprint(key):
    if not isinstance(key, bytes) or len(key) < 32:
        raise GatewayRejected("SIGNING_KEY_INVALID")
    return hashlib.sha256(key).hexdigest()


def setup_ci_coordinator(conn, *, signing_key):
    """Only for blank GitHub Actions PostgreSQL database, never Neon."""
    _guard_connection(conn)
    digest = _fingerprint(signing_key)
    with conn.transaction():
        conn.execute("CREATE SCHEMA b2b_eval_ci_control")
        conn.execute("""CREATE TABLE b2b_eval_ci_control.state (
            singleton integer PRIMARY KEY CHECK (singleton = 1),
            active_key_sha256 char(64) NOT NULL,
            disabled boolean NOT NULL DEFAULT false)""")
        conn.execute("""CREATE TABLE b2b_eval_ci_control.nonces (
            nonce_digest char(64) PRIMARY KEY,
            state text NOT NULL CHECK (state IN ('SPENT','REVOKED')) )""")
        conn.execute("""CREATE TABLE b2b_eval_ci_control.retired_keys (
            key_sha256 char(64) PRIMARY KEY)""")
        conn.execute("REVOKE ALL ON SCHEMA b2b_eval_ci_control FROM PUBLIC")
        conn.execute("""INSERT INTO b2b_eval_ci_control.state
            (singleton,active_key_sha256) VALUES (1,%s)""", (digest,))


def _lock_state(conn):
    row = conn.execute("""SELECT active_key_sha256,disabled
        FROM b2b_eval_ci_control.state WHERE singleton=1 FOR UPDATE""").fetchone()
    if row is None:
        raise GatewayRejected("COORDINATOR_STATE_MISSING")
    if row[1]:
        raise GatewayRejected("COORDINATOR_DISABLED")
    return row[0]


def _nonce_digest(nonce):
    if not isinstance(nonce, str) or not _NONCE.fullmatch(nonce):
        raise GatewayRejected("COORDINATOR_NONCE_INVALID")
    return hashlib.sha256(nonce.encode("ascii")).hexdigest()


def consume_once(conn, token, *, signing_key, now):
    """Atomic shared one-time consumption; returns verified role, no DB read.

    The control-row lock serializes with revoke/rotate. It does NOT prevent an
    already started read from completing after revocation.
    """
    _guard_connection(conn)
    fp = _fingerprint(signing_key)
    claims = verify_ci_token(token, signing_key=signing_key, now=now)
    nonce = _nonce_digest(claims["jti"])
    with conn.transaction():
        active = _lock_state(conn)
        if active != fp:
            raise GatewayRejected("COORDINATOR_KEY_RETIRED")
        existing = conn.execute("""SELECT state FROM b2b_eval_ci_control.nonces
            WHERE nonce_digest=%s""", (nonce,)).fetchone()
        if existing:
            raise GatewayRejected("SESSION_REVOKED" if existing[0]=="REVOKED" else "SESSION_REPLAY")
        conn.execute("""INSERT INTO b2b_eval_ci_control.nonces(nonce_digest,state)
            VALUES (%s,'SPENT')""", (nonce,))
    return claims["role"]


def revoke_nonce(conn, nonce):
    _guard_connection(conn)
    digest = _nonce_digest(nonce)
    with conn.transaction():
        _lock_state(conn)
        conn.execute("""INSERT INTO b2b_eval_ci_control.nonces(nonce_digest,state)
            VALUES (%s,'REVOKED')
            ON CONFLICT(nonce_digest) DO UPDATE SET state='REVOKED'""", (digest,))


def rotate_key(conn, *, old_key, new_key):
    """Retire the active key fingerprint; old tokens cannot be consumed."""
    _guard_connection(conn)
    old = _fingerprint(old_key)
    new = _fingerprint(new_key)
    if old == new:
        raise GatewayRejected("COORDINATOR_UNCHANGED_KEY")
    with conn.transaction():
        active = _lock_state(conn)
        if active != old:
            raise GatewayRejected("COORDINATOR_STALE_ROTATION")
        retired = conn.execute("""SELECT 1 FROM b2b_eval_ci_control.retired_keys
            WHERE key_sha256=%s""", (new,)).fetchone()
        if retired:
            raise GatewayRejected("COORDINATOR_RETIRED_KEY_REUSE")
        conn.execute("INSERT INTO b2b_eval_ci_control.retired_keys(key_sha256) VALUES (%s)", (old,))
        conn.execute("""UPDATE b2b_eval_ci_control.state
            SET active_key_sha256=%s WHERE singleton=1""", (new,))


def disable_authority(conn):
    _guard_connection(conn)
    with conn.transaction():
        row = conn.execute("""SELECT singleton FROM b2b_eval_ci_control.state
          WHERE singleton=1 FOR UPDATE""").fetchone()
        if not row:
            raise GatewayRejected("COORDINATOR_STATE_MISSING")
        conn.execute("UPDATE b2b_eval_ci_control.state SET disabled=true WHERE singleton=1")
