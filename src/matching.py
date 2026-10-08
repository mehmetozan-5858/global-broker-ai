"""Buyer-seller matching: compatibility is not verification or consent."""
from dataclasses import dataclass
import re

@dataclass
class TradeIntent:
    id: str
    side: str
    product: str
    country: str
    quantity_mt: float | None = None
    hs_code: str = ""
    grade: str = ""
    company_verified: bool = False
    contact_consent: bool = False

def clean(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))

def match(buyer: TradeIntent, seller: TradeIntent) -> dict:
    result = dict(buyer_id=buyer.id, seller_id=seller.id, score=0,
                  status="INCOMPATIBLE", can_reveal_contacts=False, missing=[])
    if buyer.side != "BUY" or seller.side != "SELL":
        return result
    if not clean(buyer.product) or clean(buyer.product) != clean(seller.product):
        return result
    score = 40
    for field, weight in (("hs_code", 15), ("grade", 15)):
        a, b = getattr(buyer, field), getattr(seller, field)
        if a and b:
            if clean(a) != clean(b):
                return result
            score += weight
        else:
            result["missing"].append(field)
    if buyer.quantity_mt is not None and seller.quantity_mt is not None:
        if buyer.quantity_mt <= 0 or seller.quantity_mt <= 0 or seller.quantity_mt < buyer.quantity_mt:
            return result
        score += 15
    else:
        result["missing"].append("quantity")
    if buyer.company_verified and seller.company_verified:
        score += 15
    else:
        result["missing"].append("corporate_verification")
    if not (buyer.contact_consent and seller.contact_consent):
        result["missing"].append("mutual_consent")
    result["missing"].append("signed_brokerage_agreement")
    result.update(score=score, status="REVIEW_REQUIRED")
    return result

def shortlist(buyers: list[TradeIntent], sellers: list[TradeIntent]) -> list[dict]:
    results = [match(b, s) for b in buyers for s in sellers]
    return sorted((r for r in results if r["status"] != "INCOMPATIBLE"),
                  key=lambda r: (-r["score"], r["buyer_id"], r["seller_id"]))
