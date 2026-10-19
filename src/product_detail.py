"""Keep source-specific product wording separate from broad translated categories."""
from __future__ import annotations

import re

from src.field_evidence import _text


def source_product_detail(row: dict) -> str:
    raw = _text(row.get('title_original') or row.get('notice-title'))
    if not raw:
        return ''
    # TED titles carry country and CPV category before the actual procurement title.
    parts = re.split(r'\s+[–—]\s+', raw, maxsplit=2)
    if row.get('source') == 'TED' and len(parts) == 3:
        raw = parts[2]
    # Product text is customer-visible. Exclude known buyer identity and contacts.
    for key in ('buyer-name', 'buyer_name', 'borrower', 'agency', 'department', 'office'):
        name = _text(row.get(key))
        if name:
            raw = re.sub(re.escape(name), '[alıcı]', raw, flags=re.I)
    raw = re.sub(r'https?://\S+|www\.\S+|\S+@\S+|(?:\+?\d[\d ()-]{7,}\d)', '[gizlendi]', raw)
    return ' '.join(raw.split())[:500]
