# AI B2B Proposal Agent — Ephemeral PostgreSQL recovery fencing

**15 November 2026 — DRAFT / NO-GO; isolated research only**

## Verified CI result
- [GitHub Actions run 43697102171](https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43697102171): **208/208** offline Python regression tests and **67/67** actual disposable PostgreSQL 16 integration tests passed.
- The 20 development-used synthetic document scenarios remain separate and are **not** an untouched independent holdout.
- `ci_pg_shared_session_gate.py` now records an increasing generation counter with successful nonce consumption, revocation, signing-key rotation, and authority disable.
- `consume_once(... trusted_min_generation=...)` checks an explicit external floor **under the PostgreSQL control-row lock before consuming**. A stale generation triggers `RECOVERY_ROLLBACK_DETECTED` and fails closed.
- New test cases simulate a stale generation and reject it using an in-memory CI witness; reject a malformed floor; terminate a live PostgreSQL connection with `pg_terminate_backend` **before commit** and verify the insert was rolled back; and simulate a lost acknowledgement **after commit** and confirm retry returns `SESSION_REPLAY`.
- Latest tests were green in both CI jobs.

## Scope and trust limits
1. The **trusted minimum generation must be obtained from an independent, durable, authenticated, rollback-resistant witness**. This has NOT been implemented. If the caller supplies no floor or a compromised/stale floor, rollback detection is not guaranteed. The CI fixture merely holds a copied counter in process memory.
2. The stale-state test manually decreases a generation in a disposable DB; it is **not an actual base-backup restore, PITR, cross-region replica failover or real crash-recovery exercise**.
3. One test genuinely terminates a PostgreSQL backend mid-transaction; a separate test simulates a lost client acknowledgement after the transaction already committed. It does **not** inject real transport failure precisely at an uncertain commit boundary.
4. A DB administrator can alter the local generation and nonce tables. No externally anchored immutable audit trail or independent attested signer exists.
5. An ongoing already-authorized document read is **not** guaranteed to stop immediately after a revoke event. Cross-connection serialization here covers entry checks only.
6. The CI coordinator uses local disposable PostgreSQL admin credentials, NOT a safe production privileged connection. It must never be deployed without service identity isolation.
7. Neon connector access and real customer identity/authorized documents remain unverified. There was **no** Neon database creation, migration, live credential use, production deploy, merge, payment or customer interaction.

## Next genuine acceptance work
- Define a separately trusted append-only witness for generation/nonce revocation state with durable audit and backup/failover procedures; fail closed on unknown witness health.
- Test restored isolated DB from actual backups and recovery timelines with independently pinned state, including stale/read replica rejection.
- Limit coordinator admin privileges via independently authenticated service role rather than `postgres`.
- Restore Neon project read access and check cost limits before any test-cloud change.
- Obtain permissioned new document corpus and untouched independently labeled evaluation set.

**Conclusion: research CI gates passed; real-world secure recovery remains NO-GO. PR #224 must stay draft.**
