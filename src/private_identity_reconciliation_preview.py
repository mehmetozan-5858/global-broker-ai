"""Read-only reconciliation proposal for duplicated private opportunity IDs.

Never mutate the original rows, rekey an existing customer request or publish
private opportunity/source identities. A proposed ID is NOT a migration plan.
"""
import hashlib
import json

def analyze_collision_rekey(rows, referenced_ids=None):
    if not isinstance(rows,list):
        return {"safe_to_apply":False,"reason":"invalid-input"}
    by_id={}
    for row in rows:
        if not isinstance(row,dict):
            return {"safe_to_apply":False,"reason":"invalid-row"}
        old=str(row.get("opportunity_id") or row.get("id") or "").strip()
        source=str(row.get("source") or row.get("source_name") or "").strip()
        if not old or not source:
            return {"safe_to_apply":False,"reason":"missing-provenance"}
        by_id.setdefault(old,[]).append(source)
    duplicates={k:v for k,v in by_id.items() if len(v)>1}
    source_collisions=sum(1 for sources in duplicates.values() if len(set(sources))>1)
    repeated_same_source=sum(1 for sources in duplicates.values() if len(set(sources))==1)
    # Linked customer introductions/requests may use old IDs; never expose
    # identifiers or infer that an unprovided reference snapshot is empty.
    reference_snapshot_verified=isinstance(referenced_ids,(set,list,tuple))
    referenced_collision_groups=None
    if reference_snapshot_verified:
        reference_ids=set(str(x) for x in referenced_ids)
        referenced_collision_groups=sum(1 for key in duplicates if key in reference_ids)
    # Not enough to make a durable rekey decision: lot, revision and references
    # must be examined separately from source names.
    return {"safe_to_apply":False,"reason":"requires-reference-and-lot-reconciliation",
            "duplicated_identity_groups":len(duplicates),
            "cross_source_groups":source_collisions,
            "same_source_groups":repeated_same_source,
            "requires_manual_reference_review":bool(duplicates),
            "reference_snapshot_verified":reference_snapshot_verified,
            "referenced_collision_groups":referenced_collision_groups}

def draft_namespaced_identifier(*,source_key,notice_id,lot_id=None):
    """Preview only: deterministic candidate, never write as existing ID."""
    if any(not isinstance(x,str) or not x.strip() for x in [source_key,notice_id]):
        return None
    # Distinguish lots only when separately verified. Never infer lot 1.
    if lot_id is not None and (not isinstance(lot_id,str) or not lot_id.strip()):
        return None
    token=json.dumps([source_key.strip(),notice_id.strip(),lot_id],ensure_ascii=False,separators=(",",":"))
    return "gb_v2_"+hashlib.sha256(token.encode("utf-8")).hexdigest()[:40]
