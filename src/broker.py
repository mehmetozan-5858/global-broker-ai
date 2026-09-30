from __future__ import annotations
import json, urllib.request
from datetime import date, timedelta
from urllib.error import HTTPError

TED_URL = "https://api.ted.europa.eu/v3/notices/search"

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
        "fields":["publication-number","notice-title","buyer-name","buyer-country","publication-date","deadline-receipt-tender-date-lot","classification-cpv","description-lot","quantity-lot","place-performance","procedure-type","contract-nature","duration-lot","award-criterion-type","selection-criterion","reserved-procurement","links"],
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

def main():
    today=date.today().strftime("%Y%m%d")
    query=f"publication-date = {today}"
    raw=ted_search(query,100)
    notices=raw.get("notices",raw.get("results",[]))
    out=[]
    for n in notices:
        item=dict(n)
        item["categories"]=categories(text_of(n))
        item["deal_score"]=score(n)
        item["source"]="TED"
        item["mode"]="shadow"
        item["title_original"]=first_title(n)
        item["title_tr"]=title_tr(n)
        item["detail_original"]=text_of(n.get("description-lot")) or first_title(n)
        item["detail_tr"]=title_tr({"notice-title": n.get("description-lot")}) if n.get("description-lot") else title_tr(n)
        item["buyer_verified"]=bool(n.get("buyer-name"))
        item["supplier_status"]="pending"
        item["landed_cost_status"]="pending"
        item["compliance_status"]="source_verified_buyer_pending_due_diligence" if n.get("buyer-name") else "pending"
        item["margin_status"]="pending_supplier_quote"
        item["offer_status"]="shadow_not_sent"
        item["commission_status"]="pending_deal_value_and_agreement"
        out.append(item)
    out.sort(key=lambda x:x["deal_score"],reverse=True)
    print(json.dumps({
        "generated":date.today().isoformat(),
        "scope":"ALL_GLOBAL_PRODUCTS",
        "count":len(out),
        "opportunities":out
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
