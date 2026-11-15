# AI B2B Proposal Agent — Session Revocation and Signing-Key Retirement

**15 November 2026 — DRAFT / NO-GO. Isolated research only.**

## CI evidence
- Verified GitHub Actions: https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43695992891
- Python offline regression: **208 / 208 passed** (20 added revocation/key tests).
- Ephemeral PostgreSQL 16: **47 / 47 passed** (4 added integration tests).
- Separate 20-case synthetic diagnostic set remains development-used and is not an independent untouched holdout.

## What was added
- `ci_session_revocation.py`: an explicitly CI-only, single-process session authority prototype.
- Rejects revoked tokens before a connection is opened, consumes one-time nonces, disables issuance and access, and rejects tokens from an immediately retired signing key.
- Rotating to a retired key is denied **within the lifetime of this authority instance**.
- A thread lock makes consumption decisions atomic **inside one process**; it is not shared storage.
- The PostgreSQL tests prove revoked/old-key/disabled token attempts do not open reviewer DB connections and a replacement-key token cannot access another reviewer's records.

## Strict gaps
1. No OIDC, actual authenticated user, production authorization gateway, real secret custody, key identifier lifecycle, signing-key rotation governance, or persistent revocation storage.
2. **Race boundary:** a revocation or rotation after a request has passed verification but before its database query finishes cannot retroactively cancel that in-flight request. The tests only establish denial before connection at the tested point.
3. Revocation and key retirement records disappear on process restart, and separate workers do not share state. Do not mistake the thread lock for distributed coordination or durable audit evidence.
4. The signer/issuer is a synthetic test fixture and must not be exposed as a real login endpoint. A bad actor controlling the issuing key can mint valid synthetic claims.
5. No Neon project/branch was verified. No migrations, deployment, payment, customer data, real offer or live credentials were used.
6. Real permissioned documents, trusted independently signed assessments, human-labeled untouched evaluation and a security/privacy review remain unsatisfied.

**Production / commercial acceptance = NO-GO. PR #224 stays draft and unmerged.**
