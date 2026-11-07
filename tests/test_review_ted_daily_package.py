"""Offline TED daily package inspection tests; no live calls."""
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile

p = Path(__file__).resolve().parents[1] / "scripts" / "review_ted_daily_package.py"
spec = importlib.util.spec_from_file_location("review_ted_daily_package", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class DailyPackageTests(unittest.TestCase):
    def test_exact_notice_xml_in_tar(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily.tar.gz"
            data = b'<Notice><ID>718662-2026</ID></Notice>'
            with tarfile.open(path, "w:gz") as archive:
                info = tarfile.TarInfo("718662_2026.xml")
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            result = mod.inspect(path, "718662-2026")
            self.assertTrue(result["xml_parsed"])
            self.assertFalse(result["source_completeness_verified"])
            self.assertFalse(result["commercial_approval"])

    def test_eforms_zero_padded_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("00718662_2026.xml", "<Notice><ID>718662-2026</ID></Notice>")
            self.assertTrue(mod.inspect(path, "718662-2026")["xml_parsed"])

    def test_incidental_publication_text_does_not_verify_notice_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("718662_2026.xml",
                    "<Notice><ID>718664-2026</ID><Description>718662-2026</Description></Notice>")
            with self.assertRaisesRegex(ValueError, "structured XML"):
                mod.inspect(path, "718662-2026")

    def test_namespaced_notice_id_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("00718662_2026.xml",
                    '<Notice xmlns="urn:example"><ID>718662-2026</ID></Notice>')
            self.assertTrue(mod.inspect(path, "718662-2026")["notice_identity_verified"])

    def test_unrelated_notice_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("718664_2026.xml", "<Notice/>")
            with self.assertRaisesRegex(ValueError, "missing"):
                mod.inspect(path, "718662-2026")

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("../718662_2026.xml", "<Notice/>")
            with self.assertRaisesRegex(ValueError, "unsafe"):
                mod.inspect(path, "718662-2026")

    def test_doctype_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("718662_2026.xml", '<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x/>')
            with self.assertRaisesRegex(ValueError, "DTD"):
                mod.inspect(path, "718662-2026")


if __name__ == "__main__":
    unittest.main()
