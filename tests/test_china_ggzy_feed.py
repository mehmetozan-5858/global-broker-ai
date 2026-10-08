import unittest
from unittest.mock import patch

from src.china_ggzy_feed import discover_candidates, is_goods_procurement, merge_payload, parse_detail


HOME_HTML = '''
<html><body>
<a href="/information/deal/html/a/370000/0201/20261008/abc.html">2026年高水平公共实验平台之显微红外光谱仪设备采购项目</a>
<a href="/information/deal/html/a/420000/0101/20261008/def.html">某项目全过程咨询服务采购</a>
<a href="/other/ignore.html">设备采购</a>
</body></html>
'''

DETAIL_HTML = '''
<html><head><title>显微红外光谱仪设备采购项目</title></head><body>
<div>项目编号：SD-2026-1008</div>
<div>采购人：山东省教育发展服务中心</div>
<div>预算金额：人民币 4200000 元</div>
<div>投标截止时间：2026年11月06日 09:30</div>
<div>所在地区：山东省</div>
<h3>采购需求</h3>
<div>显微红外光谱仪设备 2 套，要求具备高灵敏度检测能力及配套数据处理系统。</div>
<h3>投标人资格要求</h3>
<div>依法注册并具有履约能力。</div>
</body></html>
'''


class ChinaGgzyFeedTests(unittest.TestCase):
    def test_goods_procurement_requires_procurement_and_goods_signal(self):
        self.assertTrue(is_goods_procurement("实验室设备采购项目"))
        self.assertFalse(is_goods_procurement("咨询服务采购项目"))
        self.assertFalse(is_goods_procurement("实验室设备升级项目"))

    def test_discover_candidates_filters_non_goods_and_non_deal_links(self):
        rows = discover_candidates(HOME_HTML)
        self.assertEqual(len(rows), 1)
        self.assertIn("光谱仪", rows[0]["title"])
        self.assertTrue(rows[0]["url"].startswith("https://www.ggzy.gov.cn/information/deal/html/"))

    def test_parse_detail_extracts_source_backed_fields(self):
        item = parse_detail(
            "https://www.ggzy.gov.cn/information/deal/html/a/370000/0201/20261008/abc.html",
            "2026年高水平公共实验平台之显微红外光谱仪设备采购项目",
            DETAIL_HTML,
        )
        self.assertIsNotNone(item)
        self.assertEqual(item["buyer-name"], "山东省教育发展服务中心")
        self.assertIn("4200000", item["estimated_value"])
        self.assertIn("2026年11月06日", item["deadline"])
        self.assertIn("显微红外光谱仪", item["technical-specification"])
        self.assertFalse(item["buyer_verified"])
        self.assertEqual(item["market_region"], "Çin / Doğu Asya")

    def test_detail_without_content_is_rejected(self):
        item = parse_detail(
            "https://www.ggzy.gov.cn/information/deal/html/a/1.html",
            "设备采购项目",
            "<html><body>短</body></html>",
        )
        self.assertIsNone(item)

    @patch("src.china_ggzy_feed.collect")
    def test_merge_adds_official_fallback_item(self, mocked):
        mocked.return_value = ([{"id": "ggzy:1", "source_url": "https://www.ggzy.gov.cn/information/deal/html/a/1.html"}], {"status": "ok"})
        out = merge_payload({"opportunities": []})
        self.assertEqual(len(out["opportunities"]), 1)
        self.assertEqual(out["china_ggzy_feed"]["goods_opportunities_added"], 1)

    @patch("src.china_ggzy_feed.collect")
    def test_merge_deduplicates_source_url(self, mocked):
        url = "https://www.ggzy.gov.cn/information/deal/html/a/1.html"
        mocked.return_value = ([{"id": "ggzy:1", "source_url": url}], {"status": "ok"})
        out = merge_payload({"opportunities": [{"id": "existing", "source_url": url}]})
        self.assertEqual(len(out["opportunities"]), 1)
        self.assertEqual(out["china_ggzy_feed"]["goods_opportunities_added"], 0)


if __name__ == "__main__":
    unittest.main()
