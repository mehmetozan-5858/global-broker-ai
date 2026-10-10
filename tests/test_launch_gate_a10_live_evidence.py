import os
import unittest
from unittest.mock import patch

from src.launch_gate import evaluate


class LaunchGateA10LiveEvidenceTests(unittest.TestCase):
    def _payload(self, gulf_live: bool):
        return {
            "opportunities": [{"export_goods_review": {"status": "goods_candidate"}}],
            "field_evidence_summary": {"opportunities": 1},
            "specification_analysis": {"analyzed": 1},
            "commercial_feasibility_summary": {"opportunities": 1},
            "gulf_sources": {
                "priority_gulf_live_ingestion_verified": gulf_live,
                "live_ingestion_verified": gulf_live,
            },
        }

    def _all_external_flags(self):
        return {
            "GB_AUTH_READY": "true",
            "GB_PRIVATE_STORAGE_READY": "true",
            "GB_ADMIN_DUAL_RECOVERY_READY": "true",
            "GB_LEGAL_REVIEWED": "true",
            "GB_PAYMENT_TESTED": "true",
            "GB_BUSINESS_CONTACT_VERIFIED": "true",
            "GB_CUSTOM_DOMAIN_VERIFIED": "true",
            "GB_GULF_LIVE_VERIFIED": "true",
            "GB_CUSTOMER_ACCEPTANCE_TESTED": "true",
        }

    def test_env_flag_cannot_fake_missing_current_scan_gulf_evidence(self):
        with patch.dict(os.environ, self._all_external_flags(), clear=True):
            result = evaluate(self._payload(False))
        self.assertFalse(result["launch_ready"])
        self.assertFalse(result["checks"]["gulf_current_scan_verified"])
        self.assertFalse(result["checks"]["gulf_live_ingestion_verified"])
        self.assertIn("gulf_current_scan_verified", result["blockers"])

    def test_current_scan_still_requires_explicit_launch_attestation(self):
        flags = self._all_external_flags()
        flags.pop("GB_GULF_LIVE_VERIFIED")
        with patch.dict(os.environ, flags, clear=True):
            result = evaluate(self._payload(True))
        self.assertFalse(result["launch_ready"])
        self.assertTrue(result["checks"]["gulf_current_scan_verified"])
        self.assertFalse(result["checks"]["gulf_live_ingestion_verified"])

    def test_all_gates_can_open_only_with_live_evidence_and_attestation(self):
        with patch.dict(os.environ, self._all_external_flags(), clear=True):
            result = evaluate(self._payload(True))
        self.assertTrue(result["launch_ready"])
        self.assertEqual(result["mode"], "production")
        self.assertTrue(result["gulf_verification"]["requires_both"])


if __name__ == "__main__":
    unittest.main()
