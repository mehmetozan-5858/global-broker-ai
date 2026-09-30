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
        "fields":["publication-number","notice-title","buyer-name","buyer-country","publication-date","deadline-receipt-tender-date-lot","estimated-value-procurement","classification-cpv"],
        "page":1,"limit":limit,"scope":"ACTIVE","checkQuerySyntax":False,"paginationMode":"PAGE_NUMBER","onlyLatestVersions":False
    }).encode()
    req=urllib.request.Request(TED_URL,data=body,headers={"Content-Type":"application/json","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=40) as r:
        return json.load(r)

def text_of(x):
    if isinstance(x,str): return x
    if isinstance(x,list): return " ".join(text_of(v) for v in x)
    if isinstance(x,dict): return " ".join(text_of(v) for v in x.values())
    return "" if x is None else str(x)

def categories(text):
    t=text.lower()
    hits=[name for name,words in CATEGORY_HINTS.items() if any(w in t for w in words)]
    return hits or ["uncategorized_supply"]

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
    start=(date.today()-timedelta(days=7)).isoformat()
    query=f"publication-date = [{start} TO *]"
    raw=ted_search(query,100)
    notices=raw.get("notices",raw.get("results",[]))
    out=[]
    for n in notices:
        item=dict(n)
        item["categories"]=categories(text_of(n))
        item["deal_score"]=score(n)
        item["source"]="TED"
        item["mode"]="shadow"
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
