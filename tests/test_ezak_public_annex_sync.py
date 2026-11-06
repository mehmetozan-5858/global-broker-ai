"""Offline tests for official-host E-ZAK annex discovery."""
import importlib.util
from pathlib import Path
import unittest

source = Path(__file__).resolve().parents[1] / "scripts" / "ezak_public_annex_sync.py"
spec = importlib.util.spec_from_file_location("ezak_public_annex_sync", source)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class EzakDiscoveryTests(unittest.TestCase):
    def test_official_host_only(self):
        self.assertTrue(mod.official_url(mod.BASE))
        for url in ("http://zakazky.krajbezkorupce.cz/file.pdf",
                    "https://zakazky.krajbezkorupce.cz.evil.test/file.pdf",
                    "https://evil.test/file.pdf",
                    "https://user@zakazky.krajbezkorupce.cz/file.pdf"):
            with self.subTest(url=url):
                self.assertFalse(mod.official_url(url))

    def test_relative_documents_and_duplicates(self):
        html = b'<html><a href="/document_download_123">PDF</a><a href="/document_download_123">again</a><a href="https://evil.test/file.pdf">bad</a><a href="/docs/annex.xlsx">xlsx</a></html>'
        self.assertEqual(mod.discover(html), [
            "https://zakazky.krajbezkorupce.cz/docs/annex.xlsx",
            "https://zakazky.krajbezkorupce.cz/document_download_123",
        ])

    def test_navigation_links_are_not_treated_as_annexes(self):
        html = b'<html><a href="/documentation/help">help</a><a href="/file_manager">files</a><a href="/contract_display_47078.html">notice</a></html>'
        self.assertEqual(mod.discover(html), [])

    def test_invalid_port_is_rejected(self):
        self.assertFalse(mod.official_url("https://zakazky.krajbezkorupce.cz:bad/doc.pdf"))

    def test_empty_or_js_only_index_fails_to_discover(self):
        self.assertEqual(mod.discover(b"<html><script>loadDocuments()</script></html>"), [])

    def test_download_limits_are_explicit(self):
        self.assertLessEqual(mod.MAX_INDEX, 2_000_000)
        self.assertLessEqual(mod.MAX_FILE, 12_000_000)


if __name__ == "__main__":
    unittest.main()
