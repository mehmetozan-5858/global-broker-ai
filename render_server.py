from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import mimetypes
import os

from api.opportunities import handler as OpportunitiesHandler
from api.introduction import handler as IntroductionHandler
from api.contact_unlock import handler as ContactUnlockHandler
from api.private_room import handler as PrivateRoomHandler

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"

ROUTES = {
    "/": "website-mobile.html",
    "/website.html": "website-mobile.html",
    "/customer": "customer-shell.html",
    "/customer.html": "customer-shell.html",
    "/app": "app-shell.html",
    "/account": "account.html",
    "/security": "security.html",
    "/pricing": "pricing.html",
    "/privacy": "privacy.html",
    "/terms": "terms.html",
    "/refund": "refund.html",
}


class Handler(OpportunitiesHandler, PrivateRoomHandler, IntroductionHandler, ContactUnlockHandler):
    server_version = "GlobalBrokerRender/1.0"

    def _serve_file(self, path: Path):
        try:
            resolved = path.resolve()
            if WEB.resolve() not in resolved.parents and resolved != WEB.resolve():
                self.send_error(403)
                return
            data = resolved.read_bytes()
        except FileNotFoundError:
            self.send_error(404)
            return
        ctype = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.end_headers()
        self.wfile.write(data)

    def _serve_static(self):
        parsed = urlparse(self.path)
        route_path = parsed.path
        if route_path in ROUTES:
            self._serve_file(WEB / ROUTES[route_path])
            return True
        if route_path.startswith("/web/"):
            self._serve_file(ROOT / route_path.lstrip("/"))
            return True
        if route_path.startswith("/data/"):
            self._serve_file(ROOT / route_path.lstrip("/"))
            return True
        candidate = WEB / route_path.lstrip("/")
        if candidate.is_file():
            self._serve_file(candidate)
            return True
        return False

    def do_GET(self):
        path = urlparse(self.path).path
        if path in {"/api/opportunities", "/data/latest-opportunities.json"}:
            return OpportunitiesHandler.do_GET(self)
        if path == "/api/private_room":
            return PrivateRoomHandler.do_GET(self)
        if self._serve_static():
            return
        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/introduction":
            return IntroductionHandler.do_POST(self)
        if path == "/api/contact_unlock":
            return ContactUnlockHandler.do_POST(self)
        if path == "/api/private_room":
            return PrivateRoomHandler.do_POST(self)
        self.send_error(404)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Global Broker listening on {port}", flush=True)
    server.serve_forever()
