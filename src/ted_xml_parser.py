from __future__ import annotations

import re
import urllib.parse
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Iterable, Any
from xml.etree import ElementTree

MAX_EXTRACTED_CHARS = 40000
ATTACHMENT_EXTENSIONS = (".pdf", ".docx", ".txt")
EMAIL_RE = re.compile(r"(?i)(?<![A-Z0-9._%+-])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})(?![A-Z0-9._%+-])")
PHONE_RE = re.compile(r"(?<!\d)(\+?\d[\d\s()./-]{7,}\d)(?!\d)")


def _clean_text(parts: Iterable[str]) -> str:
    text = " ".join(" ".join((part or "").split()) for part in parts if part)
    return " ".join(text.split())[:MAX_EXTRACTED_CHARS]


def _looks_like_attachment(value: str) -> bool:
    try:
        path = urllib.parse.urlparse(value.strip()).path.lower()
    except Exception:
        return False
    return path.endswith(ATTACHMENT_EXTENSIONS)


def _local_name(tag: Any) -> str:
    text = str(tag or "")
    if "}" in text:
        text = text.rsplit("}", 1)[-1]
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _node_text(node: ElementTree.Element) -> str:
    return " ".join(" ".join(node.itertext()).split()).strip()


def _clean_phone(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" .,-/()")
    digits = re.sub(r"\D", "", value)
    return value if 8 <= len(digits) <= 16 else ""


def extract_ted_contacts(data: bytes) -> dict[str, str]:
    """Extract only explicit TED/eForms touchpoint contact values.

    The parser is namespace/schema tolerant, but intentionally conservative: it
    accepts e-mail/telephone/person values only from explicit contact field names,
    and accepts HTTPS web addresses only from explicit internet-address fields.
    It never promotes an arbitrary narrative e-mail or URL to buyer contact data.
    """
    root = ElementTree.fromstring(data)
    result: dict[str, str] = {}

    for node in root.iter():
        name = _local_name(node.tag)
        value = _node_text(node)
        if not value:
            continue

        if "electronicmail" in name or name in {"email", "emailaddress", "emailuri"}:
            match = EMAIL_RE.search(value)
            if match and "contact_email" not in result:
                result["contact_email"] = match.group(1).lower()
                result["contact_evidence_source"] = "ted_xml_touchpoint"
            continue

        if "telephone" in name or name in {"phone", "phonenumber", "telephonecommunication"}:
            match = PHONE_RE.search(value)
            if match and "contact_phone" not in result:
                phone = _clean_phone(match.group(1))
                if phone:
                    result["contact_phone"] = phone
                    result["contact_evidence_source"] = "ted_xml_touchpoint"
            continue

        if name in {"contactname", "personname", "contactpointname"} and "contact_person" not in result:
            if 2 <= len(value) <= 160:
                result["contact_person"] = value
                result["contact_evidence_source"] = "ted_xml_touchpoint"
            continue

        if (
            "internetaddress" in name
            or name in {"websiteuri", "endpointuri", "buyerprofileuri"}
        ) and "buyer_website" not in result:
            if value.lower().startswith("https://"):
                result["buyer_website"] = value.rstrip(".,;)")
                result["contact_evidence_source"] = "ted_xml_touchpoint"

    return result


def parse_ted_xml(data: bytes, base_url: str) -> tuple[str, list[str]]:
    """Extract source-backed text and attachment links from TED/eForms XML.

    Namespace names and tag layouts can change between eForms notice types, so this
    deliberately reads XML text nodes generically instead of binding to one schema.
    It never invents fields: only source text and explicit URL-like attributes/text
    are returned.
    """
    root = ElementTree.fromstring(data)
    if _local_name(root.tag) in {"html", "body"}:
        raise ValueError("html_is_not_ted_xml")
    text = _clean_text(root.itertext())

    links: list[str] = []
    seen: set[str] = set()
    for node in root.iter():
        candidates = list(node.attrib.values())
        if node.text:
            candidates.extend(re.findall(r"https?://[^\s<>'\"]+", node.text))
        for raw in candidates:
            if not isinstance(raw, str):
                continue
            raw = raw.strip()
            if not raw:
                continue
            absolute = urllib.parse.urljoin(base_url, raw)
            if absolute in seen or not _looks_like_attachment(absolute):
                continue
            seen.add(absolute)
            links.append(absolute)
            if len(links) >= 3:
                return text, links
    return text, links


def is_xml_source(data: bytes, content_type: str, url: str) -> bool:
    content_type = (content_type or "").lower()
    path = urllib.parse.urlparse(url).path.lower().rstrip("/")
    prefix = data.lstrip()[:80].lower()
    if b"<!doctype html" in prefix or prefix.startswith(b"<html"):
        return False
    return (
        "xml" in content_type
        or path.endswith("/xml")
        or path.endswith(".xml")
        or prefix.startswith(b"<?xml")
        or prefix.startswith(b"<notice")
    )


