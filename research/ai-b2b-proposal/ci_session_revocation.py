"""CI-only session revocation and signing key replacement.

A single-process, in-memory fixture, not a production identity provider.
No shared storage, durable revocation, JWKS, OIDC, key custody, or deployment.
"""
import secrets
import hashlib
import threading

from ci_reviewer_read_gateway import GatewayRejected, read_assigned_document
from ci_signed_reviewer_session import issue_ci_token, verify_ci_token

_ROLES = frozenset(("b2b_eval_ci_reviewer_a", "b2b_eval_ci_reviewer_b"))


class CiSessionAuthority:
    """Explicitly fail closed when a session is revoked or its key retired.

    The lock ensures single-process replay decisions are atomic. It is not
    a substitute for shared transaction-safe replay/revocation storage.
    """

    def __init__(self, *, signing_key):
        self._lock = threading.Lock()
        self._key = self._validate_key(signing_key)
        self._retired_key_digests = set()
        self._spent = set()
        self._revoked = set()
        self._disabled = False

    @staticmethod
    def _validate_key(key):
        if not isinstance(key, bytes) or len(key) < 32:
            raise GatewayRejected("SIGNING_KEY_INVALID")
        return key

    def issue_fixture(self, *, role, now, nonce):
        """Synthetic CI fixture only; not an external issuance endpoint."""
        with self._lock:
            if self._disabled:
                raise GatewayRejected("AUTHORITY_DISABLED")
            if nonce in self._revoked or nonce in self._spent:
                raise GatewayRejected("SESSION_NONCE_BLOCKED")
            return issue_ci_token(role=role, now=now, nonce=nonce,
                                  signing_key=self._key)

    def revoke_nonce(self, nonce):
        if not isinstance(nonce, str) or len(nonce) < 16 or len(nonce) > 100:
            raise GatewayRejected("REVOCATION_NONCE_INVALID")
        with self._lock:
            self._revoked.add(nonce)

    def rotate_signing_key(self, new_key):
        new_key = self._validate_key(new_key)
        with self._lock:
            if secrets.compare_digest(new_key, self._key):
                raise GatewayRejected("ROTATION_KEY_UNCHANGED")
            digest = hashlib.sha256(new_key).digest()
            if digest in self._retired_key_digests:
                raise GatewayRejected('ROTATION_KEY_RETIRED')
            # Retire old signing key permanently for this authority lifetime.
            self._retired_key_digests.add(hashlib.sha256(self._key).digest())
            self._key = new_key

    def disable(self):
        with self._lock:
            self._disabled = True

    def read_once(self, token, *, now, connect_for_role, document_id):
        if not callable(connect_for_role):
            raise GatewayRejected("SESSION_CONFIG_INVALID")
        with self._lock:
            if self._disabled:
                raise GatewayRejected("AUTHORITY_DISABLED")
            claims = verify_ci_token(token, signing_key=self._key, now=now)
            nonce = claims["jti"]
            if nonce in self._revoked:
                raise GatewayRejected("SESSION_REVOKED")
            if nonce in self._spent:
                raise GatewayRejected("SESSION_REPLAY")
            self._spent.add(nonce)  # consume before accessing the DB
            role = claims["role"]
        if role not in _ROLES:
            raise GatewayRejected("SESSION_ROLE_INVALID")
        conn = connect_for_role(role)
        if conn is None:
            raise GatewayRejected("ROLE_CONNECTION_UNAVAILABLE")
        try:
            actual = conn.execute("SELECT current_database(), current_user").fetchone()
            if actual != ("proposal_eval_ci", role):
                raise GatewayRejected("SESSION_DATABASE_ROLE_MISMATCH")
            return read_assigned_document(conn, document_id=document_id)
        finally:
            conn.close()
