"""Signed, expiring sessions for the Global Broker private data room.

The token format is intentionally small and dependency-free: base64url(JSON)
plus an HMAC-SHA256 signature.  Tokens are accepted only when the signature is
valid, the subject is present and the expiry is in the future.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


class SessionError(ValueError):
    pass


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def issue_session(subject: str, secret: str, *, ttl_seconds: int = 1800,
                  now: int | None = None, role: str = "party") -> str:
    subject = subject.strip()
    if not subject:
        raise SessionError("subject_required")
    if len(secret) < 32:
        raise SessionError("secret_too_short")
    if ttl_seconds <= 0 or ttl_seconds > 86400:
        raise SessionError("invalid_ttl")
    issued = int(time.time() if now is None else now)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": issued,
        "exp": issued + ttl_seconds,
    }
    encoded = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).digest()
    return encoded + "." + _b64encode(signature)


def verify_session(token: str, secret: str, *, now: int | None = None) -> dict[str, Any]:
    if len(secret) < 32:
        raise SessionError("secret_too_short")
    try:
        encoded, supplied_sig = token.split(".", 1)
        expected = hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64decode(supplied_sig), expected):
            raise SessionError("invalid_signature")
        payload = json.loads(_b64decode(encoded).decode("utf-8"))
    except SessionError:
        raise
    except Exception as exc:
        raise SessionError("invalid_token") from exc

    if not isinstance(payload, dict) or not str(payload.get("sub") or "").strip():
        raise SessionError("invalid_subject")
    current = int(time.time() if now is None else now)
    try:
        expires = int(payload["exp"])
        issued = int(payload["iat"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SessionError("invalid_timestamps") from exc
    if issued > current + 60:
        raise SessionError("issued_in_future")
    if expires <= current:
        raise SessionError("session_expired")
    if expires - issued > 86400:
        raise SessionError("invalid_lifetime")
    return payload
