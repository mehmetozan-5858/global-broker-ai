"""Offline regression for the single-file printer-setting XLSX review gate."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import unittest

from scripts.review_ted_xlsx_formulas import validate_archive


class ScopedArchiveTests(unittest.TestCase):
    def make_archive(self, folder, extras):
        path = Path(folder) / "sample.xlsx"
        with ZipFile(path, "w") as z:
            z.writestr("[Content_Types].xml", b"x")
            z.writestr("xl/workbook.xml", b"x")
            for name in extras:
                z.writestr(name, b"not-executed")
        return path

    def test_default_rejects_printer_settings_binary(self):
        with TemporaryDirectory() as tmp:
            path = self.make_archive(tmp, ["xl/printerSettings/printerSettings1.bin"])
            with self.assertRaisesRegex(ValueError, "forbidden"):
                validate_archive(path)

    def test_scoped_mode_allows_only_one_printer_settings_binary(self):
        with TemporaryDirectory() as tmp:
            path = self.make_archive(tmp, ["xl/printerSettings/printerSettings1.bin"])
            validate_archive(path, allow_printer_settings=True)

    def test_scoped_mode_rejects_unexpected_binary(self):
        with TemporaryDirectory() as tmp:
            path = self.make_archive(tmp, ["xl/embeddings/oleObject1.bin"])
            with self.assertRaises(ValueError):
                validate_archive(path, allow_printer_settings=True)

    def test_scoped_mode_rejects_extra_binary(self):
        with TemporaryDirectory() as tmp:
            path = self.make_archive(tmp, [
                "xl/printerSettings/printerSettings1.bin",
                "xl/printerSettings/printerSettings2.bin",
            ])
            with self.assertRaises(ValueError):
                validate_archive(path, allow_printer_settings=True)


if __name__ == "__main__":
    unittest.main()
