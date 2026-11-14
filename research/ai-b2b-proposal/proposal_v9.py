"""v9 offline evidence prototype. Manually structured input; no commercial approval."""
import re
import unicodedata
from datetime import date

def normalized(value):
    t = unicodedata.normalize("NFKD", value.casefold().replace("ı", "i"))
    return "".join(c for c in t if not unicodedata.combining(c))

def topic_of(question):
    if not isinstance(question, str):
        return None
    q = normalized(question)
    if "iso 27001" in q: return "iso27001"
    if "uptime" in q or "99.9%" in q: return "uptime"
    if "english" in q or "ingilizce" in q: return "english"
    return None

def topic_in_text(text):
    t = normalized(text)
    topics = set()
    if "iso 27001" in t: topics.add("iso27001")
    if any(x in t for x in ("uptime", "availability guarantee", "99.9%")): topics.add("uptime")
    if any(x in t for x in ("english", "ingilizce")): topics.add("english")
    return topics

def classify(topic, text):
    s = normalized(text)
    if topic == "english":
        if any(x in s for x in ("do not support english", "only german is supported", "english support is unavailable")): return "NEGATIVE"
        if "we support english" in s: return "POSITIVE"
    if topic == "iso27001":
        if any(x in s for x in ("sertifikamiz yoktur", "not certified", "expired", "suresi doldu")): return "NEGATIVE"
        if any(x in s for x in ("sertifikamiz vardir", "we are iso 27001 certified")): return "POSITIVE"
    if topic == "uptime":
        if any(x in s for x in ("do not guarantee", "not guaranteed", "no availability guarantee")): return "NEGATIVE"
        if re.search(r"guarantee 99[.,]9\s*% uptime", s): return "POSITIVE"
    return "UNRESOLVED"

def verify_v9(question, records, company="OUR_COMPANY", region=None, as_of=None):
    today = as_of or date.today()
    topic = topic_of(question)
    response = {"decision": "REVIEW_SCOPE", "topic": topic, "evidence": [],
                "review": [], "ignored": [], "commercial_approval": False,
                "automatic_offer": False}
    if not topic or not isinstance(records, list) or not isinstance(company, str) or not company:
        response["review"].append(("?", "QUERY_OR_INPUT_UNSUPPORTED"))
        return response
    for i, r in enumerate(records):
        if not isinstance(r, dict):
            response["review"].append((str(i + 1), "RECORD_INVALID"))
            continue
        line = str(r.get("line") or f"R{i + 1}")
        raw = r.get("text")
        declared_topic = r.get("topic")
        if declared_topic is not None and declared_topic not in ("english", "iso27001", "uptime"):
            response["review"].append((line, "TOPIC_UNVERIFIED"))
            continue
        if not isinstance(raw, str) or not raw.strip():
            response["review"].append((line, "TEXT_INVALID"))
            continue
        detected = topic_in_text(raw)
        if topic not in detected and detected and declared_topic != topic:
            response["ignored"].append((line, "OTHER_TOPIC"))
            continue
        if topic not in detected:
            response["review"].append((line, "RELEVANCE_UNCERTAIN"))
            continue
        if declared_topic is not None and declared_topic != topic:
            response["review"].append((line, "TOPIC_CONFLICT"))
            continue
        identity = r.get("company")
        if not isinstance(identity, str) or not identity.strip():
            response["review"].append((line, "COMPANY_MISSING"))
            continue
        if identity != company:
            response["ignored"].append((line, "OTHER_COMPANY"))
            continue
        if region:
            area = r.get("region")
            if not area:
                response["review"].append((line, "REGION_MISSING"))
                continue
            if area not in (region, "GLOBAL"):
                response["review"].append((line, "REGION_MISMATCH"))
                continue
        invalid = False
        for key in ("valid_from", "valid_until"):
            v = r.get(key)
            if v is not None:
                try:
                    if not isinstance(v, str): raise TypeError("date must be string")
                    parsed = date.fromisoformat(v)
                except (ValueError, TypeError):
                    response["review"].append((line, key.upper() + "_INVALID"))
                    invalid = True
                    break
                if key == "valid_from" and parsed > today:
                    response["review"].append((line, "FUTURE_SERVICE"))
                    invalid = True
                    break
                if key == "valid_until" and parsed < today:
                    response["review"].append((line, "EXPIRED"))
                    invalid = True
                    break
        if invalid: continue
        if r.get("valid_from") and r.get("valid_until") and r["valid_from"] > r["valid_until"]:
            response["review"].append((line, "DATE_RANGE_CONFLICT"))
            continue
        status = classify(topic, raw)
        if status == "UNRESOLVED":
            response["review"].append((line, "EVIDENCE_UNRESOLVED"))
            continue
        if topic == "iso27001" and status == "POSITIVE" and r.get("verified") is not True:
            response["review"].append((line, "VALIDITY_UNVERIFIED"))
            continue
        response["evidence"].append((line, status))
    states = {s for _, s in response["evidence"]}
    if len(states) > 1: response["decision"] = "CONFLICT"
    elif response["review"]: response["decision"] = "REVIEW_SCOPE"
    elif len(states) == 1: response["decision"] = next(iter(states))
    else: response["decision"] = "UNKNOWN"
    return response
