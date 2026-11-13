"""Bounded, read-only independent arithmetic verification for a hash-pinned XLSX.

This deliberately supports a tiny Excel subset. Anything else is UNKNOWN,
not success. Never publish raw formulas, cell values or workbook contents.
"""
import ast
import re
from collections import Counter
from decimal import Decimal, InvalidOperation
from openpyxl import load_workbook
from openpyxl.formula.tokenizer import Tokenizer
from openpyxl.utils.cell import range_boundaries
from scripts.review_ted_xlsx_formulas import EXPECTED_SHA256, inspect

CELL = re.compile(r"^\$?([A-Z]{1,3})\$?([1-9][0-9]{0,5})$", re.I)
RANGE = re.compile(r"^\$?[A-Z]{1,3}\$?[1-9][0-9]{0,5}:\$?[A-Z]{1,3}\$?[1-9][0-9]{0,5}$", re.I)
LIMIT = 5000

class Unsupported(Exception):
    pass

def decimal_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise Unsupported("non_numeric_reference")
    return Decimal(str(value))

def safe_arithmetic(expression):
    root = ast.parse(expression, mode="eval")
    def calc(node):
        if isinstance(node, ast.Expression): return calc(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return Decimal(str(node.value))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = calc(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left, right = calc(node.left), calc(node.right)
            if isinstance(node.op, ast.Add): return left + right
            if isinstance(node.op, ast.Sub): return left - right
            if isinstance(node.op, ast.Mult): return left * right
            if right == 0: raise Unsupported("division_by_zero")
            return left / right
        raise Unsupported("unsupported_operator")
    return calc(root)

def evaluate(sheet, formula, seen, depth=0):
    if depth > 20: raise Unsupported("dependency_depth")
    if not formula.startswith("="): raise Unsupported("not_formula")
    tokens = Tokenizer(formula).items
    parts = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.type == "FUNC" and token.subtype == "OPEN":
            if token.value.upper() != "SUM(": raise Unsupported("unsupported_function")
            i += 1
            if i >= len(tokens): raise Unsupported("bad_sum")
            arg = tokens[i]
            if arg.type != "OPERAND" or arg.subtype != "RANGE": raise Unsupported("unsupported_sum_argument")
            arg_value = arg.value.upper()
            if RANGE.fullmatch(arg_value):
                low_col, low_row, high_col, high_row = range_boundaries(arg_value.replace("$", ""))
                if (high_col-low_col+1)*(high_row-low_row+1) > LIMIT: raise Unsupported("range_too_large")
                vals = [get_cell(sheet, sheet.cell(row=r,column=c),seen,depth+1)
                        for r in range(low_row,high_row+1) for c in range(low_col,high_col+1)]
            elif CELL.fullmatch(arg_value):
                vals = [get_cell(sheet, sheet[arg_value.replace("$","")],seen,depth+1)]
            else:
                raise Unsupported("sum_cross_sheet_or_complex")
            i += 1
            if i >= len(tokens) or tokens[i].type != "FUNC" or tokens[i].subtype != "CLOSE":
                raise Unsupported("unsupported_sum_syntax")
            parts.append(str(sum(vals, Decimal(0))))
        elif token.type == "OPERAND":
            if token.subtype == "NUMBER": parts.append(token.value)
            elif token.subtype == "RANGE":
                if not CELL.fullmatch(token.value): raise Unsupported("cross_sheet_or_range")
                parts.append(str(get_cell(sheet,sheet[token.value.replace("$","")],seen,depth+1)))
            else: raise Unsupported("unsupported_operand")
        elif token.type == "OPERATOR-INFIX":
            if token.value not in {"+","-","*","/"}: raise Unsupported("unsupported_operator")
            parts.append(token.value)
        elif token.type == "OPERATOR-PREFIX":
            if token.value not in {"+","-"}: raise Unsupported("unsupported_prefix")
            parts.append(token.value)
        elif token.type == "PAREN":
            parts.append(token.value)
        elif token.type == "WHITE-SPACE":
            pass
        else: raise Unsupported("unsupported_token")
        i += 1
    return safe_arithmetic("".join(parts))

def get_cell(sheet,cell,seen,depth):
    key=(sheet.title,cell.coordinate)
    if key in seen: raise Unsupported("circular_reference")
    if cell.data_type == "f": return evaluate(sheet,cell.value,seen | {key},depth)
    return decimal_number(cell.value)

def verify(path):
    inventory = inspect(path,allow_printer_settings=True)
    if inventory["formula_count"] != 13: raise Unsupported("wrong_formula_count")
    formulas=load_workbook(path,read_only=False,data_only=False,keep_links=False)
    cached=load_workbook(path,read_only=True,data_only=True,keep_links=False)
    stats=Counter()
    try:
        for sheet in formulas:
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.data_type != "f": continue
                    try:
                        result=evaluate(sheet,cell.value,{(sheet.title,cell.coordinate)})
                        saved=decimal_number(cached[sheet.title][cell.coordinate].value)
                        if abs(result-saved) <= Decimal("0.0000001") * max(Decimal(1),abs(saved)):
                            stats["independently_matched"]+=1
                        else:
                            stats["mismatched"]+=1
                    except (Unsupported, InvalidOperation, SyntaxError, ValueError, TypeError, OverflowError, RecursionError) as exc:
                        stats["unsupported"]+=1
        return {"formula_count":13,"independently_matched":stats["independently_matched"],
                "mismatched":stats["mismatched"],"unsupported":stats["unsupported"],
                "technical_approval":False,
                "formula_acceptance":stats["independently_matched"]==13 and not stats["mismatched"] and not stats["unsupported"]}
    finally:
        formulas.close()
        cached.close()
