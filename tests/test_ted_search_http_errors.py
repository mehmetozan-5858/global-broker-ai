"""TED API errors must not leak response bodies or hide rate limiting."""
import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from src import broker


class TEDSearchErrorTests(unittest.TestCase):
    def test_rate_limit_has_safe_actionable_error(self):
        error = HTTPError(broker.TED_URL, 429, "Too Many Requests", {}, io.BytesIO(b"private-api-response-token"))
        with patch.object(broker.urllib.request, "urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "TED_HTTP_RATE_LIMITED_429") as ctx:
                broker.ted_search("publication-date >= 20261001", 1)
        self.assertNotIn("private-api-response-token", str(ctx.exception))

    def test_other_http_error_has_only_status_code(self):
        error = HTTPError(broker.TED_URL, 503, "Service Unavailable", {}, io.BytesIO(b"sensitive server body"))
        with patch.object(broker.urllib.request, "urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "TED_HTTP_STATUS_503") as ctx:
                broker.ted_search("publication-date >= 20261001", 1)
        self.assertNotIn("sensitive server body", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
