from http.server import BaseHTTPRequestHandler
import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

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

CONTACT_KEYS = {
    "email", "e-mail", "phone", "telephone", "mobile", "contact", "contact_email", "contact_phone", "buyer_email", "buyer_phone", "supplier_email", "supplier_phone",
    "website", "linkedin", "address", "street", "postal_code", "contact_person", "representative"
}
BUYER_KEYS = {"buyer-name", "buyer_name", "borrower", "agency", "department", "office", "contracting_authority", "organization_name"}
URL_KEYS = {"source_url", "source-url", "url", "notice_url", "detail_url", "document_url"}


def _text(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return " ".join(_text(x) for x in v)
    if isinstance(v, dict):
        return " ".join(_text(x) for x in v.values())
    return str(v)


def _pick(row, keys):
    for k in keys:
        v = row.get(k)
        if v not in (None, "", [], {}):
            return v
    return ""


def _bearer(headers):
    value = headers.get("Authorization", "")
    if value.startswith("Bearer "):
        return value[7:].strip()
    return ""


def _supabase_json(path, token):
    req = Request(
        SUPABASE_URL + path,
        headers={"apikey": SUPABASE_KEY, "Authorization": "Bearer " + token, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def _identity_and_access(token):
    user = _supabase_json("/auth/v1/user", token)
    if not isinstance(user, dict) or not user.get("id"):
        return None, None, None
    uid = user["id"]
    ent = _supabase_json("/rest/v1/customer_entitlements?select=plan_id,sector_limit,country_limit,contact_credits_remaining,all_sectors,active&user_id=eq.%s&limit=1" % uid, token)
    pref = _supabase_json("/rest/v1/customer_preferences?select=selected_sectors,selected_countries&user_id=eq.%s&limit=1" % uid, token)
    entitlement = ent[0] if isinstance(ent, list) and ent else None
    preferences = pref[0] if isinstance(pref, list) and pref else {"selected_sectors": [], "selected_countries": []}
    return user, entitlement, preferences


def _data_path():
    here = Path(__file__).resolve()
    candidates = [here.parent.parent / "data" / "latest-opportunities.json", Path.cwd() / "data" / "latest-opportunities.json", Path("/var/task/data/latest-opportunities.json")]
    for p in candidates:
        if p.exists():
            return p
    return None


def _sector_for(row):
    hay = " ".join([
        _text(row.get("product_name")), _text(row.get("product")), _text(row.get("title_tr")), _text(row.get("title_original")),
        _text(row.get("bid_description")), _text(row.get("notice-title")), _text(row.get("title")), _text(row.get("demand_summary_tr")),
        _text(row.get("detail_tr")), _text((row.get("field_evidence") or {}).get("product")),
    ]).lower()
    for sector, words in SECTOR_KEYWORDS.items():
        if any(w in hay for w in words):
            return sector
    return "other"


def _country_code(row):
    raw = _text(_pick(row, ["buyer-country", "country_code", "country_name", "project_ctry_name", "country"])).strip()
    if re.fullmatch(r"[A-Za-z]{2}", raw):
        return raw.upper()
    return COUNTRY_CODES.get(raw.lower(), "")


def _mask_private(row):
    # Return only customer-safe fields. Raw contacts, direct URLs and identifiable buyer fields never leave this endpoint.
    out = {}
    for k, v in row.items():
        lk = str(k).lower()
        if lk in CONTACT_KEYS or lk in URL_KEYS or lk in BUYER_KEYS:
            continue
        if any(x in lk for x in ["email", "phone", "telephone", "mobile", "linkedin", "contact_person", "address"]):
            continue
        out[k] = v
    out["buyer_masked"] = True
    out["buyer_display"] = "Doğrulanmış alıcı — erişim kurallarına tabi"
    out["sector_id"] = _sector_for(row)
    return out


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

    def do_GET(self):
        token = _bearer(self.headers)
        if not token:
            self._json(401, {"status": "AUTHENTICATION_REQUIRED"})
            return

        user, ent, pref = _identity_and_access(token)
        if not user:
            self._json(401, {"status": "INVALID_SESSION"})
            return
        if not isinstance(ent, dict) or not ent.get("active"):
            self._json(403, {"status": "ACTIVE_PLAN_REQUIRED"})
            return

        path = _data_path()
        if not path:
            self._json(503, {"status": "OPPORTUNITY_FEED_UNAVAILABLE"})
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._json(503, {"status": "OPPORTUNITY_FEED_UNAVAILABLE"})
            return

        selected_sectors = set(pref.get("selected_sectors") or [])
        selected_countries = set(x.upper() for x in (pref.get("selected_countries") or []) if isinstance(x, str))
        all_sectors = bool(ent.get("all_sectors"))
        rows = data.get("opportunities") or []
        result = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            review = row.get("export_goods_review") or {}
            if review.get("status") != "goods_candidate":
                continue
            sector = _sector_for(row)
            if not all_sectors:
                if not selected_sectors or sector not in selected_sectors:
                    continue
            if selected_countries:
                code = _country_code(row)
                if not code or code not in selected_countries:
                    continue
            result.append(_mask_private(row))
            if len(result) >= 250:
                break

        self._json(200, {
            "mode": "authenticated_filtered",
            "plan": ent.get("plan_id", "free"),
            "selected_sectors": sorted(selected_sectors),
            "selected_countries": sorted(selected_countries),
            "contact_credits_remaining": ent.get("contact_credits_remaining"),
            "opportunities": result,
            "count": len(result),
        })
