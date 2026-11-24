# AI B2B Proposal Agent — Signed Session to Reviewer Role Boundary

**15 November 2026 — DRAFT / NO-GO.**

## Verified CI
- Latest GitHub Actions: https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43695625955
- Offline Python regression: **188/188 passing** (18 new session unit tests).
- Temporary PostgreSQL 16: **43/43 passing** (4 new signed-session integration cases).
- Separate 20-case diagnostic examples also pass, but previously informed development and **are not an independent untouched holdout**.

## Code and safety checks
- `ci_signed_reviewer_session.py`: HMAC-SHA256 bound synthetic session claims, fixed CI audience and reviewer allowlist, short expiry window, jti/replay detection, exact database and `current_user` reviewer identity match before any data read.
- `test_ci_signed_reviewer_session.py`: invalid key/signature, altered claims, expiry, future issue time, wrong audience/role, overlong lifetime, replay, and database-role mismatch.
- Four actual disposable PostgreSQL integration checks cover own-record read, peer-record invisibility and no connections on an expired token.

## Limitations: do not overclaim
1. This is **not an OIDC / enterprise authentication integration**. Tokens are created only for synthetic CI tests. The test secret is not a real production secret.
2. In-memory replay set is **not atomic or shared** across server workers and cannot be used as production replay protection.
3. Connection factories and signing-key trust must be independently provisioned; this module cannot prove who a human user is. No real login, MFA, account lifecycle, revocation or key rotation.
4. No browser-facing authentication, network server, real customer session, production connection or Neon test branch was created.
5. PostgreSQL database name and role allowlists intentionally target `proposal_eval_ci`, blocking production by construction.
6. No private, permissioned genuine RFQ documents, externally trusted issuer verification or untouched human-labeled evaluation have been run.

**Acceptance: NO-GO.** Neon connector remains unavailable. PR #224 must stay draft and unmerged. No production deployment, commercial offer, payment or outbound messaging.
