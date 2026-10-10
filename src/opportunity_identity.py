import hashlib
import json

ID_KEYS=(
    "opportunity_id","id","notice_id","notice-id","tender_id","tender-id",
    "ocid","reference","reference_number","notice_number","notice-number"
)


def _text(value):
    if value is None:
        return ""
    if isinstance(value,(dict,list)):
        try:
            return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))
        except TypeError:
            return str(value)
    return str(value).strip()


def stable_opportunity_id(row):
    if not isinstance(row,dict):
        return ""
    for key in ID_KEYS:
        value=_text(row.get(key))
        if value:
            return value[:200]
    evidence=row.get("field_evidence") or {}
    parts=[
        _text(row.get("source")),
        _text(row.get("source_name")),
        _text(row.get("title_original")),
        _text(row.get("title_tr")),
        _text(row.get("notice-title")),
        _text(row.get("buyer-country")),
        _text(row.get("country_code")),
        _text(row.get("deadline")),
        _text(row.get("closing_date")),
        _text((evidence.get("product") or {}).get("value")),
        _text((evidence.get("deadline") or {}).get("value")),
    ]
    seed="|".join(p for p in parts if p)
    if not seed:
        seed=json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str)
    return "gb_"+hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]
