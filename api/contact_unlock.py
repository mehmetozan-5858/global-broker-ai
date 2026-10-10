from http.server import BaseHTTPRequestHandler
import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from src.opportunity_identity import stable_opportunity_id

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://yhzdqrqzjruduohypvqf.supabase.co").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_fFtN0JmDBp8TP01lKJhTFQ_sx6mkt-w")

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


def _text(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return " ".join(_text(x) for x in v)
    if isinstance(v, dict):
        return " ".join(_text(x) for x in v.values())
    return str(v).strip()


def _pick(row, keys):
    for key in keys:
        value = row.get(key)
        if value not in (None, "", [], {}):
            return _text(value)
    return ""


def _bearer(headers):
    value = headers.get("Authorization", "")
    return value[7:].strip() if value.startswith("Bearer ") else ""


def _supabase(path, token, method="GET", payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": "Bearer " + token,
        "Accept": "application/json",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = Request(SUPABASE_URL + path, headers=headers, data=data, method=method)
    try:
        with urlopen(req, timeout=10) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8")
            body = json.loads(raw) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            body = {}
        return exc.code, body
    except (URLError, TimeoutError, json.JSONDecodeError):
        return 503, {}


def _identity_and_access(token):
    status, user = _supabase("/auth/v1/user", token)
    if status != 200 or not isinstance(user, dict) or not user.get("id"):
        return None, None, None
    uid = user["id"]
    _, ent = _supabase("/rest/v1/customer_entitlements?select=plan_id,contact_credits_remaining,all_sectors,active&user_id=eq.%s&limit=1" % uid, token)
    _, pref = _supabase("/rest/v1/customer_preferences?select=selected_sectors,selected_countries&user_id=eq.%s&limit=1" % uid, token)
    entitlement = ent[0] if isinstance(ent, list) and ent else None
    preferences = pref[0] if isinstance(pref, list) and pref else {"selected_sectors": [], "selected_countries": []}
    return user, entitlement, preferences


def _data_path():
    here = Path(__file__).resolve()
    for path in [here.parent.parent / "data" / "latest-opportunities.json", Path.cwd() / "data" / "latest-opportunities.json", Path("/var/task/data/latest-opportunities.json")]:
        if path.exists():
            return path
    return None


def _sector_for(row):
    evidence = row.get("field_evidence") or {}
    hay = " ".join([
        _text(row.get("product_name")), _text(row.get("product")), _text(row.get("title_tr")), _text(row.get("title_original")),
        _text(row.get("bid_description")), _text(row.get("notice-title")), _text(row.get("title")), _text(row.get("demand_summary_tr")),
        _text(row.get("detail_tr")), _text((evidence.get("product") or {}).get("value")),
    ]).lower()
    for sector, words in SECTOR_KEYWORDS.items():
        if any(word in hay for word in words):
            return sector
    return "other"


def _country_code(row):
    raw = _pick(row, ["buyer-country", "country_code", "country_name", "project_ctry_name", "country"])
    if re.fullmatch(r"[A-Za-z]{2}", raw):
        return raw.upper()
    return COUNTRY_CODES.get(raw.lower(), "")


def _contact_payload(row):
    evidence = row.get("field_evidence") or {}
    buyer_evidence = evidence.get("buyer") or {}
    buyer = _text(buyer_evidence.get("value")) or _pick(row, ["buyer-name", "buyer_name", "borrower", "agency", "department", "office", "contracting_authority", "organization_name"])
    contact_person = _pick(row, ["contact_person", "representative", "contact-name", "contact_name"])
    email = _pick(row, ["contact_email", "buyer_email", "email", "e-mail", "email_address"])
    phone = _pick(row, ["contact_phone", "buyer_phone", "phone", "telephone", "mobile", "phone_number"])
    website = _pick(row, ["website", "buyer_website", "organization_url"])
    linkedin = _pick(row, ["linkedin", "linkedin_url"])
    address = _pick(row, ["address", "buyer_address", "street", "postal_address"])
    source_url = _pick(row, ["source_url", "source-url", "notice_url", "detail_url", "url"])
    result = {
        "buyer_name": buyer,
        "contact_person": contact_person,
        "email": email,
        "phone": phone,
        "website": website,
        "linkedin": linkedin,
        "address": address,
        "source_url": source_url,
    }
    return {key: value for key, value in result.items() if value}


def _find_opportunity(opportunity_id):
    path = _data_path()
    if not path:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    for row in data.get("opportunities") or []:
        if isinstance(row, dict) and stable_opportunity_id(row) == opportunity_id:
            return row
    return None


class handler(BaseHTTPRequestHandler):
    def _json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "private, no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Vary", "Authorization")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        token = _bearer(self.headers)
        if not token:
            self._json(401, {"status": "AUTHENTICATION_REQUIRED"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > 2048:
            self._json(400, {"status": "INVALID_REQUEST"})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"status": "INVALID_JSON"})
            return
        opportunity_id = str((payload or {}).get("opportunity_id") or "").strip()
        if len(opportunity_id) < 8 or len(opportunity_id) > 200:
            self._json(400, {"status": "INVALID_OPPORTUNITY_ID"})
            return

        user, ent, pref = _identity_and_access(token)
        if not user:
            self._json(401, {"status": "INVALID_SESSION"})
            return
        if not isinstance(ent, dict) or not ent.get("active"):
            self._json(403, {"status": "ACTIVE_PLAN_REQUIRED"})
            return

        row = _find_opportunity(opportunity_id)
        if not row:
            self._json(404, {"status": "OPPORTUNITY_NOT_FOUND"})
            return
        if (row.get("export_goods_review") or {}).get("status") != "goods_candidate":
            self._json(403, {"status": "OPPORTUNITY_NOT_ELIGIBLE"})
            return

        selected_sectors = set(pref.get("selected_sectors") or [])
        selected_countries = set(x.upper() for x in (pref.get("selected_countries") or []) if isinstance(x, str))
        sector = _sector_for(row)
        country = _country_code(row)
        if not ent.get("all_sectors") and (not selected_sectors or sector not in selected_sectors):
            self._json(403, {"status": "SECTOR_NOT_IN_PLAN"})
            return
        if selected_countries and (not country or country not in selected_countries):
            self._json(403, {"status": "COUNTRY_NOT_SELECTED"})
            return

        contact = _contact_payload(row)
        if not contact:
            self._json(404, {"status": "CONTACT_NOT_AVAILABLE"})
            return

        rpc_status, rpc = _supabase(
            "/rest/v1/rpc/consume_contact_credit",
            token,
            method="POST",
            payload={"p_opportunity_id": opportunity_id},
        )
        if rpc_status >= 400:
            message = str((rpc or {}).get("message") or "")
            if "contact_credit_required" in message:
                self._json(402, {"status": "CONTACT_CREDIT_REQUIRED"})
            else:
                self._json(403, {"status": "CONTACT_UNLOCK_DENIED"})
            return

        self._json(200, {
            "status": "UNLOCKED",
            "opportunity_id": opportunity_id,
            "already_unlocked": bool((rpc or {}).get("already_unlocked")),
            "credits_remaining": (rpc or {}).get("credits_remaining"),
            "contact": contact,
        })
