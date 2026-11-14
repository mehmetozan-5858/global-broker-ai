"""Read-only, bounded metadata probe of public E-ZAK explanation/change section.

No document content, supplier data, URLs, raw text, or claims of completeness
are emitted. This is a *screening signal* and never grants tender acceptance.
"""
from html.parser import HTMLParser
import json
import re
from scripts.ezak_public_annex_sync import BASE, MAX_INDEX, get_bounded

START = "Vysvětlení, doplnění, změny zadávací dokumentace"
END = "Veřejné dokumenty"
DATE = re.compile(r"\b[0-3][0-9]\.[01][0-9]\.20[0-9]{2}\b")


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        if data.strip():
            self.parts.append(data.strip())


def summarize(html):
    if len(html) > MAX_INDEX:
        raise ValueError("oversized index")
    parser = TextOnly()
    parser.feed(html.decode("utf-8", errors="replace"))
    combined = "\n".join(parser.parts)
    # Some E-ZAK templates repeat this heading in their guidance text. We use
    # the first occurrence and explicitly do NOT certify that it is complete.
    heading = combined.find(START)
    ending = combined.find(END, heading + len(START)) if heading >= 0 else -1
    section_found = heading >= 0 and ending > heading
    dates = sorted(set(DATE.findall(combined[heading:ending]))) if section_found else []
    return {
        "official_page_section_detected": section_found,
        "dated_explanation_entries_observed": len(dates),
        "observed_dates": dates[-8:],
        "authoritative_revision_verified": False,
        "clarifications_complete": False,
        "technical_approval": False,
    }


if __name__ == "__main__":
    data, content_type, final = get_bounded(BASE, MAX_INDEX)
    if "html" not in content_type or b"<html" not in data[:10000].lower():
        raise SystemExit("Official explanation probe blocked: expected E-ZAK HTML")
    print("Official E-ZAK explanation metadata:", json.dumps(summarize(data), ensure_ascii=False, sort_keys=True))
