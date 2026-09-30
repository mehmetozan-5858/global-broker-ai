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

def preferred_lang_text(v):
    if isinstance(v,str): return v
    if isinstance(v,dict):
        for lang in ("eng","en"):
            x=v.get(lang)
            if isinstance(x,list) and x: return text_of(x[0])
            if x: return text_of(x)
        for x in v.values():
            t=text_of(x)
            if t: return t
    if isinstance(v,list): return text_of(v[0]) if v else ""
    return text_of(v)

def first_title(n):
    v=n.get("notice-title","")
    if isinstance(v,str): return v
    if isinstance(v,dict):
        return preferred_lang_text(v)
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

def choose_detail_text(n):
    d=text_of(n.get("description-lot")).strip()
    if d: return d
    q=text_of(n.get("quantity-lot")).strip()
    t=first_title(n).strip()
    return ("Talep: "+t+(". Miktar: "+q if q else "")).strip()

def market_region(country):
    c=(country or "").upper()
    groups=[
      ("Avrupa",["ALBANIA","AUSTRIA","BELGIUM","BULGARIA","CROATIA","CYPRUS","CZECH","DENMARK","ESTONIA","FINLAND","FRANCE","GERMANY","GREECE","HUNGARY","IRELAND","ITALY","LATVIA","LITHUANIA","LUXEMBOURG","MALTA","MOLDOVA","MONTENEGRO","NETHERLANDS","NORTH MACEDONIA","NORWAY","POLAND","PORTUGAL","ROMANIA","SERBIA","SLOVAK","SLOVENIA","SPAIN","SWEDEN","SWITZERLAND","UKRAINE","UNITED KINGDOM"]),
      ("Orta Doğu",["TURKEY","TÜRKIYE","SAUDI","UNITED ARAB EMIRATES","QATAR","OMAN","KUWAIT","BAHRAIN","IRAQ","IRAN","ISRAEL","JORDAN","LEBANON","YEMEN","PALESTINE"]),
      ("Çin / Doğu Asya",["CHINA","HONG KONG","JAPAN","SOUTH KOREA","KOREA","MONGOLIA","TAIWAN"]),
      ("ABD / Kuzey Amerika",["UNITED STATES","CANADA","MEXICO"]),
      ("Asya-Pasifik",["INDIA","PAKISTAN","BANGLADESH","SRI LANKA","NEPAL","SINGAPORE","MALAYSIA","INDONESIA","THAILAND","VIETNAM","PHILIPPINES","AUSTRALIA","NEW ZEALAND","CAMBODIA","LAO","MYANMAR","AFGHANISTAN","KAZAKHSTAN","UZBEKISTAN","KYRGYZ","TAJIKISTAN","TURKMENISTAN"]),
      ("Afrika",["EGYPT","SOUTH AFRICA","MOROCCO","ALGERIA","NIGERIA","KENYA","GHANA","TUNISIA","ETHIOPIA","TANZANIA","UGANDA","RWANDA","SENEGAL","ZAMBIA","ZIMBABWE","MOZAMBIQUE","CAMEROON","COTE D","IVORY COAST","ANGOLA","BENIN","BOTSWANA","BURKINA","BURUNDI","CABO VERDE","CENTRAL AFRICAN","CHAD","COMOROS","CONGO","DJIBOUTI","EQUATORIAL GUINEA","ERITREA","ESWATINI","GABON","GAMBIA","GUINEA","LESOTHO","LIBERIA","LIBYA","MADAGASCAR","MALAWI","MALI","MAURITANIA","MAURITIUS","NAMIBIA","NIGER","SAO TOME","SEYCHELLES","SIERRA LEONE","SOMALIA","SOUTH SUDAN","SUDAN","TOGO"])
    ]
    for name,tokens in groups:
        if any(t in c for t in tokens): return name
    return "Diğer Pazarlar"

