import unittest
from src.matching import TradeIntent, match, shortlist

def trade(side, **kwargs):
    d=dict(id=side,side=side,product="crude sunflower oil",country="TR",quantity_mt=100,hs_code="1512",grade="A")
    d.update(kwargs)
    return TradeIntent(**d)

class TestMatching(unittest.TestCase):
    def test_valid_pair_requires_review(self):
        x=match(trade("BUY"),trade("SELL"))
        self.assertEqual(x["status"],"REVIEW_REQUIRED")
        self.assertFalse(x["can_reveal_contacts"])
    def test_product_conflict(self):
        self.assertEqual(match(trade("BUY"),trade("SELL",product="cement"))["status"],"INCOMPATIBLE")
    def test_hs_conflict(self):
        self.assertEqual(match(trade("BUY"),trade("SELL",hs_code="9999"))["status"],"INCOMPATIBLE")
    def test_grade_conflict(self):
        self.assertEqual(match(trade("BUY"),trade("SELL",grade="B"))["status"],"INCOMPATIBLE")
    def test_capacity_conflict(self):
        self.assertEqual(match(trade("BUY"),trade("SELL",quantity_mt=90))["status"],"INCOMPATIBLE")
    def test_consent_not_sufficient(self):
        x=match(trade("BUY",contact_consent=True,company_verified=True),trade("SELL",contact_consent=True,company_verified=True))
        self.assertFalse(x["can_reveal_contacts"])
    def test_shortlist(self):
        x=shortlist([trade("BUY")],[trade("SELL"),trade("SELL",id="bad",product="cement")])
        self.assertEqual(len(x),1)

if __name__=="__main__":
    unittest.main()
