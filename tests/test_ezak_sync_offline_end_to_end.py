"""Offline end-to-end E-ZAK sync regression, without network access."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "scripts" / "ezak_public_annex_sync.py"
spec = importlib.util.spec_from_file_location("ezak_public_annex_sync", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class EzakSyncOfflineTests(unittest.TestCase):
    def test_official_document_is_hashed_and_not_approved(self):
        html = b'<html><a href="/docs/annex.pdf">document</a></html>'
        pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"
        def fake_fetch(url, limit):
            if url == mod.BASE:
                return html, "text/html", url
            if url == "https://zakazky.krajbezkorupce.cz/docs/annex.pdf":
                return pdf, "application/pdf", url
            raise AssertionError("unexpected URL")
        with tempfile.TemporaryDirectory() as tmp, patch.object(mod, "get_bounded", side_effect=fake_fetch):
            result = mod.sync(Path(tmp))
            self.assertEqual(len(result["records"]), 1)
            self.assertFalse(result["records"][0]["accepted"])
            self.assertFalse(result["commercial_approval"])
            self.assertFalse(result["complete_annex_set_verified"])
            self.assertEqual(len(list(Path(tmp).glob("annex-*"))), 1)
            self.assertEqual(json.loads((Path(tmp) / "manifest.json").read_text())["records"][0]["kind"], "pdf")

    def test_challenge_html_cannot_be_stored_as_document(self):
        html = b'<html><a href="/docs/annex.pdf">document</a></html>'
        def fake_fetch(url, limit):
            if url == mod.BASE:
                return html, "text/html", url
            return b"<!doctype html><html>Challenge</html>", "text/html", url
        with tempfile.TemporaryDirectory() as tmp, patch.object(mod, "get_bounded", side_effect=fake_fetch):
            with self.assertRaisesRegex(ValueError, "Incomplete annex acquisition"):
                mod.sync(Path(tmp))
            manifest = json.loads((Path(tmp) / "manifest.json").read_text())
            self.assertEqual(manifest["records"][0]["error"], "ValueError")
            self.assertFalse(list(Path(tmp).glob("annex-*")))

    def test_empty_index_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(mod, "get_bounded", return_value=(b"<html></html>", "text/html", mod.BASE)):
            with self.assertRaisesRegex(ValueError, "No public annex links"):
                mod.sync(Path(tmp))


if __name__ == "__main__":
    unittest.main()
