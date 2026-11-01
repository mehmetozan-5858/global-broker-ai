"""Validate isolated annex audit evidence without upgrading the tender's approval.

Audit metadata is deliberately kept separate from ordinary extraction. The result
is suitable only for a review queue, never for sourcing or commercial release.
"""
import re

SHA256 = re.compile(r"^[0-9a-f]{64}$")
ALLOWED = {"doc", "docx", "pdf", "xlsx", "txt"}


def reconcile_annex_audit(extraction, audit):
    """Return privacy-safe evidence counts; fail closed on any inconsistency."""
    result = {
        "audit_evidence_valid": False,
        "audit_reviewed_count": 0,
        "audit_total_observed": None,
        "formula_review_required": True,
        "revision_review_required": True,
        "all_mandatory_requirements_reviewed": False,
        "supplier_sourcing_ready": False,
        "commercial_approval": False,
    }
    if not isinstance(extraction, dict) or not isinstance(audit, dict):
        return result
    inventory = extraction.get("attachment_inventory")
    if not isinstance(inventory, list) or not inventory:
        return result
    observed = extraction.get("attachment_candidates_observed")
    omitted = extraction.get("attachment_inventory_entries_omitted")
    if type(observed) is not int or observed != len(inventory) or type(omitted) is not int or omitted != 0:
        return result
    if any(not isinstance(x, dict) or x.get("status") not in {"parsed", "failed", "skipped", "unsupported"}
           for x in inventory):
        return result
    pending = [x for x in inventory if x["status"] != "parsed"]
    records = audit.get("audited_remaining")
    if not isinstance(records, list) or len(records) != len(pending):
        return result
    if audit.get("ordinary_reader_parsed") != len(inventory) - len(pending):
        return result
    if audit.get("ordinary_reader_limits_unchanged") is not True:
        return result
    formula = False
    for index, (original, record) in enumerate(zip(pending, records), 1):
        if not isinstance(record, dict) or record.get("index") != index or record.get("format") != original.get("kind"):
            return result
        if record.get("status") != "read_for_review" or not isinstance(record.get("sha256"), str) or not SHA256.fullmatch(record["sha256"]):
            return result
        if record["format"] not in ALLOWED or type(record.get("bytes")) is not int or not 0 < record["bytes"] <= 8 * 1024 * 1024:
            return result
        if type(record.get("text_chars")) is not int or record["text_chars"] < 20 or record.get("text_truncated") is not False:
            return result
        if type(record.get("formula_cells")) is not int or record["formula_cells"] < 0:
            return result
        if record["format"] == "xlsx":
            if record.get("formula_evaluation_performed") is not False or record.get("formula_approval") is not False:
                return result
            if record.get("formula_review_required") is not (record["formula_cells"] > 0):
                return result
        elif record["formula_cells"] != 0:
            return result
        formula |= record["formula_cells"] > 0
    if audit.get("commercial_approval") is not False or audit.get("supplier_sourcing_ready") is not False:
        return result
    if audit.get("applicable_revision_selected") is not False or audit.get("all_mandatory_requirements_reviewed") is not False:
        return result
    result.update(audit_evidence_valid=True, audit_reviewed_count=len(records),
                  audit_total_observed=observed, formula_review_required=formula,
                  revision_review_required=True)
    return result
