from http.server import BaseHTTPRequestHandler
import json
import os
from urllib.parse import urlparse, parse_qs

from src.access_control import AccessRecord, private_view


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


class handler(BaseHTTPRequestHandler):
    def _json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        token = _bearer(self.headers)
        expected = os.environ.get("PRIVATE_ROOM_TOKEN", "").strip()
        if not expected or token != expected:
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
        gates = record.get("access")
        if not isinstance(opportunity, dict) or not isinstance(gates, dict):
            self._json(500, {"status": "SERVER_RECORD_INVALID"})
            return

        access = AccessRecord(
            authenticated=True,
            party_verified=bool(gates.get("party_verified")),
            buyer_consent=bool(gates.get("buyer_consent")),
            seller_consent=bool(gates.get("seller_consent")),
            terms_signed=bool(gates.get("terms_signed")),
            access_fee_required=bool(gates.get("access_fee_required")),
            access_paid=bool(gates.get("access_paid")),
        )
        self._json(200, private_view(opportunity, access))
