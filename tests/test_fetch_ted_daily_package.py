"""Offline tests for bounded TED OJ S archive downloader."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

p = Path(__file__).resolve().parents[1] / "scripts" / "fetch_ted_daily_package.py"
spec = importlib.util.spec_from_file_location("fetch_ted_daily_package", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class Response:
    status = 200
    url = "https://ted.europa.eu/packages/notice/daily/202600216"

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return self.payload[:limit]


class DailyDownloadTests(unittest.TestCase):
    def test_official_url_only(self):
        self.assertTrue(mod.official("https://ted.europa.eu/packages/notice/daily/202600216"))
        for url in ("http://ted.europa.eu/a", "https://ted.europa.eu.evil.test/a",
                    "https://user@ted.europa.eu/a", "https://ted.europa.eu:bad/a"):
            self.assertFalse(mod.official(url))

    def test_download_records_digest_without_accepting_notice(self):
        payload = bytes.fromhex("504b0304") + b"test"
        with tempfile.TemporaryDirectory() as tmp, patch.object(mod, "build_opener") as builder:
            builder.return_value.open.return_value = Response(payload)
            path = Path(tmp) / "daily.zip"
            result = mod.fetch(2026, 216, path)
            self.assertEqual(path.read_bytes(), payload)
            self.assertFalse(result["notice_verified"])
            self.assertFalse(result["commercial_approval"])

    def test_html_challenge_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(mod, "build_opener") as builder:
            builder.return_value.open.return_value = Response(b"<html>please wait</html>")
            with self.assertRaisesRegex(ValueError, "unexpected package signature"):
                mod.fetch(2026, 216, Path(tmp) / "daily.zip")

    def test_invalid_issue_rejected_before_network(self):
        with self.assertRaises(ValueError):
            mod.fetch(2026, 999, Path("/tmp/not-used"))


if __name__ == "__main__":
    unittest.main()
