import unittest
from src.exportable_goods import classify

class ExportableGoodsTests(unittest.TestCase):
    def test_goods(self):
        self.assertEqual(classify({"title_original":"Supply and delivery of 25406 school desks","procurement_category":"Goods"})["status"],"goods_candidate")
    def test_service(self):
        self.assertEqual(classify({"title_original":"International materials engineer","procurement_category":"Consulting Services"})["status"],"exclude_service")
    def test_mixed(self):
        self.assertEqual(classify({"title_original":"Supply of pumps and drilling services"})["status"],"review_mixed")
    def test_unknown(self):
        self.assertEqual(classify({"title_original":"Project development phase 2"})["status"],"review_unknown")
    def test_goods_with_installation_requires_review(self):
        self.assertEqual(classify({"title_original":"Supply of equipment and engineering services","procurement_category":"Goods"})["status"],"review_mixed")

if __name__=="__main__":
    unittest.main()
