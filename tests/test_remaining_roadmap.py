import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from src.agent_center import build as build_agent_center
from src.billing_gate import decide as billing_decide, payment_record
from src.commercial_feasibility import assess as assess_feasibility
from src.commercial_terms import analyze as analyze_terms
from src.gulf_sources import annotate_payload
from src.launch_gate import evaluate as evaluate_launch
from src.offer_risk_gate import evaluate as evaluate_offer
from src.remaining_pipeline import process
from src.supplier_research import prepare as prepare_supplier

ROOT=Path(__file__).resolve().parents[1]


class RemainingRoadmapTests(unittest.TestCase):
    def test_a4_does_not_mislabel_links_as_live_ingestion(self):
        payload={}
        annotate_payload(payload)
        self.assertFalse(payload["gulf_sources"]["live_ingestion_verified"])
        self.assertTrue(any(x["name"]=="Etimad" for x in payload["gulf_sources"]["sources"]))
        self.assertTrue(all(x["live_ingestion"] is False for x in payload["gulf_sources"]["sources"]))

    def test_a5_missing_terms_remain_missing(self):
        item={"delivery_terms":"CIF"}
        result=analyze_terms(item)
        self.assertEqual(result["terms"]["delivery"]["status"],"source_backed")
        self.assertEqual(result["terms"]["payment"]["status"],"missing")
        self.assertIn("bond",result["missing"])

    def test_a6_supplier_is_not_fabricated(self):
        item={"title_original":"Industrial pump","specification_analysis":{"supplier_sourcing_ready":True}}
        result=prepare_supplier(item)
        self.assertTrue(result["dossier_ready"])
        self.assertEqual(result["candidate_suppliers"],[])
        self.assertEqual(result["verified_supplier_count"],0)

    def test_a7_no_margin_without_real_inputs(self):
        result=assess_feasibility({"quantity":"100","currency":"USD"})
        self.assertFalse(result["calculation_ready"])
        self.assertFalse(result["margin_claim_allowed"])
        self.assertIn("unit_price",result["missing_inputs"])
        self.assertIn("freight",result["missing_inputs"])

    def test_a8_external_actions_always_fail_closed(self):
        item={"export_goods_review":{"status":"goods_candidate"},"buyer_verification":{"verified":True},"specification_analysis":{"supplier_sourcing_ready":True},"supplier_research":{"verified_supplier_count":1},"commercial_feasibility":{"calculation_ready":True,"facts":{"destination":{"value":"Riyadh"}}}}
        result=evaluate_offer(item)
        self.assertTrue(result["draft_offer_ready"])
        self.assertFalse(result["external_action_authorized"])
        self.assertIn("submit_bid",result["forbidden_actions"])

    def test_a9_agent_center_stays_shadow(self):
        payload={"opportunities":[{"export_goods_review":{"status":"goods_candidate"}}]}
        result=build_agent_center(payload)
        self.assertEqual(result["mode"],"shadow")
        self.assertFalse(result["external_actions_enabled"])
        self.assertTrue(result["policy"]["human_approval_required"])

    def test_a10_launch_gate_requires_every_external_gate(self):
        payload={"opportunities":[{"export_goods_review":{"status":"goods_candidate"}}],"field_evidence_summary":{},"specification_analysis":{},"commercial_feasibility_summary":{}}
        with patch.dict(os.environ,{},clear=True):
            result=evaluate_launch(payload)
        self.assertFalse(result["launch_ready"])
        self.assertIn("server_side_auth_configured",result["blockers"])
        self.assertIn("custom_domain_verified",result["blockers"])

    def test_orchestrator_runs_all_remaining_stages(self):
        payload={"opportunities":[{"title_original":"Pump","export_goods_review":{"status":"goods_candidate"},"specification_analysis":{"supplier_sourcing_ready":False}}]}
        process(payload)
        for key in ("gulf_sources","commercial_terms_summary","supplier_research_summary","commercial_feasibility_summary","offer_risk_summary","agent_center","deal_lifecycle_summary","launch_gate"):
            self.assertIn(key,payload)
        self.assertEqual(payload["deal_lifecycle_summary"]["case_count"],0)
        self.assertFalse(payload["deal_lifecycle_summary"]["external_actions_enabled"])

    def test_w3_account_page_uses_real_auth_and_has_no_admin_self_assignment(self):
        html=(ROOT/"web/account.html").read_text(encoding="utf-8")
        self.assertIn("/auth/v1/token?grant_type=password",html)
        self.assertIn("/auth/v1/signup",html)
        self.assertIn("/auth/v1/recover",html)
        self.assertNotIn("role:'admin'",html)
        self.assertNotIn('role:"admin"',html)

    def test_w4_billing_stays_closed_until_all_business_gates_pass(self):
        d=billing_decide(provider_verified=False,legal_entity_verified=False,invoice_flow_verified=False,refund_terms_reviewed=False,customer_terms_accepted=False)
        self.assertFalse(d.payment_allowed)
        self.assertIn("payment_provider",d.blockers)
        self.assertEqual(payment_record(provider_reference=None,amount=None,currency=None,provider_verified=False)["status"],"unconfirmed")

    def test_w5_vercel_has_clean_routes_and_security_headers(self):
        cfg=json.loads((ROOT/"vercel.json").read_text(encoding="utf-8"))
        routes={x["source"]:x["destination"] for x in cfg["rewrites"]}
        self.assertEqual(routes["/"],"/web/website-mobile.html")
        self.assertEqual(routes["/account"],"/web/account.html")
        all_headers={h["key"] for block in cfg["headers"] for h in block["headers"]}
        self.assertIn("X-Content-Type-Options",all_headers)
        self.assertIn("X-Frame-Options",all_headers)

    def test_shadow_scan_integrates_remaining_pipeline(self):
        workflow=(ROOT/".github/workflows/shadow-scan.yml").read_text(encoding="utf-8")
        self.assertIn('python -m src.remaining_pipeline "$NEXT"',workflow)
        self.assertIn("unexpected production launch",workflow)


if __name__=="__main__":
    unittest.main()
