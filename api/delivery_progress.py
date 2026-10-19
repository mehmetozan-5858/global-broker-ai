"""Public, read-only fixed-roadmap progress; no account or opportunity access."""
from http.server import BaseHTTPRequestHandler
import json
from pathlib import Path

from src.delivery_progress import public_summary

LEDGER = Path(__file__).resolve().parents[1] / 'docs' / 'delivery-progress.json'


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            payload = public_summary(json.loads(LEDGER.read_text(encoding='utf-8')))
            status = 200
        except (OSError, ValueError, TypeError, KeyError):
            status, payload = 503, {'error': 'progress_unavailable'}
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)
