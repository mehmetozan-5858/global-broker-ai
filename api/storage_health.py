from http.server import BaseHTTPRequestHandler
import json

from src.storage import StorageError, build_record_store


class handler(BaseHTTPRequestHandler):
    def _json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        oidc = (self.headers.get("x-vercel-oidc-token", "") or "").strip()
        if not oidc:
            self._json(503, {"status": "OIDC_MISSING"})
            return
        try:
            record = build_record_store().get_opportunity_record(
                "smoke-private-room-001", bearer_token=oidc
            )
        except StorageError as exc:
            self._json(503, {"status": "STORE_UNAVAILABLE", "reason": str(exc)})
            return
        self._json(200, {
            "status": "OK" if isinstance(record, dict) else "RECORD_NOT_FOUND",
            "record_found": isinstance(record, dict),
        })
