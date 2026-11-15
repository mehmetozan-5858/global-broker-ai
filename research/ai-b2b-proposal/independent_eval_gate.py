"""Independent evaluation evidence gate — offline, research only.

No synthetic regression data may be passed off as independent validation.
The output is NEVER authorization for commercial acceptance or production.
"""
import hashlib
import json
import math
from collections import Counter

LABELS = frozenset(("POSITIVE", "NEGATIVE", "REVIEW_SCOPE", "CONFLICT", "UNKNOWN"))
MIN_EVALUATION_CASES = 100  # Research evidence sufficiency floor, NOT a production target.
REQUIRED_STRATA = frozenset(("tr", "en", "multipage_pdf", "conditional", "counterparty"))

class EvaluationRejected(ValueError):
    pass

def _bound01(number):
    return max(0.0, min(1.0, number))

def wilson_upper(events, total, z=1.96):
    """95% two-sided Wilson score interval upper bound; no observations => None."""
    if total == 0:
        return None
    p = events / total
    denom = 1.0 + z*z/total
    center = p + z*z/(2*total)
    margin = z*math.sqrt(p*(1-p)/total + z*z/(4*total*total))
    return _bound01((center + margin) / denom)

def evaluate_external_gold(records, manifest):
    """Evaluate already-generated decisions versus independent gold labels.

    Input records must contain id, actual, expected, stratum, evidence_hash.
    The upstream harness must independently control gold labels and document bytes.
    """
    if not isinstance(records, list) or not isinstance(manifest, dict):
        raise EvaluationRejected("DATASET_OR_MANIFEST_INVALID")
    if not records:
        raise EvaluationRejected("EMPTY_EVALUATION")
    if manifest.get("origin") != "independent_authorized_human_gold":
        raise EvaluationRejected("INDEPENDENT_GOLD_NOT_ATTESTED")
    if manifest.get("previously_used_for_development") is not False:
        raise EvaluationRejected("CONTAMINATED_OR_UNKNOWN_SET")
    if manifest.get("frozen_before_execution") is not True:
        raise EvaluationRejected("DATASET_NOT_FROZEN")
    if not isinstance(manifest.get("reviewer_id"), str) or not manifest["reviewer_id"].strip():
        raise EvaluationRejected("REVIEWER_MISSING")
    expected_digest = manifest.get("sha256_canonical")
    if not isinstance(expected_digest, str) or len(expected_digest) != 64:
        raise EvaluationRejected("DATASET_DIGEST_INVALID")
    canonical = json.dumps(records, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != expected_digest:
        raise EvaluationRejected("DATASET_HASH_MISMATCH")
    seen = set()
    group = Counter()
    counts = Counter()
    for row in records:
        if not isinstance(row, dict):
            raise EvaluationRejected("RECORD_NOT_OBJECT")
        identifier = row.get("id")
        if not isinstance(identifier, str) or not identifier.strip() or identifier in seen:
            raise EvaluationRejected("CASE_ID_INVALID_OR_DUPLICATE")
        seen.add(identifier)
        actual, expected = row.get("actual"), row.get("expected")
        if actual not in LABELS or expected not in LABELS:
            raise EvaluationRejected("LABEL_INVALID")
        stratum = row.get("stratum")
        if not isinstance(stratum, str) or not stratum.strip():
            raise EvaluationRejected("STRATUM_MISSING")
        proof = row.get("evidence_hash")
        if not isinstance(proof, str) or len(proof) != 64 or any(c not in "0123456789abcdef" for c in proof):
            raise EvaluationRejected("EVIDENCE_HASH_INVALID")
        group[stratum] += 1
        counts["total"] += 1
        counts["exact"] += actual == expected
        counts["unsafe_positive"] += actual == "POSITIVE" and expected != "POSITIVE"
        counts["missed_positive"] += expected == "POSITIVE" and actual != "POSITIVE"
        counts["positive_gold"] += expected == "POSITIVE"
        counts["non_positive_gold"] += expected != "POSITIVE"
        counts["abstention"] += actual in ("REVIEW_SCOPE", "UNKNOWN", "CONFLICT")
    missing = sorted(REQUIRED_STRATA - set(group))
    adequate = counts["total"] >= MIN_EVALUATION_CASES and not missing and counts["positive_gold"] and counts["non_positive_gold"]
    return {
        "status": "RESEARCH_EVIDENCE_INCOMPLETE" if not adequate else "RESEARCH_EVIDENCE_MEASURED",
        "commercial_approval": False,
        "production_ready": False,
        "total": counts["total"],
        "exact": counts["exact"],
        "unsafe_positive": counts["unsafe_positive"],
        "missed_positive": counts["missed_positive"],
        "abstention": counts["abstention"],
        "positive_gold": counts["positive_gold"],
        "non_positive_gold": counts["non_positive_gold"],
        "unsafe_positive_rate": (counts["unsafe_positive"] / counts["non_positive_gold"] if counts["non_positive_gold"] else None),
        "unsafe_positive_95pct_upper": wilson_upper(counts["unsafe_positive"], counts["non_positive_gold"]),
        "missed_positive_rate": (counts["missed_positive"] / counts["positive_gold"] if counts["positive_gold"] else None),
        "missed_positive_95pct_upper": wilson_upper(counts["missed_positive"], counts["positive_gold"]),
        "strata": dict(group),
        "missing_strata": missing,
        "real_world_source_authenticity_verified": False,
    }
