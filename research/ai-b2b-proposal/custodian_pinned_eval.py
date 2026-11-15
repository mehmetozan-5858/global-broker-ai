"""Extra offline custodian boundary for independent evaluation.

The digest and reviewer allowlist MUST be supplied out-of-band by a trusted
custodian. In-repository examples or values supplied by the evaluated model
DO NOT establish independence or authenticity. Research-only, no production.
"""
import hashlib
import hmac
import json
import re
from independent_eval_gate import EvaluationRejected, evaluate_external_gold

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REVIEWER = re.compile(r"^[A-Za-z0-9_.@:-]{3,128}$")


def canonical_manifest_bytes(manifest):
    if not isinstance(manifest, dict):
        raise EvaluationRejected("CUSTODIAN_MANIFEST_INVALID")
    try:
        raw = json.dumps(manifest, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False)
        return raw.encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise EvaluationRejected("CUSTODIAN_MANIFEST_UNSERIALIZABLE") from exc


def evaluate_custodian_pinned(records, manifest, *, trusted_manifest_sha256=None,
                              trusted_reviewers=None):
    """Require a separately controlled manifest digest and reviewer allowlist.

    All supplied values are untrusted unless the CALLER obtains trusted pins
    from a separate approved authority; this function cannot prove that.
    """
    if not isinstance(trusted_manifest_sha256, str) or not _SHA256.fullmatch(trusted_manifest_sha256):
        raise EvaluationRejected("OUT_OF_BAND_MANIFEST_PIN_MISSING")
    if not isinstance(trusted_reviewers, (tuple, frozenset)) or not trusted_reviewers:
        raise EvaluationRejected("CUSTODIAN_REVIEWER_ALLOWLIST_MISSING")
    if not all(isinstance(x, str) and _REVIEWER.fullmatch(x) for x in trusted_reviewers):
        raise EvaluationRejected("CUSTODIAN_REVIEWER_ALLOWLIST_INVALID")
    digest = hashlib.sha256(canonical_manifest_bytes(manifest)).hexdigest()
    if not hmac.compare_digest(digest, trusted_manifest_sha256):
        raise EvaluationRejected("CUSTODIAN_MANIFEST_PIN_MISMATCH")
    reviewer = manifest.get("reviewer_id")
    if reviewer not in trusted_reviewers:
        raise EvaluationRejected("CUSTODIAN_REVIEWER_NOT_AUTHORIZED")
    result = evaluate_external_gold(records, manifest)
    result["out_of_band_pin_matched"] = True
    result["trusted_custodian_identity_verified"] = False
    result["production_ready"] = False
    result["commercial_approval"] = False
    return result
