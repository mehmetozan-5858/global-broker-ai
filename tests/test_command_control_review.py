import io
import json
import unittest
from src.command_control_review import build_review, submit_review, REQUIRED, ENDPOINT

class CommandReviewTests(unittest.TestCase):
    def test_missing_gate_evidence_stays_unknown_and_ids_are_deterministic(self):
        plan = build_review({}, "a" * 40)
        self.assertTrue(all(g["status"] == "unknown" for g in plan["review"]["gates"]))
        self.assertEqual(plan, build_review({}, "a" * 40))
        self.assertNotEqual(plan["enqueue"], build_review({}, "b" * 40)["enqueue"])
        self.assertFalse(plan["releaseAuthorized"])

    def test_only_explicit_booleans_become_reported_pass_or_failure(self):
        checks = {REQUIRED[0]: True, REQUIRED[1]: False, REQUIRED[2]: "true"}
        gates = build_review({"launch_gate": {"checks": checks}}, "a" * 40)["review"]["gates"]
        self.assertEqual([g["status"] for g in gates[:3]], ["verified", "blocked", "unknown"])

    def test_submission_is_disabled_and_invalid_tokens_or_plans_never_call_transport(self):
        plan = build_review({}, "a" * 40)
        def forbidden(*args, **kwargs):
            self.fail("transport must not run")
        self.assertEqual(submit_review(plan, "", transport=forbidden)["reason"], "submission-disabled")
        self.assertEqual(submit_review(plan, "", enabled=True, transport=forbidden)["reason"], "agent-token-required")
        plan["enqueue"]["task"]["project"] = "other"
        self.assertEqual(submit_review(plan, "abc." + "x" * 43, enabled=True, transport=forbidden)["reason"], "invalid-review-plan")

    def test_bounded_two_step_submission_targets_only_fixed_endpoint(self):
        calls = []
        class Response(io.BytesIO):
            status = 200
        def transport(req, **kwargs):
            calls.append((req.full_url, json.loads(req.data)))
            return Response(json.dumps({"ok": True, "providerExecuted": False}).encode())
        result = submit_review(build_review({}, "a" * 40), "abc." + "x" * 43, enabled=True, transport=transport)
        self.assertTrue(result["ok"])
        self.assertEqual([x[0] for x in calls], [ENDPOINT, ENDPOINT])
        self.assertEqual([x[1]["operation"] for x in calls], ["enqueue", "review"])
