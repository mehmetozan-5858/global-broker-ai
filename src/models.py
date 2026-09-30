from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class Opportunity:
    source: str
    source_id: str
    title: str
    buyer: str = ""
    buyer_country: str = ""
    product_category: str = ""
    quantity: str = ""
    estimated_value: Optional[float] = None
    currency: str = ""
    deadline: str = ""
    source_url: str = ""
    buyer_verified: Optional[bool] = None
    supplier_status: str = "pending"
    landed_cost_status: str = "pending"
    compliance_status: str = "pending"
    margin_status: str = "pending"
    deal_score: int = 0

    def to_dict(self):
        return asdict(self)
