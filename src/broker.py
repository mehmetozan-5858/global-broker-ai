from __future__ import annotations
import json, re, urllib.request
from datetime import date, timedelta

TED_URL = "https://api.ted.europa.eu/v3/notices/search"
KEYWORDS = {
    "fertilizer": ["fertilizer","fertiliser","urea","ammonium","phosphate","potash"],
    "mining": ["bauxite","ore","mineral","copper","aluminium","aluminum","iron ore"],
    "industrial": ["industrial raw material","raw materials","chemical products"]
}

def ted_search(query: str, limit: int = 100):
    body = json.dumps({
        "query": query,
        "fields": ["publication-number","notice-title","buyer-name","buyer-country",
                   "publication-date","deadline-receipt-tender-date-lot",
                   "estimated-value-procurement","classification-cpv"],
        "page": 1, "limit": limit, "paginationMode": "PAGE_NUMBER"
    }).encode()
    req=urllib.request.Request(TED_URL,data=body,headers={"Content-Type":"application/json","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=40) as r:
        return json.load(r)

def text_of(x):
    if isinstance(x,str): return x
    if isinstance(x,list): return " ".join(text_of(v) for v in x)
    if isinstance(x,dict): return " ".join(text_of(v) for v in x.values())
    return "" if x is None else str(x)

def sector(text):
    t=text.lower()
    hits=[name for name,words in KEYWORDS.items() if any(w in t for w in words)]
    return hits[0] if hits else "other"

def score(row):
    txt=text_of(row)
    s=20
    if sector(txt)!="other": s+=25
    if row.get("buyer-name"): s+=15
    if row.get("estimated-value-procurement"): s+=15
    if row.get("deadline-receipt-tender-date-lot"): s+=10
    if row.get("classification-cpv"): s+=10
    return min(100,s)

def main():
    start=(date.today()-timedelta(days=7)).isoformat()
    # Broad supply-contract query first; sector relevance is scored locally.
    query=f"publication-date >= {start} AND contract-nature = supplies"
    raw=ted_search(query)
    notices=raw.get("notices", raw.get("results", []))
    out=[]
    for n in notices:
        item=dict(n)
        item["sector"]=sector(text_of(n))
        item["deal_score"]=score(n)
        item["source"]="TED"
        out.append(item)
    out.sort(key=lambda x:x["deal_score"],reverse=True)
    print(json.dumps({"generated":date.today().isoformat(),"mode":"shadow","count":len(out),"opportunities":out[:100]},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
