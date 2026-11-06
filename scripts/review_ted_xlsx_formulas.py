"""Offline inventory of a specific TED annex XLSX; never evaluates formulas.

Usage (local/private, with openpyxl installed):
  python scripts/review_ted_xlsx_formulas.py /private/path/annex.xlsx

The command fails closed on hash/count mismatch and prints only aggregate counts.
It never downloads documents, executes macros, or approves procurement.
"""
import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_SHA256 = "41144156ef49a411de75c423f3e460732bc1bc111da326d76801cb798de20d45"
EXPECTED_FORMULAS = 13
MAX_BYTES = 2_000_000


def inspect(path: Path):
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("Missing or oversized workbook")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError("Workbook SHA-256 mismatch: not the reviewed source")
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
                "formulas_evaluated": False, "technical_approval": False}
    finally:
        formulas.close()
        cached.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.workbook), sort_keys=True))
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(2, f"XLSX review blocked: {type(exc).__name__}: {exc}\n")
