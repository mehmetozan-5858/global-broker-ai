import unittest
from pathlib import Path

from src.admin_recovery import can_grant_admin, evaluate_enrollment

ROOT = Path(__file__).resolve().parents[1]


class LaunchGates123Tests(unittest.TestCase):
    def test_admin_recovery_requires_both_channels_provider_and_aal2(self):
        record = {
            "email_verified_at": "2026-10-10T00:00:00Z",
            "phone_verified_at": "2026-10-10T00:01:00Z",
            "phone_factor_id": "factor-1",
            "sms_provider_verified": True,
            "enabled": True,
        }
        self.assertTrue(can_grant_admin(record))
        self.assertFalse(evaluate_enrollment(record, jwt_aal="aal1")["ready"])
        self.assertTrue(evaluate_enrollment(record, jwt_aal="aal2")["ready"])

    def test_admin_cannot_be_granted_without_sms_provider(self):
        record = {
            "email_verified_at": "x",
            "phone_verified_at": "y",
            "phone_factor_id": "factor-1",
            "sms_provider_verified": False,
            "enabled": True,
        }
        self.assertFalse(can_grant_admin(record))

    def test_database_migration_has_restrictive_aal2_and_trigger_guard(self):
        sql = (ROOT / "sql/admin_dual_channel_recovery.sql").read_text(encoding="utf-8")
        self.assertIn("as restrictive", sql)
        self.assertIn("auth.jwt()->>'aal'", sql)
        self.assertIn("admin_dual_channel_recovery_not_ready", sql)
        self.assertIn("sms_provider_verified is true", sql)

    def test_pages_deploy_runs_real_customer_smoke(self):
        workflow = (ROOT / ".github/workflows/deploy-mobile.yml").read_text(encoding="utf-8")
        self.assertIn("Live customer acceptance smoke test", workflow)
        self.assertIn("CUSTOMER_ACCEPTANCE_OK", workflow)
        self.assertIn("public customer feed contains a non-goods record", workflow)

    def test_shadow_scan_runs_all_three_priority_gulf_adapters(self):
        workflow = (ROOT / ".github/workflows/shadow-scan.yml").read_text(encoding="utf-8")
        self.assertIn("python -m src.saudi_etimad_feed", workflow)
        self.assertIn("python -m src.uae_mof_feed", workflow)
        self.assertIn("python -m src.qatar_monaqasat_feed", workflow)

    def test_launch_gate_includes_admin_dual_recovery(self):
        source = (ROOT / "src/launch_gate.py").read_text(encoding="utf-8")
        self.assertIn("GB_ADMIN_DUAL_RECOVERY_READY", source)
        self.assertIn("admin_dual_recovery_ready", source)


if __name__ == "__main__":
    unittest.main()
