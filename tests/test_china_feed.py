import unittest
from unittest.mock import patch

from src.china_feed import classify_goods, discover_notice_urls, merge_payload, parse_notice


INDEX_HTML = '''
<html><body>
<a href="/cggg/dfgg/gkzb/202610/t20261008_12345678.htm">设备采购</a>
<a href="https://www.ccgp.gov.cn/cggg/zygg/gkzb/202610/t20261008_87654321.htm">中央设备</a>
<a href="/other/page.htm">ignore</a>
</body></html>
'''

NOTICE_HTML = '''
<html><head><title>精密检测设备采购项目公开招标公告_中国政府采购网</title></head><body>
<div>项目名称：精密检测设备采购项目</div>
<div>采购方式：公开招标</div>
<div>预算金额：4,700,000.00元</div>
<div>采购单位：重庆市计量质量检测研究院</div>
<div>行政区域：重庆市</div>
<div>提交投标文件截止时间：2026年11月10日 10:00</div>
<h3>采购需求：</h3>
<div>精密检测设备 2 套，技术要求符合 ISO 9001 相关质量体系要求。</div>
<div>合同履行期限：签订合同后60日内。</div>
<h3>二、申请人的资格要求：</h3>
<div>投标人应具备合法经营资格。</div>
<h3>三、获取招标文件：</h3>
</body></html>
'''

SERVICE_HTML = '''
<html><head><title>审计服务采购项目公开招标公告_中国政府采购网</title></head><body>
<div>项目名称：审计服务采购项目</div>
<div>采购需求：年度审计服务及咨询服务。</div>
</body></html>
'''


class ChinaFeedTests(unittest.TestCase):
    def test_discover_only_official_open_tender_links(self):
        urls = discover_notice_urls(INDEX_HTML, "https://www.ccgp.gov.cn/cggg/dfgg/gkzb/index.htm")
        self.assertEqual(len(urls), 2)
        self.assertTrue(all(url.startswith("https://www.ccgp.gov.cn/") for url in urls))

    def test_goods_notice_extracts_buyer_budget_deadline_and_need(self):
        out = parse_notice(
            "https://www.ccgp.gov.cn/cggg/dfgg/gkzb/202610/t20261008_12345678.htm",
            NOTICE_HTML,
        )
        self.assertIsNotNone(out)
        self.assertEqual(out["buyer-name"], "重庆市计量质量检测研究院")
        self.assertIn("4,700,000.00", out["estimated_value"])
        self.assertIn("2026年11月10日", out["deadline"])
        self.assertIn("精密检测设备", out["technical-specification"])
        self.assertEqual(out["market_region"], "Çin / Doğu Asya")
        self.assertFalse(out["buyer_verified"])

    def test_service_only_notice_is_filtered(self):
        out = parse_notice(
            "https://www.ccgp.gov.cn/cggg/dfgg/gkzb/202610/t20261008_99999999.htm",
            SERVICE_HTML,
        )
        self.assertIsNone(out)

    def test_goods_classifier_requires_goods_evidence(self):
        ok, reason = classify_goods("医疗设备采购", "设备一批")
        self.assertTrue(ok)
        self.assertIn("goods_keyword", reason)
        ok, reason = classify_goods("咨询服务", "年度咨询服务")
        self.assertFalse(ok)
        self.assertIn("service_or_works", reason)

    @patch("src.china_feed.collect_china_opportunities")
    def test_merge_deduplicates_by_id(self, mocked):
        mocked.return_value = ([{"id": "ccgp:1", "market_region": "Çin / Doğu Asya"}], {"status": "ok"})
        payload = {"opportunities": [{"id": "ccgp:1"}]}
        out = merge_payload(payload)
        self.assertEqual(len(out["opportunities"]), 1)
        self.assertEqual(out["china_feed"]["status"], "ok")

    @patch("src.china_feed.collect_china_opportunities")
    def test_merge_adds_china_opportunity(self, mocked):
        mocked.return_value = ([{"id": "ccgp:2", "market_region": "Çin / Doğu Asya"}], {"status": "ok"})
        out = merge_payload({"opportunities": []})
        self.assertEqual(out["opportunities"][0]["id"], "ccgp:2")


if __name__ == "__main__":
    unittest.main()
