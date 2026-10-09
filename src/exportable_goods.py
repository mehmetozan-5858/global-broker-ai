"""Conservative physical-goods export eligibility for international brokerage.

Unknown or mixed procurements are held for review, never promoted as verified
exportable goods solely because their title contains 'equipment' or 'supply'.
"""
from __future__ import annotations
import re
from typing import Any

SERVICE = re.compile(r"\b(?:consult(?:ant|ancy|ing)?|engineering services?|architect(?:ure|ural)? services?|personnel|staff(?:ing)?|recruitment|training|audit(?:ing)?|technical assistance|feasibility study|drilling services?|well drilling|maintenance services?|repair services?|cleaning services?|security services?|transport services?|logistics services?|construction works?|civil works?|works contract|service contract|hizmet(?:leri)?|danışmanlık|mühendis(?:lik|i)?|personel|istihdam|eğitim hizmeti|sondaj hizmeti|bakım hizmeti|onarım hizmeti|inşaat işi|yapım işi)\b",re.I)
GOODS = re.compile(r"\b(?:goods|supplies|equipment|machinery|machines?|materials?|products?|spare parts?|vehicles?|furniture|medical devices?|medicines?|pharmaceuticals?|textiles?|garments?|chemicals?|food|grain|steel|cables?|generators?|computers?|servers?|laptops?|network equipment|desks?|chairs?|beds?|pumps?|pipes?|procurement of goods|supply and delivery|temini|tedariki|mal alımı|ekipman|makine|malzeme|ürün|yedek parça|araç|mobilya|ilaç|gıda|kablo|jeneratör|bilgisayar|masa|sandalye|ranza|pompa|boru)\b",re.I)
GOODS_TYPES={"goods","supply","supplies","mal alımı","mal alimi","ürün","goods contract"}
SERVICE_TYPES={"services","service","works","consulting services","consultancy","consulting","hizmet","hizmet alımı","construction","works contract"}

def _text(value: Any)->str:
    if isinstance(value,dict):return " ".join(_text(x) for x in value.values())
    if isinstance(value,list):return " ".join(_text(x) for x in value)
    return str(value or "").strip()

def classify(item: dict[str,Any])->dict[str,str]:
    typ=_text(next((item[k] for k in ("contract-nature","procurement_category","procurement_type","contract_type","contract-nature-lot") if item.get(k)), "")).lower().strip()
    title=_text(item.get("title_original") or item.get("title_tr") or item.get("bid_description") or item.get("notice-title") or item.get("title"))
    goods=bool(GOODS.search(title))
    service=bool(SERVICE.search(title))
    if typ in SERVICE_TYPES:
        return {"status":"exclude_service","reason":"Kaynak ihale türü hizmet veya yapım olarak bildiriyor."}
    if typ in GOODS_TYPES:
        if service:
            return {"status":"review_mixed","reason":"Mal alımı olarak sınıflandırılmış ancak başlıkta hizmet/yapım unsuru var."}
        return {"status":"goods_candidate","reason":"Kaynak mal alımı olarak sınıflandırıyor; ihracat ve katılım koşulları ayrıca doğrulanmalı."}
    if goods and service:
        return {"status":"review_mixed","reason":"Başlıkta hem fiziksel ürün hem hizmet unsurları bulunuyor."}
    if service:
        return {"status":"exclude_service","reason":"Başlık hizmet, personel veya yapım işi içeriyor."}
    if goods:
        return {"status":"goods_candidate","reason":"Başlık fiziksel ürün tedarikine işaret ediyor; tür ve ihracat koşulları teyit edilmeli."}
    return {"status":"review_unknown","reason":"İlanın fiziksel mal alımı olduğu henüz kanıtlanamadı."}
