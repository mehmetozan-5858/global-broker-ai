# AI B2B Proposal Agent — Out-of-Band Evaluation Custody

**Date:** 15 November 2026  
**Status:** DRAFT / NO-GO — isolated research branch only

## Delivered
- `custodian_pinned_eval.py`: verifies evaluation manifest SHA-256 against an explicit separately supplied digest; checks reviewer identity against an explicit allowlist before computing measurements.
- `test_custodian_pinned_eval.py`: 15 offline synthetic tests covering missing/wrong digest, modified manifest or labels, rejected reviewer, unauthorized reviewer, absent dataset freezing, contamination and exact metric isolation.
- `.github/workflows/ai-b2b-proposal-v9-offline.yml`: 122 regression tests plus the 20-case development-used diagnostic set.
- **Verified CI:** https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43690589237 — success, 122 tests.

## Critical limits
This is **not cryptographic signer identity verification**. Whoever supplies both the digest and manifest can generate a matching pair. Reviewer IDs in a manifest and an allowlist are text assertions, not signed identities. The code cannot verify physical document origins, customers' permission, a certificate authority, signatures, a PDF's visual semantics, or independent adjudication.

The existing set of 20 diagnostic examples influenced development, so it is **not an untouched holdout** and cannot provide a real-world accuracy claim. The 122 green tests likewise only prove code-path behavior on the test fixtures.

## Unresolved acceptance requirements
1. Secure, separately administered digest/manifest registry with authenticated custodians and durable audit trail, no secrets stored in public GitHub.
2. Actual authorized, unreused Turkish and English documents with independently reviewed gold labels in private storage.
3. Blind evaluation with predeclared metrics and sufficiently many examples, including multi-page PDF and challenging table layout.
4. External issuer/company/certificate validation and visual reconciliation.
5. Security review and explicit signed-off live acceptance.

Never merge PR #224, deploy, approve commercial offers, or use live credentials without these gates.
