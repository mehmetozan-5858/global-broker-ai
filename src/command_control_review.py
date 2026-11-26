"""Data-only adapter from Broker launch checks to the shared review queue.

No network calls occur unless the operator explicitly invokes submit_review.
Operator-reported checks never authorize brokerage or release.
"""
from __future__ import annotations
import hashlib
import json
import re
import urllib.request
from .launch_readiness_report import CATEGORIES

ENDPOINT = "https://www.aivisibilityworks.com/api/command-control"
REQUIRED = tuple(dict.fromkeys(key for keys in CATEGORIES.values() for key in keys)) + (
    "technical_annexes_reviewed", "spreadsheet_formulas_reviewed", "source_revision_verified"
)

def build_review(payload: dict, source_sha: str, tenant_id: str = "internal") -> dict:
    if not isinstance(payload, dict) or not re.fullmatch(r"[a-f0-9]{40}", source_sha or ""):
        raise ValueError("invalid-source-evidence")
    if not isinstance(tenant_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", tenant_id):
        raise ValueError("invalid-tenant")
    gate = payload.get("launch_gate")
    checks = gate.get("checks") if isinstance(gate, dict) else None
    checks = checks if isinstance(checks, dict) else {}
    gates = [{"id": key, "status": "verified" if checks.get(key) is True else
              "blocked" if checks.get(key) is False else "unknown"} for key in REQUIRED]
    fingerprint = hashlib.sha256(json.dumps([tenant_id, source_sha, gates], sort_keys=True).encode()).hexdigest()[:32]
    task = {"id": "broker-" + fingerprint, "tenantId": tenant_id,
            "project": "global-broker-ai", "action": "acceptance.review"}
    return {"enqueue": {"operation": "enqueue", "task": task},
            "review": {"operation": "review", "taskId": task["id"], "gates": gates},
            "sourceSha": source_sha, "independentlyVerified": False,
            "releaseAuthorized": False}

def submit_review(plan: dict, token: str, *, enabled: bool = False, transport=None) -> dict:
    if enabled is not True:
        return {"ok": False, "reason": "submission-disabled"}
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]{43}", token):
        return {"ok": False, "reason": "agent-token-required"}
    # Recheck the plan, including project/scope and bounded fixed acceptance IDs.
    try:
        task = plan["enqueue"]["task"]
        gates = plan["review"]["gates"]
        if (set(plan["enqueue"]) != {"operation", "task"} or plan["enqueue"]["operation"] != "enqueue" or
            set(task) != {"id", "tenantId", "project", "action"} or task["project"] != "global-broker-ai" or
            task["action"] != "acceptance.review" or not re.fullmatch(r"broker-[a-f0-9]{32}", task["id"]) or
            not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", task["tenantId"]) or
            set(plan["review"]) != {"operation", "taskId", "gates"} or plan["review"]["operation"] != "review" or
            plan["review"]["taskId"] != task["id"] or len(gates) != len(REQUIRED) or
            [g["id"] for g in gates] != list(REQUIRED) or
            any(set(g) != {"id", "status"} or g["status"] not in {"verified", "blocked", "unknown"} for g in gates)):
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        return {"ok": False, "reason": "invalid-review-plan"}
    opener = transport or urllib.request.build_opener(_NoRedirect()).open
    for key in ("enqueue", "review"):
        request = urllib.request.Request(ENDPOINT, data=json.dumps(plan[key]).encode(), method="POST",
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
        try:
            with opener(request, timeout=10) as response:
                data = json.loads(response.read(65537))
                if response.status != 200 or data.get("ok") is not True or data.get("providerExecuted") is not False:
                    return {"ok": False, "reason": "review-not-confirmed"}
        except Exception:
            return {"ok": False, "reason": "review-transport-failed"}
    return {"ok": True, "state": "review-recorded", "releaseAuthorized": False}

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
