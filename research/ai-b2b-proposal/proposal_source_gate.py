"""Fail-closed offline source integrity gate. Not a proof of real-world authenticity."""
import hashlib
from proposal_v9 import verify_v9

def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def verify_source_bound_v9(question, records, trusted_sources, **kwargs):
    """trusted_sources maps source_id to {company, lines, sha256, optional region}.
    The trusted snapshot must come from independent ingestion, not the model output.
    """
    blocked = {"decision": "REVIEW_SCOPE", "evidence": [], "review": [],
               "ignored": [], "commercial_approval": False, "automatic_offer": False,
               "source_integrity_verified": False, "real_world_authenticity_verified": False}
    if not isinstance(records, list) or not records or not isinstance(trusted_sources, dict):
        blocked["review"].append(("?", "SOURCE_INPUT_UNAVAILABLE"))
        return blocked
    safe = []
    for index, record in enumerate(records):
        tag = str(index + 1)
        if not isinstance(record, dict):
            blocked["review"].append((tag, "RECORD_INVALID"))
            continue
        line, source_id, claim = record.get("line"), record.get("source_id"), record.get("text")
        if not isinstance(line, str) or not line.strip() or not isinstance(source_id, str) or not source_id.strip():
            blocked["review"].append((tag, "SOURCE_REFERENCE_MISSING"))
            continue
        tag = source_id + ":" + line
        source = trusted_sources.get(source_id)
        if not isinstance(source, dict):
            blocked["review"].append((tag, "SOURCE_NOT_TRUSTED"))
            continue
        lines, digest, identity = source.get("lines"), source.get("sha256"), source.get("company")
        if not isinstance(lines, dict) or not lines or not isinstance(digest, str):
            blocked["review"].append((tag, "TRUSTED_SNAPSHOT_INVALID"))
            continue
        if not all(isinstance(k, str) and isinstance(v, str) for k,v in lines.items()):
            blocked["review"].append((tag, "TRUSTED_LINES_INVALID"))
            continue
        canonical = "".join(key + "\t" + lines[key] + "\n" for key in sorted(lines))
        if sha256_text(canonical) != digest:
            blocked["review"].append((tag, "SOURCE_HASH_MISMATCH"))
            continue
        if line not in lines or not isinstance(claim, str) or claim != lines[line]:
            blocked["review"].append((tag, "SOURCE_LINE_MISMATCH"))
            continue
        if not isinstance(identity, str) or not identity.strip():
            blocked["review"].append((tag, "TRUSTED_IDENTITY_MISSING"))
            continue
        if record.get("company") != identity:
            blocked["review"].append((tag, "COMPANY_SCOPE_MISMATCH"))
            continue
        region = kwargs.get("region")
        if region and (source.get("region") is None or source["region"] != record.get("region")):
            blocked["review"].append((tag, "TRUSTED_REGION_MISMATCH"))
            continue
        safe.append(record)
    if blocked["review"]:
        return blocked
    result = verify_v9(question, safe, **kwargs)
    result["source_integrity_verified"] = True
    result["real_world_authenticity_verified"] = False
    return result