def _at(node: ElementTree.Element, path: str) -> ElementTree.Element | None:
    """Namespace-independent direct-child path, never a whole-document search."""
    current = node
    for name in path.split("/"):
        match = next((child for child in current if _local_name(child.tag) == name.lower()), None)
        if match is None:
            return None
        current = match
    return current


def _value(node: ElementTree.Element, path: str) -> str:
    found = _at(node, path)
    return _node_text(found) if found is not None else ""


def _positive(value: str) -> bool:
    try:
        number = Decimal(value)
        return number.is_finite() and number > 0
    except (InvalidOperation, ValueError):
        return False


def extract_ted_lots(data: bytes) -> list[dict[str, Any]]:
    """Read explicit eForms lot fields without mixing lots or supplier prices.

    Paths follow the TED eForms procedure/lot schema. Missing fields stay absent;
    quantity is not inferred from descriptive prose or the notice's title.
    """
    root = ElementTree.fromstring(data)
    lots = []
    for node in root.iter():
        if _local_name(node.tag) != "procurementprojectlot":
            continue
        identifier = _at(node, "id")
        if identifier is None or identifier.get("schemeName", "Lot") != "Lot":
            continue
        lot: dict[str, Any] = {"lot_id": _node_text(identifier), "fields": {}}
        fields = lot["fields"]
        for target, path in (
            ("product", "procurementproject/name"),
            ("description", "procurementproject/description"),
            ("delivery_city", "procurementproject/realizedlocation/address/cityname"),
            ("delivery_country", "procurementproject/realizedlocation/address/country/identificationcode"),
        ):
            value = _value(node, path)
            if value:
                fields[target] = {"value": value[:8000], "source_path": path}
        path = "procurementproject/estimatedoverallcontractquantity"
        quantity = _at(node, path)
        if quantity is not None and _positive(_node_text(quantity)):
            fields["quantity"] = {"value": _node_text(quantity), "unit": quantity.get("unitCode"), "source_path": path}
        path = "procurementproject/requestedtendertotal/estimatedoverallcontractamount"
        amount = _at(node, path)
        if amount is not None and _positive(_node_text(amount)):
            currency = amount.get("currencyID", "").upper()
            if re.fullmatch(r"[A-Z]{3}", currency):
                fields["estimated_budget"] = {"value": _node_text(amount), "currency": currency, "source_path": path}
        path = "tenderingprocess/tendersubmissiondeadlineperiod/enddate"
        deadline = _value(node, path)
        match = re.fullmatch(r"(\d{4}-\d{2}-\d{2})(Z|[+-]\d{2}:\d{2})?", deadline)
        valid_offset = True
        if match and match.group(2) and match.group(2) != "Z":
            hours, minutes = map(int, match.group(2)[1:].split(":"))
            valid_offset = hours <= 14 and minutes < 60 and (hours < 14 or minutes == 0)
        if match and valid_offset:
            try:
                date.fromisoformat(match.group(1))
            except ValueError:
                pass
            else:
                fields["deadline"] = {"value": match.group(1), "source_value": deadline, "source_path": path}
        if lot["lot_id"] and fields:
            lots.append(lot)
    return lots


def apply_ted_lots(item: dict[str, Any], lots: list[dict[str, Any]], source_url: str) -> None:
    item["ted_lots"] = lots
    item["ted_lot_count"] = len(lots)
    selected_id = str(item.get("selected_lot_id") or "")
    selected = [lot for lot in lots if lot["lot_id"] == selected_id] if selected_id else lots
    if len(selected) != 1:
        item["ted_lot_selection_required"] = len(lots) > 1
        return
    item["ted_lot_selection_required"] = False
    lot = selected[0]
    evidence = item.setdefault("structured_source_evidence", {})
    mapping = {"product": "product_name", "description": "description-lot", "deadline": "submission_deadline_date", "delivery_city": "delivery_city", "delivery_country": "delivery_country"}
    for name, fact in lot["fields"].items():
        target = mapping.get(name)
        value = fact["value"]
        if name == "quantity":
            target = "quantity"
            value += (" " + fact["unit"]) if fact.get("unit") else ""
        elif name == "estimated_budget":
            target = "estimated_value"
        if not target or item.get(target) not in (None, "", [], {}):
            continue
        if name == "estimated_budget":
            # Notice budget is never a supplier quote, unit price or profit.
            existing_currency = item.get("budget_currency")
            if existing_currency and existing_currency != fact["currency"]:
                continue
            item["budget_currency"] = fact["currency"]
        item[target] = value
        evidence[target] = {**fact, "source_url": source_url, "lot_id": lot["lot_id"], "inferred": False}
