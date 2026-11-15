# AI B2B Proposal Agent — Actual pg_dump/pg_restore recovery check

**2026-11-15 — DRAFT / NO-GO. Isolated GitHub Actions CI only.**

## Executed and verified
- [CI run 43698870024](https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43698870024): **three jobs green**: 222/222 offline Python tests; 71/71 actual ephemeral PostgreSQL 16 integration tests; and a new real PostgreSQL custom-format **pg_dump / pg_restore** job.
- New script `ci_actual_pg_restore_check.py` and isolated GitHub Actions job `ephemeral-pg-dump-restore`.
- Initialized an empty disposable `proposal_eval_ci` PostgreSQL service and session coordinator at generation 0.
- Captured a real custom-format `pg_dump` of the isolated coordinator schema **before** using a synthetic reviewer token.
- Committed the token consumption after the backup; generation increased to 1.
- Dropped only the disposable coordinator schema and executed a real `pg_restore` from the earlier backup.
- Confirmed restored coordinator generation returned to 0 and the old token usage record disappeared from the restored state.
- With a synthetic, externally supplied expected-generation floor of 1 plus the signed witness fixture, `consume_with_signed_witness` rejected the old token with `RECOVERY_ROLLBACK_DETECTED`; the rejected attempt did not advance generation or consume the token.

## Limits; no production assertion
1. The trusted floor of 1 is a **synthetic CI test constant** supplied from outside the restored database. It is not a live, durable, independently secured witness. A compromised/missing/rolled-back witness could defeat this protection.
2. This is a **real logical schema dump and restore** into a disposable CI PostgreSQL database, **not** a Neon production backup, physical base backup, PITR, replica promotion, failover, or disaster-recovery certification.
3. The workflow uses a disposable postgres admin fixture and synthetic test signing keys; no user login, OIDC, managed secrets, role-scoped production auth or customer data was involved.
4. The read path must mandate a verified witness floor. Legacy `consume_once` still supports an optional floor for earlier controlled tests; a working production gateway cannot leave it optional.
5. There remains an unsolved atomicity problem across PostgreSQL commit and independent witness persistence; an unknown witness state must cause refusal, not optimistic authorization.
6. No real Neon project/branch was accessed. Connection discovery continues to fail and no paid resource was created.

**Decision: DRAFT / NO-GO.** Continue only with separately secured independent witness custody and cross-resource rollback handling, actual cloud test branch after access/cost verification, and permitted independently labeled customer-document evidence.
