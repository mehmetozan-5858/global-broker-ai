def deal_score(o) -> int:
    """Product-neutral pre-trade score. Unknown data is not treated as positive."""
    score = 10
    if o.title: score += 10
    if o.buyer: score += 15
    if o.buyer_country: score += 10
    if o.estimated_value: score += 15
    if o.deadline: score += 10
    if o.buyer_verified is True: score += 15
    if o.supplier_status == "verified": score += 10
    if o.compliance_status == "clear": score += 10
    if o.margin_status == "positive": score += 5
    return min(100, score)
