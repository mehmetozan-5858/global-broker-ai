from http.server import BaseHTTPRequestHandler
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://yhzdqrqzjruduohypvqf.supabase.co").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_fFtN0JmDBp8TP01lKJhTFQ_sx6mkt-w")


def _bearer(headers):
    value = headers.get("Authorization", "")
    return value[7:].strip() if value.startswith("Bearer ") else ""


def _supabase_json(path, token):
    req = Request(
        SUPABASE_URL + path,
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def _private_feed(token):
    req = Request(
        SUPABASE_URL + '/rest/v1/rpc/gb_admin_opportunity_feed',
        data=b'{"p_limit":500}',
        headers={'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + token,
                 'Accept':'application/json', 'Content-Type':'application/json'},
        method='POST',
    )
    try:
        with urlopen(req, timeout=12) as response:
            result=json.loads(response.read().decode('utf-8'))
        if not isinstance(result,dict) or not isinstance(result.get('opportunities'),list):
            return None
        return result
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def _data_path():
    here = Path(__file__).resolve()
    for p in [
        here.parent.parent / "data" / "latest-opportunities.json",
        Path.cwd() / "data" / "latest-opportunities.json",
        Path("/var/task/data/latest-opportunities.json"),
    ]:
        if p.exists():
            return p
    return None


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

    def do_GET(self):
        token = _bearer(self.headers)
        if not token:
            self._json(401, {"status": "AUTHENTICATION_REQUIRED"})
            return

        user = _supabase_json("/auth/v1/user", token)
        if not isinstance(user, dict) or not user.get("id"):
            self._json(401, {"status": "INVALID_SESSION"})
            return

        uid = user["id"]
        roles = _supabase_json(
            "/rest/v1/user_roles?select=role&user_id=eq.%s" % uid,
            token,
        )
        if not isinstance(roles, list) or not any(
            isinstance(row, dict) and row.get("role") == "admin" for row in roles
        ):
            self._json(403, {"status": "ADMIN_AAL2_REQUIRED"})
            return

        full = _private_feed(token)
        if full is None:
            self._json(503, {"status": "PRIVATE_OPPORTUNITY_FEED_UNAVAILABLE"})
            return

        path = _data_path()
        data = {}
        try:
            if path:
                data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}

        # Use private database rows; the masked file supplies aggregate telemetry only.
        source_rows = full['opportunities']

        rows = []
        for row in source_rows:
            if not isinstance(row, dict):
                continue
            review = row.get("export_goods_review") or {}
            if review and review.get("status") not in (None, "", "goods_candidate"):
                continue
            rows.append(row)
            if len(rows) >= 500:
                break

        payload = dict(data) if isinstance(data, dict) else {}
        payload["mode"] = "admin_authenticated_private_feed"
        payload["opportunities"] = rows
        payload["count"] = len(rows)
        self._json(200, payload)
