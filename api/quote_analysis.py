"""Bearer-only private preview; SQL enforces the current admin role and AAL2."""
from http.server import BaseHTTPRequestHandler
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from api.admin_opportunities import SUPABASE_URL, SUPABASE_KEY, _bearer
from src.quote_review_analysis import analyze


def preview(token, opportunity_id):
    request = Request(SUPABASE_URL + '/rest/v1/rpc/gb_quote_analysis_context',
        data=json.dumps({'p_opportunity_id': opportunity_id}).encode(), method='POST',
        headers={'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=15) as response:
            return 200, analyze(json.loads(response.read(4000000)))
    except HTTPError as error:
        return (error.code if error.code in (401, 403) else 503), {'status': 'ANALYSIS_UNAVAILABLE'}
    except (URLError, TimeoutError, ValueError, KeyError, TypeError):
        return 503, {'status': 'ANALYSIS_UNAVAILABLE'}


class handler(BaseHTTPRequestHandler):
    def _analysis_json(self, status, payload):
        raw = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        for key, value in {'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'private, no-store', 'Vary': 'Authorization', 'Referrer-Policy': 'no-referrer', 'X-Content-Type-Options': 'nosniff'}.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        token = _bearer(self.headers)
        if not token:
            return self._analysis_json(401, {'status': 'AUTHENTICATION_REQUIRED'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 1024:
                raise ValueError('size')
            body = json.loads(self.rfile.read(length))
            identity = body.get('opportunity_id')
            if set(body) != {'opportunity_id'} or not isinstance(identity, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,200}', identity):
                raise ValueError('identity')
        except (ValueError, TypeError, AttributeError):
            return self._analysis_json(400, {'status': 'INVALID_REQUEST'})
        status, result = preview(token, identity)
        return self._analysis_json(status, result)
