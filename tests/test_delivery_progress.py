import copy
import json
import unittest
from pathlib import Path

from src.delivery_progress import build, public_summary

ROOT = Path(__file__).resolve().parents[1]


class DeliveryProgressTests(unittest.TestCase):
    def setUp(self):
        self.ledger = json.loads((ROOT / "docs/delivery-progress.json").read_text())
        for p in self.ledger["packages"]:
            p["status"] = "pending"
            p["evidence"] = {}

    def test_no_credit_for_written_or_tested_only_package(self):
        self.ledger["packages"][0].update(status="in_progress", evidence={"tests": "local tests"})
        self.assertEqual(build(self.ledger)["surfaces"]["web"]["current"], 70)
        self.assertEqual(build(self.ledger)["surfaces"]["app"]["current"], 65)

    def test_completion_needs_all_three_evidence_types(self):
        p = self.ledger["packages"][0]
        p.update(status="complete", evidence={"tests": "passed", "deployment": "READY"})
        with self.assertRaises(ValueError):
            build(self.ledger)
        p["evidence"]["live_verification"] = "checked"
        result = build(self.ledger)
        self.assertEqual(result["surfaces"]["web"]["current"], 72)
        self.assertEqual(result["surfaces"]["app"]["current"], 67)
        self.assertEqual(result["next_package"], "P2")
        p["status"] = "blocked"
        self.assertEqual(build(self.ledger)["surfaces"]["web"]["current"], 70)

    def test_scope_must_sum_to_100(self):
        self.ledger["packages"][0]["points"]["app"] += 1
        with self.assertRaises(ValueError):
            build(self.ledger)

    def test_duplicate_ids_rejected(self):
        self.ledger["packages"].append(copy.deepcopy(self.ledger["packages"][0]))
        with self.assertRaises(ValueError):
            build(self.ledger)

    def test_step_progress_never_awards_package_points_or_exposes_private_evidence(self):
        self.ledger['packages'][0]['steps'] = [{'id': 'fixture', 'title': 'Fixture software', 'category': 'software', 'status': 'complete',
            'evidence': {'tests': 'PRIVATE_SENTINEL', 'deployment': 'READY', 'live_verification': 'checked'}}]
        result = public_summary(self.ledger)
        self.assertEqual(result['surfaces']['web']['current'], 70)
        self.assertNotIn('PRIVATE_SENTINEL', json.dumps(result))
        self.assertGreater(result['step_summary']['software']['complete'], 0)

    def test_completed_step_requires_all_evidence_and_duplicate_ids_are_rejected(self):
        step = {'id': 'fixture', 'title': 'Fixture', 'category': 'software', 'status': 'complete', 'evidence': {'tests': 'local only'}}
        self.ledger['packages'][0]['steps'] = [step]
        with self.assertRaises(ValueError):
            build(self.ledger)
        step['status'] = 'pending'
        self.ledger['packages'][0]['steps'].append(copy.deepcopy(step))
        with self.assertRaises(ValueError):
            build(self.ledger)
