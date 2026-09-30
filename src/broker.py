from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import date
import json

@dataclass
class Opportunity:
    source: str
    buyer: str
    country: str
    product: str
    quantity: str = ""
    deadline: str = ""
    estimated_value_usd: float = 0
    buyer_verified: bool = False
    supplier_signal: int = 0      # 0-100
    margin_signal: int = 0        # 0-100

def clamp(v: float) -> int:
    return max(0, min(100, round(v)))

def deal_score(o: Opportunity) -> int:
    demand = 25 if o.product and o.buyer else 8
    buyer = 20 if o.buyer_verified else 6
    value = 15 if o.estimated_value_usd >= 500_000 else (10 if o.estimated_value_usd >= 100_000 else 5)
    supply = 15 * clamp(o.supplier_signal) / 100
    margin = 15 * clamp(o.margin_signal) / 100
    timing = 10 if o.deadline else 5
    return clamp(demand + buyer + value + supply + margin + timing)

def rank(opportunities):
    rows=[]
    for o in opportunities:
        row=asdict(o)
        row["deal_score"]=deal_score(o)
        rows.append(row)
    return sorted(rows,key=lambda x:x["deal_score"],reverse=True)

if __name__ == "__main__":
    demo=[
        Opportunity("shadow-demo","Demo Buyer","GB","Urea 46%", "10,000 MT", "", 3_000_000, True, 75, 70),
        Opportunity("shadow-demo","Demo Buyer 2","DE","Industrial raw material", "", "", 150_000, False, 60, 45),
    ]
    print(json.dumps(rank(demo),ensure_ascii=False,indent=2))
