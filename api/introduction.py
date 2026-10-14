from http.server import BaseHTTPRequestHandler
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.introduction_readiness import introduction_preflight

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://yhzdqrqzjruduohypvqf.supabase.co").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_fFtN0JmDBp8TP01lKJhTFQ_sx6mkt-w")


def _bearer(headers):
    value = headers.get("Authorization", "")
    return value[7:].strip() if value.startswith("Bearer ") else ""


def _post_json(url, token, payload, timeout=12):
    req = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8")
            body = json.loads(raw) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            body = {}
        return exc.code, body
    except (URLError, TimeoutError, json.JSONDecodeError):
        return 503, {}


def _rpc(token, opportunity_id):
    return _post_json(
        SUPABASE_URL + "/rest/v1/rpc/request_introduction",
        token,
        {"p_opportunity_id": opportunity_id},
    )


def _verify(token, request_id):
    if not request_id:
        return 400, {}
    return _post_json(
        SUPABASE_URL + "/functions/v1/broker-introduction-verify",
        token,
        {"request_id": request_id},
        timeout=15,
    )


def _error_code(body):
    message = str((body or {}).get("message") or (body or {}).get("details") or "").lower()
    checks = (
        ("authentication_required", "AUTHENTICATION_REQUIRED", 401),
        ("active_plan_required", "ACTIVE_PLAN_REQUIRED", 403),
        ("invalid_opportunity_id", "INVALID_OPPORTUNITY_ID", 400),
        ("opportunity_not_found", "OPPORTUNITY_NOT_FOUND", 404),
        ("sector_not_in_plan", "SECTOR_NOT_IN_PLAN", 403),
        ("country_not_selected", "COUNTRY_NOT_SELECTED", 403),
        ("introduction_credit_required", "INTRODUCTION_CREDIT_REQUIRED", 402),
    )
    for needle, code, status in checks:
        if needle in message:
            return status, code
    return 403, "INTRODUCTION_REQUEST_DENIED"


class handler(BaseHTTPRequestHandler):
    def _json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "private, no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Vary", "Authorization")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        token = _bearer(self.headers)
        if not token:
            self._json(401, {"status": "AUTHENTICATION_REQUIRED"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > 2048:
            self._json(400, {"status": "INVALID_REQUEST"})
            return

        try:
            request_body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"status": "INVALID_JSON"})
            return

        opportunity_id = str((request_body or {}).get("opportunity_id") or "").strip()
        if len(opportunity_id) < 8 or len(opportunity_id) > 200:
            self._json(400, {"status": "INVALID_OPPORTUNITY_ID"})
            return

        # Fail closed before the RPC can reserve or debit a contact credit.
        preflight_status, preflight_code = introduction_preflight(opportunity_id)
        if preflight_status != 200:
            self._json(preflight_status, {"status": preflight_code})
            return

        rpc_status, result = _rpc(token, opportunity_id)
        if rpc_status >= 400 or not isinstance(result, dict) or not result.get("ok"):
            status, code = _error_code(result)
            if rpc_status == 503:
                status, code = 503, "INTRODUCTION_SERVICE_UNAVAILABLE"
            self._json(status, {"status": code})
            return

        request_id = result.get("request_id")
        request_status = result.get("status")
        credit_refunded = False
        verify_status, verified = _verify(token, request_id)
        if verify_status < 400 and isinstance(verified, dict) and verified.get("status") == "OK":
            request_status = verified.get("request_status") or request_status
            credit_refunded = bool(verified.get("credit_refunded"))

        self._json(200, {
            "status": "INTRODUCTION_REQUESTED",
            "opportunity_id": opportunity_id,
            "request_id": request_id,
            "request_status": request_status,
            "already_requested": bool(result.get("already_requested")),
            "credits_remaining": result.get("credits_remaining"),
            "credit_refunded": credit_refunded,
        })
