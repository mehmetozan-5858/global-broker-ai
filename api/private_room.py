from http.server import BaseHTTPRequestHandler
import json
import os
from urllib.parse import urlparse, parse_qs

from src.access_control import AccessRecord, private_view
from src.consent_records import ConsentEvent, current_consent
from src.session_security import SessionError, verify_session
from src.storage import StorageError, build_record_store


def _bearer(headers):
    value = headers.get("Authorization", "")
    if not value.startswith("Bearer "):
        return ""
    return value[7:].strip()


def _session_from_headers(headers):
    token = _bearer(headers)
    secret = os.environ.get("PRIVATE_ROOM_SESSION_SECRET", "")
    if not token or not secret:
        raise SessionError("authentication_required")
    return verify_session(token, secret)


def _runtime_store_token(headers):
    return (headers.get("x-vercel-oidc-token", "") or "").strip()


def _consent_events(record):
    raw_events = record.get("consent_events")
    if not isinstance(raw_events, list):
        return []
    events = []
    for raw in raw_events:
        if not isinstance(raw, dict):
            continue
        try:
            event = ConsentEvent(
                opportunity_id=str(raw.get("opportunity_id") or ""),
                party=str(raw.get("party") or ""),
                actor_id=str(raw.get("actor_id") or ""),
                action=str(raw.get("action") or ""),
                timestamp=str(raw.get("timestamp") or ""),
                purpose=str(raw.get("purpose") or "contact_introduction"),
                evidence_ref=str(raw.get("evidence_ref") or ""),
            ).validate()
        except ValueError:
            continue
        events.append(event)
    return events


def _build_access(record, opportunity_id):
    gates = record.get("access")
    if not isinstance(gates, dict):
        raise ValueError("server_record_invalid")
    events = _consent_events(record)
    return AccessRecord(
        authenticated=True,
        party_verified=bool(gates.get("party_verified")),
        buyer_consent=current_consent(events, opportunity_id, "buyer"),
        seller_consent=current_consent(events, opportunity_id, "seller"),
        terms_signed=bool(gates.get("terms_signed")),
        access_fee_required=bool(gates.get("access_fee_required")),
        access_paid=bool(gates.get("access_paid")),
    )


def _subject_authorized(record, session):
    """Fail closed if the server-side opportunity has no explicit subject allowlist."""
    allowed = record.get("allowed_subjects")
    subject = session.get("sub")
    return (
        isinstance(allowed, list)
        and bool(allowed)
        and isinstance(subject, str)
        and bool(subject.strip())
        and subject in allowed
    )


def _consent_command(session, payload):
    if not isinstance(payload, dict):
        raise ValueError("invalid_consent_request")
    opportunity_id = str(payload.get("opportunity_id") or "").strip()
    action = str(payload.get("action") or "").strip()
    actor_id = str(session.get("sub") or "").strip()
    if not opportunity_id or action not in {"grant", "revoke"} or not actor_id:
        raise ValueError("invalid_consent_request")
    return opportunity_id, actor_id, action


class handler(BaseHTTPRequestHandler):
    def _json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def _authenticated_session(self):
        try:
            return _session_from_headers(self.headers)
        except SessionError:
            self._json(401, {"status": "AUTHENTICATION_REQUIRED"})
            return None

    def do_GET(self):
        session = self._authenticated_session()
        if session is None:
            return

        query = parse_qs(urlparse(self.path).query)
        opportunity_id = (query.get("id") or [""])[0].strip()
        if not opportunity_id:
            self._json(404, {"status": "OPPORTUNITY_NOT_FOUND"})
            return

        try:
            store = build_record_store()
            runtime_token = _runtime_store_token(self.headers)
            record = store.get_opportunity_record(
                opportunity_id, bearer_token=runtime_token
            )
        except StorageError:
            self._json(503, {"status": "PRIVATE_ROOM_STORAGE_UNAVAILABLE"})
            return

        if not isinstance(record, dict):
            self._json(404, {"status": "OPPORTUNITY_NOT_FOUND"})
            return

        opportunity = record.get("opportunity")
        if not isinstance(opportunity, dict):
            self._json(500, {"status": "SERVER_RECORD_INVALID"})
            return

        if not _subject_authorized(record, session):
            self._json(403, {"status": "SESSION_NOT_AUTHORIZED_FOR_OPPORTUNITY"})
            return

        try:
            access = _build_access(record, opportunity_id)
        except ValueError:
            self._json(500, {"status": "SERVER_RECORD_INVALID"})
            return

        self._json(200, private_view(opportunity, access))

    def do_POST(self):
        session = self._authenticated_session()
        if session is None:
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"status": "INVALID_REQUEST"})
            return
        if content_length <= 0 or content_length > 4096:
            self._json(400, {"status": "INVALID_REQUEST"})
            return

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"status": "INVALID_JSON"})
            return

        try:
            opportunity_id, actor_id, action = _consent_command(session, payload)
        except ValueError:
            self._json(400, {"status": "INVALID_CONSENT_REQUEST"})
            return

        try:
            result = build_record_store().record_consent(
                opportunity_id,
                actor_id,
                action,
                bearer_token=_runtime_store_token(self.headers),
            )
        except StorageError as exc:
            if str(exc) == "consent_subject_not_authorized":
                self._json(403, {"status": "SUBJECT_NOT_AUTHORIZED"})
            elif str(exc) in {"invalid_consent_action", "invalid_consent_request"}:
                self._json(400, {"status": "INVALID_CONSENT_REQUEST"})
            else:
                self._json(503, {"status": "PRIVATE_ROOM_STORAGE_UNAVAILABLE"})
            return

        self._json(200, result)
