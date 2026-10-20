"""Strict, scope-preserving World Bank notice-table facts; never quote evidence."""
from __future__ import annotations
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qs, urlsplit

HEADERS = ("lot no", "description", "quantity", "physical unit",
           "final (project site) destination as specified in bds")
UNITS = {"meter": "m", "meters": "m", "metre": "m", "metres": "m", "m": "m",
         "piece": "pcs", "pieces": "pcs", "unit": "units", "units": "units"}
LOT = re.compile(r"([1-9][0-9]{0,2})\s*:\s*(.{2,80})")
NUMBER = re.compile(r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?")
ENDINGS = ("the framework agreement", "bidding will be conducted")
MAX_ROWS = 64

def _safe(value, limit):
    return (isinstance(value, str) and 0 < len(value) <= limit
            and not any(token in value.lower() for token in ("@", "http:", "https:", "www."))
            and not any(ord(char) < 32 for char in value))

def parse(text):
    """Reject an ambiguous or damaged table as a whole, not partial row guesses."""
    if not isinstance(text, str) or len(text) > 40000:
        return []
    lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
    starts = [i for i in range(len(lines) - 4)
              if tuple(line.casefold() for line in lines[i:i+5]) == HEADERS]
    core_headers = sum(tuple(line.casefold() for line in lines[i:i+4]) == HEADERS[1:]
                       for i in range(len(lines) - 3))
    if len(starts) != 1 or core_headers != 1:
        return []
    rows, seen, lots = [], set(), {}
    current = None
    cursor = starts[0] + 5
    while cursor < len(lines):
        line = lines[cursor]
        if line.casefold().startswith(ENDINGS):
            break
        group = LOT.fullmatch(line)
        if group:
            identity, label = int(group[1]), group[2]
            if identity != len(lots) + 1 or not _safe(label, 80):
                return []
            current = identity
            lots[identity] = {"label": label, "rows": 0}
            cursor += 1
            continue
        if current is None or cursor + 4 > len(lines):
            return []
        product, amount, unit, destination = lines[cursor:cursor+4]
        if any(value.casefold().startswith(ENDINGS) or value.casefold() in HEADERS
               for value in (product, amount, unit, destination)):
            return []
        if (not _safe(product, 180) or not NUMBER.fullmatch(amount)
                or unit.casefold() not in UNITS or not _safe(destination, 80)
                or not re.fullmatch(r"[^\W\d_][^\d@:/\\]{1,79}", destination)):
            return []
        try:
            quantity = Decimal(amount.replace(",", ""))
        except InvalidOperation:
            return []
        if not quantity.is_finite() or not 0 < quantity <= 1000000000000:
            return []
        key = (current, product.casefold())
        if key in seen or len(rows) >= MAX_ROWS:
            return []
        seen.add(key)
        lots[current]["rows"] += 1
        rows.append({"lot_id": str(current), "lot_label": lots[current]["label"],
                     "product": product, "quantity": format(quantity, "f"),
                     "unit": UNITS[unit.casefold()], "destination": destination})
        cursor += 4
    if not rows or any(lot["rows"] == 0 for lot in lots.values()):
        return []
    return rows

def annotate(item, text, source_url):
    for key in ("source_line_items", "source_line_items_evidence", "source_lot_count"):
        item.pop(key, None)
    identity = item.get("id")
    if item.get("source") != "WORLD_BANK" or not isinstance(identity, str) or not re.fullmatch(r"OP[0-9]{8}", identity):
        return 0
    try:
        url = urlsplit(source_url)
        valid = (url.scheme == "https" and url.hostname == "search.worldbank.org"
                 and not url.username and not url.password and url.port in (None, 443)
                 and url.path == "/api/v2/procnotices"
                 and parse_qs(url.query).get("qterm") == [identity])
    except (ValueError, TypeError):
        return 0
    if not valid:
        return 0
    rows = parse(text)
    if not rows:
        return 0
    item["source_line_items"] = rows
    item["source_lot_count"] = len({row["lot_id"] for row in rows})
    item["source_lot_selection_required"] = True
    item["source_line_items_evidence"] = {
        "method": "explicit_notice_table", "notice_id": identity,
        "source_url": source_url, "row_count": len(rows),
        "aggregate_quantity_created": False, "exact_spec_approved": False}
    return len(rows)
