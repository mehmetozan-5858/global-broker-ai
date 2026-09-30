from __future__ import annotations
import json, urllib.request, urllib.parse
from datetime import date, timedelta
from urllib.error import HTTPError

TED_URL = "https://api.ted.europa.eu/v3/notices/search"
WORLD_BANK_URL = "https://search.worldbank.org/api/v2/procnotices"

# Global Broker is product-agnostic: no sector is hard-coded as the business.
# Categories are descriptive signals only; ALL supply opportunities remain eligible.
CATEGORY_HINTS = {
    "agriculture_food": ["food","grain","wheat","rice","corn","oilseed","fertilizer","fertiliser","urea"],
    "metals_mining": ["ore","mineral","bauxite","copper","aluminium","aluminum","steel","iron"],
    "chemicals": ["chemical","polymer","resin","solvent","acid"],
    "energy_fuels": ["fuel","diesel","gas","energy","lubricant"],
    "construction": ["cement","bitumen","aggregate","glass","timber","building material"],
    "machinery": ["machinery","machine","pump","compressor","generator","equipment"],
    "electrical_electronics": ["electrical","electronic","cable","transformer","battery"],
    "medical": ["medical","pharmaceutical","medicine","laboratory","hospital"],
    "textiles": ["textile","fabric","garment","clothing"],
    "packaging": ["packaging","paper","cardboard","container","bottle"],
    "transport_parts": ["vehicle","automotive","spare parts","tyre","tire"],
    "industrial_general": ["raw material","industrial","component","consumable"]
}

def ted_search(query: str, limit: int = 100):
    body=json.dumps({
        "query":query,
        "fields":["publication-number","notice-title","buyer-name","buyer-country","publication-date","deadline-receipt-tender-date-lot","classification-cpv","description-lot","quantity-lot","procedure-type","contract-nature","links"],
        "page":1,"limit":limit,"scope":"ACTIVE","checkQuerySyntax":False,"paginationMode":"PAGE_NUMBER","onlyLatestVersions":False
    }).encode()
    req=urllib.request.Request(TED_URL,data=body,headers={"Content-Type":"application/json","Accept":"*/*"})
    try:
        with urllib.request.urlopen(req,timeout=40) as r:
            return json.load(r)
    except HTTPError as e:
        raise RuntimeError("TED HTTP %s: %s" % (e.code,e.read().decode("utf-8","replace"))) from e

def text_of(x):
    if isinstance(x,str): return x
    if isinstance(x,list): return " ".join(text_of(v) for v in x)
    if isinstance(x,dict): return " ".join(text_of(v) for v in x.values())
    return "" if x is None else str(x)

def categories(text):
    t=text.lower()
    hits=[name for name,words in CATEGORY_HINTS.items() if any(w in t for w in words)]
    return hits or ["uncategorized_supply"]

TR_TERMS = {
"medical":"medikal","hospital":"hastane","equipment":"ekipman","vehicle":"araç","food":"gıda","construction":"inşaat",
"machinery":"makine","electrical":"elektrik","electronic":"elektronik","chemical":"kimyasal","textile":"tekstil",
"packaging":"ambalaj","supply":"tedarik","services":"hizmetler","service":"hizmet","maintenance":"bakım","repair":"onarım",
"purchase":"satın alma","procurement":"tedarik","delivery":"teslimat","works":"yapım işleri","system":"sistem","systems":"sistemler"
}

def first_title(n):
    v=n.get("notice-title","")
    if isinstance(v,str): return v
    if isinstance(v,dict):
        vals=[]
        for x in v.values():
            vals += x if isinstance(x,list) else [x]
        return next((str(x) for x in vals if x), "")
    if isinstance(v,list): return str(v[0]) if v else ""
    return str(v or "")

def auto_translate_tr(text):
    text=(text or "").strip()
    if not text: return ""
    try:
        q=urllib.parse.urlencode({"client":"gtx","sl":"auto","tl":"tr","dt":"t","q":text[:4500]})
        req=urllib.request.Request("https://translate.googleapis.com/translate_a/single?"+q,headers={"User-Agent":"GlobalBrokerAI/1.0"})
        with urllib.request.urlopen(req,timeout=20) as r:
            data=json.load(r)
        return "".join(p[0] for p in data[0] if p and p[0]).strip()
    except Exception:
        return ""

def title_tr(n):
    original=first_title(n).strip()
    if not original: return "Uluslararası satın alma talebi"
    words=original.replace("-"," - ").split()
    translated=[TR_TERMS.get(w.lower().strip(".,:;()"),w) for w in words]
    changed=sum(a!=b for a,b in zip(words,translated))
    if changed>=2: return " ".join(translated)[:160]
    cats=categories(text_of(n))
    labels={"medical":"Medikal ürün alımı","machinery":"Makine / ekipman alımı","construction":"İnşaat malzemesi alımı",
    "agriculture_food":"Gıda / tarım ürünü alımı","transport_parts":"Araç / yedek parça alımı","electrical_electronics":"Elektrik / elektronik alımı",
    "chemicals":"Kimyasal ürün alımı","textiles":"Tekstil ürünü alımı","packaging":"Ambalaj ürünü alımı","metals_mining":"Metal / maden ürünü alımı"}
    for k,v in labels.items():
        if k in cats:return v
    return "Uluslararası satın alma talebi"