def demand_summary_tr(item):
    title=(item.get("title_tr") or item.get("title_original") or "").strip()
    detail=(item.get("detail_tr") or "").strip()
    cat=text_of(item.get("classification-cpv") or item.get("procurement_category") or item.get("sector")).strip()
    qty=text_of(item.get("quantity-lot") or item.get("quantity")).strip()
    parts=[]
    if detail and detail.lower()!=title.lower(): parts.append(detail)
    elif title: parts.append(title)
    if qty: parts.append("Miktar: "+qty)
    if cat: parts.append("Kategori / ürün grubu: "+cat)
    return ". ".join(parts).strip() or "İlan kaynağında ayrıntılı talep açıklaması bulunmuyor."

def commercial_signals(item):
    text=(" ".join([text_of(item.get("title_original")),text_of(item.get("detail_original")),text_of(item.get("classification-cpv")),text_of(item.get("categories"))])).lower()
    goods_words=["supply","purchase","procurement","equipment","material","goods","product","vehicle","machine","medical","food","chemical","textile","steel","cable","furniture"]
    service_words=["consulting","consultancy","audit","training","software development","technical assistance","study","supervision"]
    goods=sum(1 for w in goods_words if w in text)
    services=sum(1 for w in service_words if w in text)
    if goods>services:
        fit="Ürün tedariği ağırlıklı — broker modeli için incelenecek"
        turkey="Türkiye'den tedarikçi eşleştirmesi araştırılacak"
    elif services>goods:
        fit="Hizmet/uzmanlık ağırlıklı — ürün brokerlığı uygunluğu ayrıca kontrol edilecek"
        turkey="Türkiye'den uygun hizmet sağlayıcı araştırılacak"
    else:
        fit="Ön değerlendirme gerekli"
        turkey="Türkiye bağlantılı tedarik olasılığı araştırılacak"
    return {
      "broker_opportunity":fit,
      "turkey_supply_status":turkey,
      "supplier_search_status":"Ajan araştırması bekliyor",
      "commission_potential":"İşlem değeri ve komisyon anlaşması olmadan hesaplanamaz"
    }

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
    params=urllib.parse.urlencode({"format":"json","rows":limit,"os":0,"srce":"both","srt":"submission_deadline_date","order":"desc","apilang":"en","fl":"id,url,notice_type,publication_date,project_id,bid_description,procurement_category,procurement_method,deadline_date,country_code,country_name,sector,project_name"})
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
    title=text_of(n.get("bid_description") or n.get("notice_title") or n.get("description") or n.get("title"))
    country=text_of(n.get("country_name") or n.get("project_ctry_name") or n.get("country") or n.get("regionname"))
    deadline=text_of(n.get("deadline_date") or n.get("submission_deadline_date") or n.get("deadline") or n.get("closing_date"))
    buyer=text_of(n.get("borrower") or n.get("agency") or n.get("project_name"))
    item=dict(n)
    item["title_original"]=title
    item["title_tr"]=auto_translate_tr(title) or title
    item["detail_original"]=text_of(n.get("bid_description") or n.get("notice_text") or n.get("description") or title)
    item["detail_tr"]=auto_translate_tr(item["detail_original"]) or item["title_tr"]
    item["buyer-country"]=country
    item["market_region"]=market_region(country)
    item["buyer-name"]=buyer
    item["deadline-receipt-tender-date-lot"]=deadline
    item["categories"]=categories(item["detail_original"])
    item["classification-cpv"]=text_of(n.get("procurement_category") or n.get("sector"))
    item["procedure-type"]=text_of(n.get("procurement_method") or n.get("notice_type"))
    item["source_url"]=text_of(n.get("url"))
    item["source"]="WORLD_BANK"
    item["region_hint"]="GLOBAL_WORLD_BANK"
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
        item["detail_original"]=preferred_lang_text(n.get("description-lot")) or first_title(n)
        item["detail_tr"]=auto_translate_tr(item["detail_original"]) or title_tr(n)
        item["buyer-name"]=preferred_lang_text(n.get("buyer-name"))
        item["buyer-country"]=preferred_lang_text(n.get("buyer-country"))
        item["market_region"]=market_region(item["buyer-country"])
        item["buyer_verified"]=bool(item["buyer-name"])
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
