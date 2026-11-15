# AI B2B Proposal Agent — Private Evaluation Metadata Ledger

**Date:** 15 November 2026  
**Status:** DRAFT / NO-GO; offline local proof-of-concept, not a deployed private environment.

## Implemented and tested
- `private_eval_metadata_ledger.py`: local SQLite file, metadata only (pseudonymous record ID, source digest, manifest digest, reviewer ID, state), no PDF bytes or raw claims.
- Owner-only POSIX file permission check; rejection of symlinks, broad-permission existing database files, relative paths and malformed identifiers.
- Prototype transitions: `RECEIVED → FROZEN → REVIEWED`, plus quarantining, with custodian/reviewer role parameter checks.
- Append-only-by-trigger audit entries, chained hashes and aggregate sanitized summary.
- `test_private_eval_metadata_ledger.py`: 22 purely synthetic tests; no customer documents.
- Offline CI: https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43690795462 — 144 passing regression cases, separate synthetic development diagnostic also passed.

## Security boundaries and known shortcomings
1. The `actor_id` and `role` parameters are **caller assertions**: no login, cryptographic principal verification or RBAC enforcement from a trusted service exists. They **cannot secure untrusted callers**.
2. SQLite database owner may modify tables, disable or drop triggers, rewrite the database or forge a new valid hash chain. The audit chain is an accidental-tampering check, **not externally anchored or tamper-proof evidence**.
3. POSIX file permissions do not establish encrypted-at-rest storage; backups, shared parent directories, ACLs, process isolation and hardware key custody remain unverified.
4. This code does not create a private hosted environment, manage secrets, deploy or persist any actual customer evaluation records.
5. SHA-256 digests can expose information through association and must be treated as sensitive metadata. The test values are artificial. No real customer names or files belong in the public repo.
6. Public CI tests only software behavior in ephemeral runners; they are not certification that a production database is safe.

## Future acceptance gates
- Dedicated private store and role-scoped service identities (non-production branch only initially).
- Authenticate custodian and reviewer via trusted auth provider; log actor provenance outside the application.
- External write-once audit anchoring; prevent privileged actor from rewriting past evidence.
- Encryption and key rotation, backup/restore, retention/deletion governance, incident response.
- Explicit authorized private example documents and independent gold labels, frozen before blind evaluation.
- Security and privacy review before any real customer data access.

PR #224 stays draft / NO-GO. No production merge, deploy, payment or commercial offer is authorized.
