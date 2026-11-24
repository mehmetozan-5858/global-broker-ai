"""CI-only signed session-to-PostgreSQL reviewer binding.

Research fixture, NOT production authentication: no OIDC, trusted third-party
identity provider, key rotation or shared atomic replay store. Keys must
come from a separate issuer and never from request data.
"""
import base64
import hashlib
import hmac
import json
import re
import time
from ci_reviewer_read_gateway import GatewayRejected, read_assigned_document

_ROLES = frozenset(("b2b_eval_ci_reviewer_a", "b2b_eval_ci_reviewer_b"))
_AUD = "b2b-eval-ci-only"
_JTI = re.compile(r"^[a-zA-Z0-9_-]{16,100}$")
_MAX_LIFETIME = 120


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def issue_ci_token(*, role, now, nonce, signing_key):
    """Only for synthetic local fixtures; never expose an issuance endpoint."""
    if role not in _ROLES or not isinstance(now, int) or not isinstance(nonce, str) or not _JTI.fullmatch(nonce):
        raise GatewayRejected("ISSUER_FIXTURE_INVALID")
    if not isinstance(signing_key, bytes) or len(signing_key) < 32:
        raise GatewayRejected("SIGNING_KEY_INVALID")
    payload = {"aud": _AUD, "role": role, "iat": now, "exp": now + 60,
               "jti": nonce}
    body = _b64(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    sig = _b64(hmac.new(signing_key, body.encode("ascii"), hashlib.sha256).digest())
    return body + "." + sig


def verify_ci_token(token, *, signing_key, now=None):
    """Return a verified principal, never trust role from a request separately."""
    if not isinstance(signing_key, bytes) or len(signing_key) < 32:
        raise GatewayRejected("SIGNING_KEY_INVALID")
    if not isinstance(token, str) or len(token) > 1024 or token.count(".") != 1:
        raise GatewayRejected("TOKEN_INVALID")
    body, sig = token.split(".")
    if not body or not sig or any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for ch in (body + sig)):
        raise GatewayRejected("TOKEN_INVALID")
    computed = _b64(hmac.new(signing_key, body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, computed):
        raise GatewayRejected("SIGNATURE_INVALID")
    try:
        payload_bytes = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
        payload = json.loads(payload_bytes)
    except (ValueError, UnicodeError, TypeError) as exc:
        raise GatewayRejected("TOKEN_PAYLOAD_INVALID") from exc
    if not isinstance(payload, dict) or set(payload) != {"aud", "role", "iat", "exp", "jti"}:
        raise GatewayRejected("TOKEN_CLAIMS_INVALID")
    if payload["aud"] != _AUD or payload["role"] not in _ROLES:
        raise GatewayRejected("TOKEN_SCOPE_INVALID")
    if not isinstance(payload["iat"], int) or isinstance(payload["iat"], bool) or not isinstance(payload["exp"], int) or isinstance(payload["exp"], bool):
        raise GatewayRejected("TOKEN_TIME_INVALID")
    if not isinstance(payload["jti"], str) or not _JTI.fullmatch(payload["jti"]):
        raise GatewayRejected("TOKEN_NONCE_INVALID")
    current = int(time.time()) if now is None else now
    if not isinstance(current, int) or isinstance(current, bool) or payload["iat"] > current or payload["exp"] <= current:
        raise GatewayRejected("TOKEN_EXPIRED_OR_NOT_YET_VALID")
    if not 0 < payload["exp"] - payload["iat"] <= _MAX_LIFETIME:
        raise GatewayRejected("TOKEN_LIFETIME_INVALID")
    return payload


def read_with_verified_ci_session(token, *, signing_key, now, replay_registry, connect_for_role, document_id):
    """Verify before opening a DB connection, then require exact DB role match.

    This test-only in-memory registry is NOT safe across processes or workers.
    """
    if not isinstance(replay_registry, set) or not callable(connect_for_role):
        raise GatewayRejected("SESSION_CONFIG_INVALID")
    principal = verify_ci_token(token, signing_key=signing_key, now=now)
    nonce = principal["jti"]
    if nonce in replay_registry:
        raise GatewayRejected("SESSION_REPLAY")
    replay_registry.add(nonce)  # burn nonce even when database access fails
    conn = connect_for_role(principal["role"])
    if conn is None:
        raise GatewayRejected("ROLE_CONNECTION_UNAVAILABLE")
    try:
        actual = conn.execute("SELECT current_database(), current_user").fetchone()
        if actual != ("proposal_eval_ci", principal["role"]):
            raise GatewayRejected("SESSION_DATABASE_ROLE_MISMATCH")
        return read_assigned_document(conn, document_id=document_id)
    finally:
        conn.close()
