"""Regression: technical acceptance must fail closed on unresolved TED evidence."""
import json
from pathlib import Path
import unittest
from scripts.ted_technical_acceptance_gate import decision, REQUIRED_EVIDENCE
from scripts.audit_ted_tank_capacity_envelopes import SOURCE


class TechnicalGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = json.loads(SOURCE.read_text(encoding="utf-8"))

    def test_current_evidence_is_critical_and_blocked(self):
        out = decision(self.matrix)
        self.assertEqual(out["status"], "BLOCKED")
        self.assertEqual(out["risk_level"], "critical")
        self.assertEqual(out["sites_with_drawing_conflict"], ["Slavkov u Brna", "Veselí nad Moravou"])
        self.assertEqual(out["sites_with_specification_conflict"], ["Slavkov u Brna"])
        self.assertEqual(out["affected_new_tanks_in_drawing_conflict"], 5)
        self.assertEqual(out["evidence_flags_confirmed"], 0)
        self.assertEqual(out["evidence_flags_required"], 7)
        self.assertFalse(out["technical_approval"])
        self.assertFalse(out["commercial_approval"])
        self.assertFalse(out["deployment_approval"])

    def test_claimed_external_evidence_cannot_override_geometry(self):
        out = decision(self.matrix, {name: True for name in REQUIRED_EVIDENCE})
        self.assertEqual(out["status"], "BLOCKED")
        self.assertIn("specification_capacity_envelope_conflict", out["blockers"])
        self.assertIn("drawing_capacity_envelope_conflict", out["blockers"])
        self.assertFalse(out["technical_approval"])

    def test_no_partial_evidence_is_treated_as_verified(self):
        out = decision(self.matrix, {"independent_engineering_approval": "yes"})
        self.assertEqual(out["evidence_flags_confirmed"], 0)
        self.assertIn("missing_independent_engineering_approval", out["blockers"])


if __name__ == "__main__":
    unittest.main()