def score(row):
    # Product-neutral initial score. Later agents add supplier, landed-cost,
    # payment-risk, sanctions/compliance, margin and close-probability signals.
    s=20
    if row.get("buyer-name"): s+=20
    if row.get("estimated-value-procurement"): s+=20
    if row.get("deadline-receipt-tender-date-lot"): s+=15
    if row.get("classification-cpv"): s+=15
    if row.get("buyer-country"): s+=10
    return min(100,s)


def world_bank_search(limit: int = 200):
    """Public World Bank procurement notices. Fail closed: no synthetic rows."""
    params=urllib.parse.urlencode({"format":"json","rows":limit,"os":0,"srce":"both","srt":"submission_deadline_date","order":"desc","apilang":"en","fl":"id,notice_type,publication_date,submission_deadline_date,project_ctry_name,project_id,project_name,notice_text,notice_title,description"})
    req=urllib.request.Request(WORLD_BANK_URL+"?"+params,headers={"User-Agent":"GlobalBrokerAI/1.0","Accept":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=40) as r:
            data=json.load(r)
        docs=data.get("procnotices",data.get("documents",data.get("results",[])))
        if isinstance(docs,dict): docs=list(docs.values())
        return docs if isinstance(docs,list) else []
    except Exception:
        return []

def normalize_world_bank(n):
    title=text_of(n.get("notice_title") or n.get("description") or n.get("title"))
    country=text_of(n.get("project_ctry_name") or n.get("country_name") or n.get("country") or n.get("regionname"))
    deadline=text_of(n.get("submission_deadline_date") or n.get("deadline") or n.get("closing_date"))
    buyer=text_of(n.get("borrower") or n.get("agency") or n.get("project_name"))
    item=dict(n)
    item["title_original"]=title
    item["title_tr"]=auto_translate_tr(title) or title
    item["detail_original"]=text_of(n.get("notice_text") or n.get("description") or title)
    item["detail_tr"]=auto_translate_tr(item["detail_original"]) or item["title_tr"]
    item["buyer-country"]=country
    item["buyer-name"]=buyer
    item["deadline-receipt-tender-date-lot"]=deadline
    item["categories"]=categories(item["detail_original"])
    item["source"]="WORLD_BANK"
    item["mode"]="shadow"
    item["buyer_verified"]=bool(buyer)
    item["supplier_status"]="pending"
    item["landed_cost_status"]="pending"
    item["compliance_status"]="source_verified_buyer_pending_due_diligence" if buyer else "pending"
    item["margin_status"]="pending_supplier_quote"
    item["offer_status"]="shadow_not_sent"
    item["commission_status"]="pending_deal_value_and_agreement"
    item["deal_score"]=score(item)
    return item

def main():
    # Scan a rolling window instead of only today's notices. This gives the
    # regional agents a broader live pool while TED remains the first source.
    # More official sources (UNGM, World Bank, SAM.gov) are added as separate
    # adapters; never fabricate rows when a source cannot be queried.
    end=date.today()
    start=end-timedelta(days=14)
    query=f"publication-date >= {start.strftime('%Y%m%d')} AND publication-date <= {end.strftime('%Y%m%d')}"
    raw=ted_search(query,250)
    notices=raw.get("notices",raw.get("results",[]))
    out=[]
    for n in notices:
        item=dict(n)
        item["categories"]=categories(text_of(n))
        item["deal_score"]=score(n)
        item["source"]="TED"
        item["mode"]="shadow"
        item["title_original"]=first_title(n)
        item["title_tr"]=auto_translate_tr(first_title(n)) or title_tr(n)
        item["detail_original"]=text_of(n.get("description-lot")) or first_title(n)
        item["detail_tr"]=auto_translate_tr(item["detail_original"]) or title_tr({"notice-title": n.get("description-lot")}) if n.get("description-lot") else (auto_translate_tr(item["detail_original"]) or title_tr(n))
        item["buyer_verified"]=bool(n.get("buyer-name"))
        item["supplier_status"]="pending"
        item["landed_cost_status"]="pending"
        item["compliance_status"]="source_verified_buyer_pending_due_diligence" if n.get("buyer-name") else "pending"
        item["margin_status"]="pending_supplier_quote"
        item["offer_status"]="shadow_not_sent"
        item["commission_status"]="pending_deal_value_and_agreement"
        out.append(item)
    # Add non-European/global opportunities from the World Bank public procurement feed.
    # Source failures simply add zero rows; they never create placeholder opportunities.
    for n in world_bank_search(200):
        try:
            item=normalize_world_bank(n)
            if item.get("title_original"):
                out.append(item)
        except Exception:
            continue

    # Deduplicate across sources by normalized title + buyer/country.
    deduped=[]
    seen=set()
    for item in out:
        key=(item.get("title_original","").strip().lower(), text_of(item.get("buyer-name")).strip().lower(), text_of(item.get("buyer-country")).strip().lower())
        if key in seen: continue
        seen.add(key); deduped.append(item)
    out=deduped
    out.sort(key=lambda x:x["deal_score"],reverse=True)
    print(json.dumps({
        "generated":date.today().isoformat(),
        "scope":"ALL_GLOBAL_PRODUCTS",
        "count":len(out),
        "opportunities":out
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
