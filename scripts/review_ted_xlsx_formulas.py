"""Offline, fail-closed inventory of TED 702997-2026 XLSX (no formula execution).

Usage: python scripts/review_ted_xlsx_formulas.py /private/annex.xlsx
Only aggregate counts are printed; never upload private annex contents to GitHub.
"""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import BadZipFile, ZipFile

EXPECTED_SHA256 = "41144156ef49a411de75c423f3e460732bc1bc111da326d76801cb798de20d45"
EXPECTED_FORMULAS = 13
MAX_BYTES = 2_000_000
MAX_UNCOMPRESSED = 25_000_000
MAX_ENTRIES = 300


def validate_archive(path: Path, *, allow_printer_settings: bool = False):
    """Reject macros, external links, oversized expansion and suspicious ZIP entries."""
    with ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) > MAX_ENTRIES:
            raise ValueError("Workbook ZIP entry limit exceeded")
        if sum(item.file_size for item in members) > MAX_UNCOMPRESSED:
            raise ValueError("Workbook ZIP expansion limit exceeded")
        names = [item.filename.lower() for item in members]
        if any(
            name.startswith("/") or "\\" in name or ".." in name.split("/")
            or name.startswith("xl/externallinks/")
            or "vbaproject" in name
            or name.endswith(".exe")
            or (name.endswith(".bin") and not (
                allow_printer_settings and name.startswith("xl/printersettings/")
                and name.count("/") == 2
            ))
            for name in names
        ):
            raise ValueError("Workbook contains forbidden archive member")
        if allow_printer_settings and sum(n.endswith(".bin") for n in names) != 1:
            raise ValueError("Expected exactly one scoped printer settings binary member")
        if "[content_types].xml" not in names or "xl/workbook.xml" not in names:
            raise ValueError("Workbook required OOXML members missing")


def inspect(path: Path, *, allow_printer_settings: bool = False):
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("Missing or oversized workbook")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError("Workbook SHA-256 mismatch: not the reviewed source")
    validate_archive(path, allow_printer_settings=allow_printer_settings)
    from openpyxl import load_workbook

    formulas = load_workbook(path, read_only=True, data_only=False, keep_links=False)
    cached = load_workbook(path, read_only=True, data_only=True, keep_links=False)
    try:
        count = 0
        cached_count = 0
        for sheet in formulas:
            values = cached[sheet.title]
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.data_type == "f":
                        count += 1
                        if values[cell.coordinate].value is not None:
                            cached_count += 1
        if count != EXPECTED_FORMULAS:
            raise ValueError("Formula count mismatch: human review required")
        return {"sha256_match": True, "formula_count": count,
                "cached_result_count": cached_count,
                "formulas_evaluated": False, "technical_approval": False,
                "printer_settings_scoped_review": allow_printer_settings}
    finally:
        formulas.close()
        cached.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.workbook), sort_keys=True))
    except (ValueError, OSError, ImportError, BadZipFile) as exc:
        parser.exit(2, f"XLSX review blocked: {type(exc).__name__}: {exc}\n")
