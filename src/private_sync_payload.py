import json
import re
import sys
from pathlib import Path

from src.opportunity_identity import stable_opportunity_id

SECTOR_KEYWORDS = {
    "furniture": ["furniture", "mobilya", "chair", "table", "desk", "cabinet", "wooden", "wood", "hotel furniture", "office furniture", "interior"],
    "machinery": ["cnc", "machine", "machinery", "makine", "lathe", "milling", "industrial equipment", "automation", "spare part"],
    "textile": ["textile", "tekstil", "garment", "apparel", "fabric", "kumaş", "clothing", "uniform", "yarn"],
    "automotive": ["automotive", "vehicle part", "auto part", "otomotiv", "brake", "suspension", "filter", "tyre", "tire"],
    "packaging": ["packaging", "ambalaj", "carton", "cardboard", "corrugated", "label", "bottle", "container", "printing"],
    "construction": ["construction", "building material", "yapı", "inşaat", "ceramic", "tile", "door", "window", "insulation", "sanitary ware"],
    "food": ["food", "gıda", "grain", "cereal", "rice", "wheat", "pulse", "lentil", "nuts", "fruit", "agriculture"],
    "chemicals": ["chemical", "kimya", "fertilizer", "gübre", "resin", "polymer", "paint", "coating", "detergent"],
    "electronics": ["electrical", "electronic", "elektrik", "elektronik", "cable", "switchgear", "lighting", "transformer", "battery"],
    "medical": ["medical", "medikal", "hospital", "laboratory", "lab equipment", "diagnostic", "surgical", "sterilization"],
}

COUNTRY_CODES = {
    "turkey":"TR","türkiye":"TR","germany":"DE","deutschland":"DE","france":"FR","italy":"IT","spain":"ES","united kingdom":"GB","uk":"GB","england":"GB",
    "united states":"US","usa":"US","u.s.":"US","canada":"CA","mexico":"MX","brazil":"BR","argentina":"AR","netherlands":"NL","belgium":"BE",
    "poland":"PL","romania":"RO","bulgaria":"BG","greece":"GR","austria":"AT","switzerland":"CH","sweden":"SE","norway":"NO","denmark":"DK","finland":"FI",
    "saudi arabia":"SA","united arab emirates":"AE","uae":"AE","qatar":"QA","kuwait":"KW","oman":"OM","bahrain":"BH","jordan":"JO","egypt":"EG",
    "china":"CN","india":"IN","japan":"JP","south korea":"KR","korea":"KR","singapore":"SG","malaysia":"MY","indonesia":"ID","vietnam":"VN","thailand":"TH",
    "australia":"AU","new zealand":"NZ","south africa":"ZA","morocco":"MA","algeria":"DZ","tunisia":"TN","nigeria":"NG","kenya":"KE"
}

EMAIL_RE = re.compile(r"(?:e-?mail|email address|e-?posta|eposta)\s*[:：-]\s*([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", re.I)
PHONE_RE = re.compile(r"(?:phone|telephone|tel\.?|mobile|telefon|irtibat telefonu|contact number)\s*[:：-]\s*(\+?[0-9][0-9() .\-/]{5,24}[0-9])", re.I)
WEBSITE_RE = re.compile(r"(?:website|web site|web|internet sitesi)\s*[:：-]\s*(https://[^\s<>'\"]+)", re.I)
CONTACT_PERSON_RE = re.compile(r"(?:contact person|contact name|authorized person|yetkili|irtibat kişisi|ilgili kişi)\s*[:：-]\s*([^\n\r;|]{3,100})", re.I)

def text(v):
    if v is None: return ""
    if isinstance(v, list): return " ".join(text(x) for x in v)
    if isinstance(v, dict): return " ".join(text(x) for x in v.values())
    return str(v).strip()

def pick(row, keys):
    for key in keys:
        value = row.get(key)
        if value not in (None, "", [], {}): return text(value)
    return ""

def _https(value):
    value = str(value or "").strip().rstrip(".,;)")
    return value if value.lower().startswith("https://") else ""

def _labelled(pattern, source):
    match = pattern.search(source or "")
    return match.group(1).strip().rstrip(".,;") if match else ""

def enrich_private_contact(row):
    """Promote only explicit structured or labelled source contact facts.

    Unlabelled e-mail addresses/phone-like numbers are intentionally ignored to
    avoid turning unrelated document text into a buyer contact claim.
    """
    extracted = text(row.get("document_extracted_text"))
    email = pick(row, ["contact_email", "buyer_email", "email_address"])
    phone = pick(row, ["contact_phone", "buyer_phone", "phone_number"])
    person = pick(row, ["contact_person", "representative", "contact_name"])
    website = _https(pick(row, ["buyer_website", "organization_url", "website"]))

    if not email:
        email = _labelled(EMAIL_RE, extracted)
    if not phone:
        phone = _labelled(PHONE_RE, extracted)
    if not website:
        website = _https(_labelled(WEBSITE_RE, extracted))
    if not person:
        person = _labelled(CONTACT_PERSON_RE, extracted)

    if email:
        row["contact_email"] = email
    if phone:
        row["contact_phone"] = phone
    if person:
        row["contact_person"] = person
    if website:
        row["website"] = website
        row.pop("buyer_website", None)

    direct = bool(email or phone or website)
    official_route = bool(_https(pick(row, ["source_url", "notice_url", "detail_url", "url", "document_url"])))
    row["contact_route_available"] = direct or official_route
    row["direct_contact_available"] = direct
    row["contact_source_backed"] = bool(email or phone or website or person)
    return row

def sector_for(row):
    evidence = row.get("field_evidence") or {}
    hay = " ".join([
        text(row.get("product_name")), text(row.get("product")), text(row.get("title_tr")), text(row.get("title_original")),
        text(row.get("bid_description")), text(row.get("notice-title")), text(row.get("title")), text(row.get("demand_summary_tr")),
        text(row.get("detail_tr")), text((evidence.get("product") or {}).get("value")),
    ]).lower()
    for sector, words in SECTOR_KEYWORDS.items():
        if any(word in hay for word in words): return sector
    return "other"

def country_code(row):
    raw = pick(row, ["buyer-country", "country_code", "country_name", "project_ctry_name", "country"])
    if re.fullmatch(r"[A-Za-z]{2}", raw): return raw.upper()
    return COUNTRY_CODES.get(raw.lower(), "")

def prepare(path):
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    rows = data.get("opportunities") or []
    kept = 0
    contact_routes = 0
    direct_contacts = 0
    for row in rows:
        if not isinstance(row, dict): continue
        if (row.get("export_goods_review") or {}).get("status") != "goods_candidate": continue
        row["opportunity_id"] = stable_opportunity_id(row)
        row["sector_id"] = sector_for(row)
        row["country_code"] = country_code(row)
        enrich_private_contact(row)
        contact_routes += int(bool(row.get("contact_route_available")))
        direct_contacts += int(bool(row.get("direct_contact_available")))
        kept += 1
    data["private_contact_summary"] = {
        "opportunities": kept,
        "contact_routes_available": contact_routes,
        "direct_contacts_available": direct_contacts,
        "rule": "Only explicit structured or labelled source contact facts are promoted; unlabelled document text is not treated as contact evidence.",
    }
    p.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"PRIVATE_SYNC_METADATA_READY opportunities={kept} contact_routes={contact_routes} direct_contacts={direct_contacts}")

if __name__ == "__main__":
    prepare(sys.argv[1] if len(sys.argv) > 1 else "data/latest-opportunities.private.json")
