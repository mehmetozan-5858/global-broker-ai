"""Local-only evaluation metadata ledger for isolated B2B proposal R&D.

NO document bytes, customer text, email, access tokens, or real IDs are stored.
Owner-only POSIX file permissions are best-effort; filesystem ACLs, key custody,
encrypted-at-rest storage, backups and identity verification remain external.
Not a network service, production backend or commercial acceptance system.
"""
import hashlib
import json
import os
import re
import sqlite3
import stat
from pathlib import Path

_HASH = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
_ROLES = frozenset(("custodian", "reviewer", "auditor"))
_STATES = frozenset(("RECEIVED", "FROZEN", "REVIEWED", "QUARANTINED"))

class LedgerRejected(ValueError):
    pass

def _valid_identifier(value):
    return isinstance(value, str) and bool(_ID.fullmatch(value))

def _digest(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()

def open_metadata_ledger(path):
    """Create or open a local SQLite ledger with owner-only file permissions."""
    if not isinstance(path, (str, os.PathLike)):
        raise LedgerRejected("PATH_INVALID")
    target = Path(path)
    if not target.is_absolute():
        raise LedgerRejected("ABSOLUTE_PATH_REQUIRED")
    if target.exists() and (target.is_symlink() or not target.is_file()):
        raise LedgerRejected("FILE_NOT_REGULAR")
    if not target.parent.is_dir():
        raise LedgerRejected("PARENT_MISSING")
    if os.name != "posix":
        raise LedgerRejected("POSIX_ONLY_PROTOTYPE")
    if target.exists():
        mode = stat.S_IMODE(target.stat().st_mode)
        if mode & 0o077:
            raise LedgerRejected("FILE_PERMISSIONS_TOO_BROAD")
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(target, flags, 0o600)
    try:
        actual = os.fstat(fd)
        if not stat.S_ISREG(actual.st_mode):
            raise LedgerRejected("FILE_NOT_REGULAR")
        if stat.S_IMODE(actual.st_mode) & 0o077:
            raise LedgerRejected("FILE_PERMISSIONS_TOO_BROAD")
    finally:
        os.close(fd)
    conn = sqlite3.connect(str(target))
    try:
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS intake(
          record_id TEXT PRIMARY KEY, source_digest TEXT NOT NULL,
          manifest_digest TEXT NOT NULL, reviewer_id TEXT NOT NULL,
          state TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS audit(
          sequence INTEGER PRIMARY KEY AUTOINCREMENT,
          record_id TEXT NOT NULL, actor_id TEXT NOT NULL,
          actor_role TEXT NOT NULL, event TEXT NOT NULL,
          event_digest TEXT NOT NULL, previous_digest TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit
            BEGIN SELECT RAISE(ABORT, 'AUDIT_IMMUTABLE'); END;
        CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit
            BEGIN SELECT RAISE(ABORT, 'AUDIT_IMMUTABLE'); END;
        CREATE TRIGGER IF NOT EXISTS intake_no_delete BEFORE DELETE ON intake
            BEGIN SELECT RAISE(ABORT, 'INTAKE_IMMUTABLE'); END;
        """)
    except Exception:
        conn.close()
        raise
    return conn

def _check_actor(actor_id, role):
    if not _valid_identifier(actor_id) or role not in _ROLES:
        raise LedgerRejected("ACTOR_OR_ROLE_INVALID")

def _append_audit(conn, record_id, actor_id, role, event):
    previous = conn.execute("SELECT event_digest FROM audit ORDER BY sequence DESC LIMIT 1").fetchone()
    prev = previous[0] if previous else "0"*64
    payload = {"record_id": record_id, "actor_id": actor_id, "role": role,
               "event": event, "previous": prev}
    digest = _digest(payload)
    conn.execute("""INSERT INTO audit(record_id,actor_id,actor_role,event,event_digest,previous_digest)
                    VALUES(?,?,?,?,?,?)""", (record_id,actor_id,role,event,digest,prev))

def intake_metadata(conn, *, record_id, source_digest, manifest_digest,
                    reviewer_id, actor_id, role):
    """Metadata only; required digests must originate in a separately trusted process."""
    _check_actor(actor_id, role)
    if role != "custodian":
        raise LedgerRejected("CUSTODIAN_REQUIRED")
    if not all(_valid_identifier(x) for x in (record_id, reviewer_id)):
        raise LedgerRejected("IDENTIFIER_INVALID")
    if not all(isinstance(x, str) and _HASH.fullmatch(x) for x in (source_digest,manifest_digest)):
        raise LedgerRejected("DIGEST_INVALID")
    with conn:
        if conn.execute("SELECT 1 FROM intake WHERE record_id=?", (record_id,)).fetchone():
            raise LedgerRejected("DUPLICATE_RECORD")
        conn.execute("""INSERT INTO intake(record_id,source_digest,manifest_digest,reviewer_id,state)
                        VALUES(?,?,?,?,?)""", (record_id,source_digest,manifest_digest,reviewer_id,"RECEIVED"))
        _append_audit(conn,record_id,actor_id,role,"RECEIVED")

def transition_metadata(conn, *, record_id, new_state, actor_id, role):
    _check_actor(actor_id, role)
    if not _valid_identifier(record_id) or new_state not in _STATES:
        raise LedgerRejected("TRANSITION_INVALID")
    allowed = {("RECEIVED","FROZEN"):"custodian", ("RECEIVED","QUARANTINED"):"custodian",
               ("FROZEN","REVIEWED"):"reviewer", ("FROZEN","QUARANTINED"):"custodian"}
    with conn:
        row = conn.execute("SELECT state,reviewer_id FROM intake WHERE record_id=?",(record_id,)).fetchone()
        if not row:
            raise LedgerRejected("RECORD_UNKNOWN")
        current, expected_reviewer = row
        if allowed.get((current,new_state)) != role:
            raise LedgerRejected("ILLEGAL_STATE_TRANSITION")
        if role == "reviewer" and actor_id != expected_reviewer:
            raise LedgerRejected("REVIEWER_NOT_ASSIGNED")
        conn.execute("UPDATE intake SET state=? WHERE record_id=?", (new_state,record_id))
        _append_audit(conn,record_id,actor_id,role,new_state)

def verify_audit_chain(conn):
    prev = "0"*64
    for record_id,actor_id,role,event,digest,linked in conn.execute(
            "SELECT record_id,actor_id,actor_role,event,event_digest,previous_digest FROM audit ORDER BY sequence"):
        expected=_digest({"record_id":record_id,"actor_id":actor_id,"role":role,
                          "event":event,"previous":prev})
        if linked != prev or digest != expected:
            return False
        prev=digest
    return True

def sanitized_summary(conn):
    """Only counts and integrity, no row contents or identifiers."""
    states=dict(conn.execute("SELECT state,COUNT(*) FROM intake GROUP BY state").fetchall())
    return {"states":states,"audit_events":conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0],
            "audit_chain_valid":verify_audit_chain(conn),
            "identity_authentication_verified":False,"storage_encrypted_at_rest_verified":False,
            "real_customer_data_authorized":False,"commercial_approval":False}
