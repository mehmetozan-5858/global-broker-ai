"""Review-only classifier for TED official response and daily XML fallback evidence.

Does not fetch anything, bypass WAF, or mark an opportunity accepted.
"""
import re


def classify_response(record):
    status = record.get("http_status")
    kind = record.get("body_kind")
    challenge = record.get("challenge_indicator") is True
    if status == 202:
        return "pending_or_challenged_not_document"
    if challenge:
        return "challenge_not_document"
    if status != 200:
        return "http_not_accepted"
    if kind not in {"xml", "pdf"}:
        return "not_official_document"
    if record.get("accepted_as_notice") is not True:
        return "unverified_notice"
    return "verified_notice_response"


def verify_bulk_manifest(manifest, publication):
    """Verify metadata only. A matching manifest is NOT proof XML was parsed."""
    if not re.fullmatch(r"[0-9]{1,8}-[0-9]{4}", publication):
        raise ValueError("invalid publication number")
    if not isinstance(manifest, dict):
        raise ValueError("missing bulk manifest")
    if manifest.get("source_channel") != "official_daily_xml_package":
        raise ValueError("untrusted source channel")
    if not re.fullmatch(r"[a-f0-9]{64}", str(manifest.get("package_sha256", ""))):
        raise ValueError("missing package digest")
    if manifest.get("publication_number") != publication:
        raise ValueError("publication mismatch")
    if manifest.get("xml_parsed") is not True or manifest.get("notice_identity_verified") is not True:
        raise ValueError("unverified XML or notice identity")
    if manifest.get("source_completeness_verified") is not True:
        raise ValueError("bulk source incomplete")
    return {"publication_number": publication, "bulk_evidence_verified": True,
            "annexes_complete": False, "commercial_approval": False}
