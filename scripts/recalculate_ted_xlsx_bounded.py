"""Independent read-only arithmetic check of exact SHA-pinned TED 702997 XLSX.
Only cell references, addition, and SUM(range) are supported. No eval, macros,
external links, network, formula printing, or approval writes.
"""
from decimal import Decimal, InvalidOperation
from pathlib import Path
import json
import re
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.formula.tokenizer import Tokenizer
from openpyxl.utils.cell import range_boundaries

from scripts.review_ted_xlsx_formulas import (
    EXPECTED_SHA256, EXPECTED_FORMULAS, MAX_BYTES, validate_archive,
)

CELL = re.compile(r"^\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}$", re.I)
RANGE = re.compile(r"^\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}:\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}$", re.I)
MAX_RANGE_CELLS = 10000

class UnsupportedFormula(ValueError):
    pass

def numeric(value):
    if value is None:
        return Decimal(0)
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise UnsupportedFormula("Non-numeric dependency")
    try:
        d = Decimal(str(value))
        if not d.is_finite():
            raise UnsupportedFormula("Non-finite numeric dependency")
        return d
    except InvalidOperation as exc:
        raise UnsupportedFormula("Invalid numeric dependency") from exc

def split_sheet(ref, default):
    if "!" not in ref:
        return default, ref
    name, address = ref.rsplit("!", 1)
    if name.startswith("'") and name.endswith("'"):
        name = name[1:-1].replace("''", "'")
    if not name or "[" in name or "]" in name:
        raise UnsupportedFormula("External/invalid sheet reference")
    return name, address

def recalculate(path: Path):
    import hashlib
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise UnsupportedFormula("Missing/oversized XLSX")
    if hashlib.sha256(path.read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise UnsupportedFormula("XLSX identity mismatch")
    validate_archive(path, allow_printer_settings=True)
    wb = load_workbook(path, read_only=True, data_only=False, keep_links=False)
    cached = load_workbook(path, read_only=True, data_only=True, keep_links=False)
    memo, visiting = {}, set()
    count, compared, matched, rejected, mismatch = 0, 0, 0, 0, 0

    def cell_value(sheet_name, addr):
        if sheet_name not in wb.sheetnames or not CELL.fullmatch(addr):
            raise UnsupportedFormula("Unsupported cell reference")
        normalized = addr.replace("$", "").upper()
        key = (sheet_name, normalized)
        if key in memo:
            return memo[key]
        if key in visiting:
            raise UnsupportedFormula("Circular dependency")
        visiting.add(key)
        try:
            cell = wb[sheet_name][normalized]
            if cell.data_type == "f":
                value = formula_value(str(cell.value), sheet_name)
            else:
                value = numeric(cell.value)
            memo[key] = value
            return value
        finally:
            visiting.remove(key)

    def ref_value(ref, current_sheet, *, is_sum=False):
        sheet_name, addr = split_sheet(ref, current_sheet)
        if sheet_name not in wb.sheetnames:
            raise UnsupportedFormula("Missing referenced sheet")
        if CELL.fullmatch(addr):
            return cell_value(sheet_name, addr)
        if is_sum and RANGE.fullmatch(addr):
            first_col, first_row, last_col, last_row = range_boundaries(addr.replace("$", ""))
            area = (last_col-first_col+1)*(last_row-first_row+1)
            if area < 1 or area > MAX_RANGE_CELLS:
                raise UnsupportedFormula("Invalid/oversized range")
            from openpyxl.utils.cell import get_column_letter
            total = Decimal(0)
            for row in range(first_row, last_row+1):
                for col in range(first_col, last_col+1):
                    total += cell_value(sheet_name, f"{get_column_letter(col)}{row}")
            return total
        raise UnsupportedFormula("Unsupported named or range reference")

    def formula_value(formula, sheet_name):
        parts = Tokenizer(formula).items
        position = 0
        def atom():
            nonlocal position
            if position >= len(parts):
                raise UnsupportedFormula("Incomplete expression")
            token = parts[position]
            position += 1
            if token.type == "OPERAND" and token.subtype == "RANGE":
                return ref_value(token.value, sheet_name)
            if token.type == "FUNC" and token.subtype == "OPEN" and token.value.upper() == "SUM(":
                if position >= len(parts):
                    raise UnsupportedFormula("Empty SUM")
                inner = parts[position]
                position += 1
                if inner.type != "OPERAND" or inner.subtype != "RANGE":
                    raise UnsupportedFormula("Unsupported SUM argument")
                value = ref_value(inner.value, sheet_name, is_sum=True)
                if position >= len(parts) or parts[position].type != "FUNC" or parts[position].subtype != "CLOSE":
                    raise UnsupportedFormula("Unexpected SUM syntax")
                position += 1
                return value
            raise UnsupportedFormula("Unsupported token")
        if not parts:
            raise UnsupportedFormula("Empty formula")
        total = atom()
        while position < len(parts):
            op = parts[position]
            if op.type != "OPERATOR-INFIX" or op.value != "+":
                raise UnsupportedFormula("Unsupported operator")
            position += 1
            total += atom()
        return total

    try:
        for sheet in wb:
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.data_type != "f":
                        continue
                    count += 1
                    try:
                        calculated = cell_value(sheet.title, cell.coordinate)
                        observed = cached[sheet.title][cell.coordinate].value
                        recorded = numeric(observed)
                        compared += 1
                        if abs(calculated-recorded) <= Decimal("0.000000001") * max(Decimal(1), abs(calculated), abs(recorded)):
                            matched += 1
                        else:
                            mismatch += 1
                    except (UnsupportedFormula, ValueError, TypeError, IndexError, KeyError):
                        rejected += 1
        return {
            "sha256_match": True, "formula_count": count,
            "compared": compared, "matched": matched, "mismatched": mismatch,
            "unsupported": rejected,
            "restricted_recalculation_pass": count == EXPECTED_FORMULAS and matched == count and rejected == 0,
            "authoritative_excel_acceptance": False,
            "technical_approval": False,
        }
    finally:
        wb.close()
        cached.close()

if __name__ == "__main__":
    import sys
    try:
        print(json.dumps(recalculate(Path(sys.argv[1])), sort_keys=True))
    except (ValueError, OSError, BadZipFile) as exc:
        print(json.dumps({"restricted_recalculation_pass": False, "error_type": type(exc).__name__, "technical_approval": False}))
        raise SystemExit(2)
