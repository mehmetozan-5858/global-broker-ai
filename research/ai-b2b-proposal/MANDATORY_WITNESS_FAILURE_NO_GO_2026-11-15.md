# AI B2B Proposal Agent — Mandatory witness failure closure

**15 November 2026 — DRAFT / NO-GO, research only.**

## Confirmed GitHub evidence
[Workflow run 43699178132](https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43699178132) passed all three jobs:
- **237/237** Python regression tests; 15 new simulated provider-outage/stale-response/post-commit failure unit tests.
- **71/71** actual ephemeral PostgreSQL 16 authorization/recovery tests.
- Real custom-format **pg_dump/pg_restore** of disposable coordinator passed and rollback of a previously used token remained rejected with an artificial external generation pin.

## Added code
- `ci_required_witness_gate.py`: restricted prototype requiring a witness provider, valid signed evidence, separately pinned minimum generation and a verified persistence result.
- `test_ci_required_witness_gate.py`: tests missing provider, read exceptions, malformed response, missing floor, old witness, bad signature, connection errors, ambiguous transaction, witness persistence timeout/rejection, stale acknowledgment, and failure to read updated evidence.
- Fail-closed outcome: missing/invalid witness denies before database connection; when database commit is complete but independent evidence cannot be confirmed, a role/authorization success is **not returned**. The session may still be spent; no automatic retry can be treated as successful authorization.

## Unresolved limitations
1. There is still **no actual independently managed immutable/durable witness provider**. The new interface is tested using a synthetic in-memory fixture; do not describe it as provisioned production storage.
2. Cross-resource atomic commit is not implemented. If the DB commits and the provider write fails, the system denies the request but may require manual reconciliation. Multiple concurrent commit streams, crash recovery and rollback of the external provider remain unproven.
3. Existing low-level `consume_once` permits no external generation floor for explicitly controlled previous CI regression scenarios; therefore the project must not claim that bypass paths are impossible in production.
4. Provider health, external issuer identity, credentials, audit controls, durable retention and managed HSM/key lifecycle are unverified.
5. No Neon project access or deployment. No real customer login, authorized real RFQ file, offer, payment or outbound message.
6. An in-flight already-authorized document read cannot be guaranteed to stop immediately on a subsequent revocation.

**PR #224 remains DRAFT and NO-GO. No merge, production deployment, spending or customer data.**
