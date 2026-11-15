# AI B2B Proposal Agent — Shared Session Coordination Evidence

**15 November 2026 — PR #224 DRAFT / NO-GO; disposable GitHub CI only**

## Verified acceptance evidence
- [GitHub CI run 43696433316](https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43696433316): **208/208** offline Python tests and **63/63** actual ephemeral PostgreSQL 16 integration tests passed.
- New `ci_pg_shared_session_gate.py`: serializes session consumption, revocation, and signing-key rotation via a PostgreSQL control-row `SELECT ... FOR UPDATE` inside explicit transactions.
- New `test_ci_pg_shared_session_gate.py`: **16** integration tests, including simultaneous use of one token from two independent connections, remote revocation, consumed-then-revoked token, disabled authority, stale signing key, and key rollover rejection.
- Control schema exists only inside transient database `proposal_eval_ci`, not in the production migration. Session data stores nonce hashes, the active signing-key SHA-256 fingerprint, and retired fingerprints; **no raw signing keys or documents**.
- A prior test run failed because a terminal disable test ran before the retired-key reuse case. The test ordering was corrected; final CI passed. This was a test fixture ordering issue, not a successful authorization bypass.

## Technical and trust boundaries
- PostgreSQL's transaction-level row lock gives a single serialization point **for connections to that same ephemeral PostgreSQL primary**. The test covers two independently authenticated connections and two concurrent threads. It is not a test of cross-region replicas or a real multiple-process deployment.
- The coordinator requires the CI-only `postgres` administration connection for mutations. **This is deliberately NOT a production access pattern**; restricted, independently authenticated service roles and server-side credential custody have not been implemented.
- A prior token consumption can finish an in-flight request after revocation, because this check authorizes before the actual document read. **Immediate in-flight cancellation is not guaranteed.**
- A restored older DB backup could lose revocation or retired-key history; durable audit anchoring, rollback resistance, high availability, failover and backup tests remain absent.
- The signing key is a synthetic fixture supplied by a trusted caller; no independent human/IdP identity, OIDC, MFA, secret service or real user-to-role binding exists.
- No actual Neon project, cloud database role or customer document was accessed. Neon connector continues to be unavailable.
- Real independent labeled customer document evaluation, source verification, PDF rendering checks and legal permissions remain open.

## Exit condition
Maintain `NO-GO`. No merge, deploy, paid cloud resource, customer email, commercial offer, production data, or live credential use. Next genuine gates are dedicated authenticated service identity, controlled secrets, backup/failover behavior, and actual isolated Neon branch access.
