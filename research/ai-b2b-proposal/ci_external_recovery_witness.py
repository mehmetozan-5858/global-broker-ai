"""Research-only out-of-database recovery witness contract.

A signed witness + independently supplied minimum generation can detect a
stale restored PostgreSQL state. This is NOT a trusted external witness
service: signing keys, durable pins, access control, backups and atomicity
across DB and witness are NOT provided by this module.
"""
import base64
import hashlib
import hmac
import json

from ci_reviewer_read_gateway import GatewayRejected
from ci_pg_shared_session_gate import consume_once, check_external_recovery_floor

_AUD = "b2b-eval-recovery-ci-only"
_LIMIT = 2048


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _validate_key(key):
    if not isinstance(key, bytes) or len(key) < 32:
        raise GatewayRejected("WITNESS_KEY_INVALID")


def _validate_floor(value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise GatewayRejected("WITNESS_FLOOR_INVALID")


def issue_fixture_witness(generation, *, signing_key):
    """Synthetic CI issuer only; must never be exposed to request callers."""
    _validate_key(signing_key)
    _validate_floor(generation)
    payload = {"aud": _AUD, "generation": generation, "version": 1}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
    body = _b64(raw)
    signature = _b64(hmac.new(signing_key, body.encode("ascii"), hashlib.sha256).digest())
    return body + "." + signature


def verify_recovery_witness(witness, *, signing_key, trusted_min_generation):
    """Only a separately controlled trusted_min_generation prevents witness rollback.

    Signing proves only possession of the test HMAC key, not real-world
    authority, file immutability or correctness of the asserted generation.
    """
    _validate_key(signing_key)
    _validate_floor(trusted_min_generation)
    if not isinstance(witness, str) or len(witness) > _LIMIT or witness.count(".") != 1:
        raise GatewayRejected("WITNESS_INVALID")
    body, signature = witness.split(".")
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    if not body or not signature or any(c not in alphabet for c in body+signature):
        raise GatewayRejected("WITNESS_INVALID")
    expected = _b64(hmac.new(signing_key, body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        raise GatewayRejected("WITNESS_SIGNATURE_INVALID")
    try:
        payload = json.loads(base64.urlsafe_b64decode(body + "="*(-len(body) % 4)))
    except (UnicodeError, ValueError, TypeError) as exc:
        raise GatewayRejected("WITNESS_PAYLOAD_INVALID") from exc
    if not isinstance(payload, dict) or set(payload) != {"aud", "generation", "version"}:
        raise GatewayRejected("WITNESS_CLAIMS_INVALID")
    if payload["version"] != 1 or isinstance(payload["version"], bool) or payload["aud"] != _AUD:
        raise GatewayRejected("WITNESS_SCOPE_INVALID")
    generation = payload["generation"]
    _validate_floor(generation)
    if generation < trusted_min_generation:
        raise GatewayRejected("WITNESS_ROLLBACK_DETECTED")
    return generation


def check_with_signed_witness(conn, *, witness, witness_key, trusted_min_generation):
    """Refuse stale database before any eligible data-access decision."""
    minimum = verify_recovery_witness(witness, signing_key=witness_key,
                                      trusted_min_generation=trusted_min_generation)
    return check_external_recovery_floor(conn, trusted_min_generation=minimum)


def consume_with_signed_witness(conn, token, *, signing_key, now,
                                witness, witness_key, trusted_min_generation):
    """Require valid signed outside-DB floor before single-use token consume.

    Crucially, DB generation can advance without witness being updated when
    commit acknowledgement is lost. This fixture does not solve distributed
    DB+witness atomic commit; NOT production safe.
    """
    minimum = verify_recovery_witness(witness, signing_key=witness_key,
                                      trusted_min_generation=trusted_min_generation)
    return consume_once(conn, token, signing_key=signing_key, now=now,
                        trusted_min_generation=minimum)
