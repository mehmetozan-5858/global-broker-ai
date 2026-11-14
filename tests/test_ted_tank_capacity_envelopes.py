"""Offline fail-closed regressions for drawing-derived capacity envelopes."""
import json
from copy import deepcopy
from pathlib import Path
import unittest

from scripts.audit_ted_tank_capacity_envelopes import SOURCE, audit


class TankCapacityEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.matrix = json.loads(SOURCE.read_text(encoding="utf-8"))

    def test_drawn_15kl_tanks_have_impossible_cylindrical_envelopes(self):
        result = audit(self.matrix)
        flagged = {x["site"]: x for x in result["rows"] if x["drawing_envelope_below_required_volume"]}
        self.assertEqual(set(flagged), {"Veselí nad Moravou", "Slavkov u Brna"})
        self.assertEqual(result["sites_with_impossible_envelope"], 2)
        self.assertEqual(result["tanks_in_impossible_envelopes"], 5)
        for row in flagged.values():
            self.assertEqual(row["required_each_l"], 15_000)
            self.assertEqual(row["outer_cylinder_upper_bound_each_l"], 13_572)
            self.assertGreater(row["deficit_each_l_if_impossible"], 1400)
            self.assertFalse(row["usable_volume_verified"])
        self.assertFalse(result["technical_approval"])
        self.assertFalse(result["commercial_approval"])

    def test_slavkov_is_impossible_even_at_specified_maximum_envelope(self):
        result = audit(self.matrix)
        flagged = [r for r in result["rows"] if r["spec_dimensional_envelope_below_required_volume"]]
        self.assertEqual({r["site"] for r in flagged}, {"Slavkov u Brna"})
        self.assertEqual(result["sites_impossible_under_spec_cylinder_envelope"], 1)
        self.assertEqual(result["tanks_impossible_under_spec_cylinder_envelope"], 3)
        self.assertEqual(flagged[0]["spec_max_outer_cylinder_upper_bound_each_l"], 14143)
        self.assertEqual(flagged[0]["minimum_ideal_cylinder_height_at_allowed_max_diameter_mm"], 3182)
        self.assertFalse(flagged[0]["usable_volume_verified"])

    def test_veseli_could_be_revised_inside_spec_but_drawn_design_is_too_short(self):
        result = audit(self.matrix)
        veseli = next(r for r in result["rows"] if r["site"] == "Veselí nad Moravou")
        self.assertTrue(veseli["drawing_envelope_below_required_volume"])
        self.assertFalse(veseli["spec_dimensional_envelope_below_required_volume"])
        self.assertEqual(veseli["minimum_ideal_cylinder_height_at_drawn_diameter_mm"], 3316)

    def test_cannot_claim_capacity_verified(self):
        changed = deepcopy(self.matrix)
        changed["rows"][0]["capacity_verified"] = True
        with self.assertRaises(ValueError):
            audit(changed)

    def test_cannot_change_approval_or_scope(self):
        changed = deepcopy(self.matrix)
        changed["technical_approval"] = True
        with self.assertRaises(ValueError):
            audit(changed)
        changed = deepcopy(self.matrix)
        changed["rows"][0]["count"] = 4
        with self.assertRaises(ValueError):
            audit(changed)

    def test_other_tanks_are_not_promoted_to_capacity_verified(self):
        result = audit(self.matrix)
        for row in result["rows"]:
            self.assertFalse(row["usable_volume_verified"])


if __name__ == "__main__":
    unittest.main()
