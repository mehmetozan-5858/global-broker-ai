"""Strictly bounded, read-only reviewer query adapter for disposable CI.

NOT an HTTP authentication gateway. Database role authentication and
password management are external; no credentials, SQL text or role claims
from a request may be passed to this adapter.
"""
import re
from uuid import UUID

_ROLE = re.compile(r"^b2b_eval_ci_reviewer_[ab]$")
_DB = "proposal_eval_ci"
_QUERY = """SELECT document_id::text, lifecycle_state
FROM b2b_research_eval.document_meta
WHERE document_id = %s::uuid
ORDER BY document_id LIMIT 1"""


class GatewayRejected(ValueError):
    pass


def read_assigned_document(conn, *, document_id):
    """Query a single synthetic metadata row; only from a CI reviewer connection.

    Does not verify human reviewer identity, authenticate users, or permit writes.
    """
    if not isinstance(document_id, str):
        raise GatewayRejected("DOCUMENT_ID_INVALID")
    try:
        parsed = UUID(document_id)
    except (ValueError, AttributeError) as exc:
        raise GatewayRejected("DOCUMENT_ID_INVALID") from exc
    if str(parsed) != document_id:
        raise GatewayRejected("DOCUMENT_ID_NOT_CANONICAL")
    if conn is None or not callable(getattr(conn, "execute", None)):
        raise GatewayRejected("CONNECTION_INVALID")
    # Explicit runtime guard against accidentally targeting cloud/prod.
    identity = conn.execute("SELECT current_database(), current_user").fetchone()
    if (not isinstance(identity, (tuple, list)) or len(identity) != 2
            or identity[0] != _DB or not isinstance(identity[1], str)
            or not _ROLE.fullmatch(identity[1])):
        raise GatewayRejected("NOT_EPHEMERAL_REVIEWER")
    result = conn.execute(_QUERY, (document_id,)).fetchone()
    if result is None:
        return {"status": "NOT_VISIBLE", "document": None, "commercial_approval": False}
    if (not isinstance(result, (tuple, list)) or len(result) != 2
            or result[0] != document_id or result[1] not in ("RECEIVED","FROZEN","REVIEWED","QUARANTINED")):
        raise GatewayRejected("UNEXPECTED_RESULT")
    return {"status": "FOUND", "document": {"document_id": result[0], "state": result[1]},
            "commercial_approval": False}
