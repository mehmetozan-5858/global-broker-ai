# AI B2B Proposal Agent — Signed recovery witness contract

**15 November 2026 — DRAFT / NO-GO. Isolated research only.**

## Verified evidence
- [CI run 43698573439](https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43698573439) passed with **222/222 Python** and **71/71 actual temporary PostgreSQL** tests.
- New `ci_external_recovery_witness.py` requires an HMAC-signed synthetic generation statement **and** a separately supplied trusted minimum generation. Missing witness, incorrect HMAC, stale signed value, missing floor or invalid floor are denied.
- `test_ci_external_recovery_witness.py` contains 14 new synthetic proof and rejection cases.
- Four additional ephemeral PostgreSQL 16 tests check matching signed witness, stale database generation, stale signed witness with a newer trusted floor, and missing witness.
- The database-only counter and the signed witness are distinct logical inputs. In CI the trust floor is held in test memory and keys are synthetic fixtures.

## Hard unresolved dependencies
1. **No real independent durable witness store exists.** A signed claim and a supplied floor do not prove who signed it or that the floor survived restoration. No WORM store, key vault, audit anchoring, independent custody or production privilege isolation is in place.
2. **Two-resource atomicity remains unsolved:** a DB transaction may commit without witness persistence, and a witness can lag behind DB commits. A stable monotonic external fence must be designed so uncertain commits fail closed.
3. The test simulates a stale restored generation by deliberately decreasing the counter on an isolated CI database; no actual backup restore, PITR, replica promotion or multi-region failover has been tested.
4. A rollback of the independent witness itself to a previously validly signed older statement can only be detected if a genuinely independent newer trusted minimum survives.
5. The signing key is a synthetic fixture and cannot authenticate a real reviewer, custodian or service. No real human-approved evaluation material or cloud authentication.
6. Neon is not accessible through the connected tooling; no actual Neon branch, role or test deployment has been inspected/created.
7. Real customer documents, payments, email, production and live offers remain untouched.

**Decision: NO-GO. PR #224 remains draft and unmerged.** Next acceptance gate is actual independent append-only durable witness with managed keys and intentional recovery/failover tests.
