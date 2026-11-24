# AI B2B Proposal Agent — Uncertain commit reconciliation, NO-GO

**15 November 2026 — DRAFT / RESEARCH ONLY.**

## Verified results
- [GitHub Actions run 43699482158](https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43699482158): **249/249 Python regression** and **75/75 ephemeral PostgreSQL 16 integration tests** passed.
- Separate **real disposable pg_dump/pg_restore** workflow passed again and demonstrated rollback-guarded rejection of a previously consumed token with an artificial external pin.
- Added `ci_uncertain_commit_reconciliation.py` and 12 offline negative/positive diagnostic tests.
- Added 4 actual PostgreSQL integration scenarios in `test_ci_pg_shared_session_gate.py`: already spent nonce, witness lag, witness provider outage and missing nonce.

## What reconciliation does
- Confirms a signed witness before database inspection; checks the PostgreSQL nonce and generation with an isolated CI connection.
- Classifies mismatches as `BLOCKED_DB_ROLLBACK`, `BLOCKED_NO_COMMITTED_NONCE`, `BLOCKED_REVOKED`, `BLOCKED_WITNESS_LAG_OPERATOR_REVIEW`, or `BLOCKED_SPENT_NO_REAUTHORIZATION`.
- **Every result is explicitly unauthorized:** no new grant, no token retry, no witness auto-advance, no DB mutation. Witness-lag needs independently verified operator review; it is not proof that automatic repair is safe.
- Witness read failures and invalid signatures fail closed *before* DB inspection.

## Critical limitations
1. This is inspection-only CI diagnostics, **not** automated witness recovery or a deployed customer service. No durable independent witness storage or real identity provider exists.
2. Transaction rollback or uncertainty cannot be universally determined from one snapshot; a stale restored database and an unavailable witness must not lead to approval. Committed DB operations whose witness cannot be persisted may require manual reconciliation and token replacement, not replay.
3. The external minimum floor remains a synthetic test assumption, and read-only inspection cannot prove race-free multi-resource reconciliation, crash recovery or distributed transaction atomicity.
4. The coordinator uses ephemeral CI postgres admin privileges and synthetic signing keys. No Neon role, database, document, payment, email, production deployment or real customer data was used.
5. Previously development-used 20 synthetic proposal examples are NOT a held-out independent evaluation.
6. In-flight cancellation, external audit custody, replication/failover safety and cloud production security remain unverified.

**Decision: NO-GO; keep PR #224 DRAFT, unmerged.** Next gate: externally trusted and durable witness custody, safely scoped service authentication, real isolated recovery tests, then authorized independent evaluation.
