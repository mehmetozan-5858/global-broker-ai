from http.server import BaseHTTPRequestHandler
import json
import os
from urllib.parse import urlparse, parse_qs

from src.access_control import AccessRecord, private_view
from src.consent_records import ConsentEvent, current_consent
from src.session_security import SessionError, verify_session


def _load_records():
    raw = os.environ.get("PRIVATE_ROOM_RECORDS_JSON", "{}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


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

    def do_GET(self):
        try:
            session = _session_from_headers(self.headers)
        except SessionError:
            self._json(401, {"status": "AUTHENTICATION_REQUIRED"})
            return

        query = parse_qs(urlparse(self.path).query)
        opportunity_id = (query.get("id") or [""])[0].strip()
        records = _load_records()
        record = records.get(opportunity_id)
        if not opportunity_id or not isinstance(record, dict):
            self._json(404, {"status": "OPPORTUNITY_NOT_FOUND"})
            return

        opportunity = record.get("opportunity")
        if not isinstance(opportunity, dict):
            self._json(500, {"status": "SERVER_RECORD_INVALID"})
            return

        allowed_subjects = record.get("allowed_subjects")
        if isinstance(allowed_subjects, list) and allowed_subjects:
            if session.get("sub") not in allowed_subjects:
                self._json(403, {"status": "SESSION_NOT_AUTHORIZED_FOR_OPPORTUNITY"})
                return

        try:
            access = _build_access(record, opportunity_id)
        except ValueError:
            self._json(500, {"status": "SERVER_RECORD_INVALID"})
            return

        self._json(200, private_view(opportunity, access))
