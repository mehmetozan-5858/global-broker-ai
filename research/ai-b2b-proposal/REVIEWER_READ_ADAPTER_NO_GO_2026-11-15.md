# AI B2B Proposal Agent — Read-only reviewer adapter acceptance evidence

**15 Nov 2026 — DRAFT / NO-GO.**

## Verified results
- GitHub Actions [run 43694186379](https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43694186379): 170 Python regression tests and 39 PostgreSQL 16 integration tests passed.
- New Python module `ci_reviewer_read_gateway.py` implements a hardcoded, parameterized, single-record read against an authenticated PostgreSQL session. No SQL supplied by a request is executed.
- `test_ci_reviewer_read_gateway.py`: 14 negative/positive unit tests.
- `test_ephemeral_reviewer_identity.py`: 7 additional live PostgreSQL integration checks for own-record read, peer-record invisibility, disallowing admin connection, malformed input, and spoofed custom session values.

## Safety boundary
1. Database name must exactly match ephemeral `proposal_eval_ci` and `current_user` an explicit CI reviewer role; other DBs/admin roles rejected.
2. The adapter returns only a UUID and lifecycle state, never raw document contents or digests.
3. Document UUID must be canonical; passed as SQL parameter; no arbitrary SQL, updates, transactions, or outbound messages from adapter.
4. PostgreSQL RLS is independently checked in CI using two restricted login roles. Production SQL migration remains default-deny without read policies, grants, or a working service.
5. **No real user authentication**: this module is neither an HTTP server nor an identity provider or end-to-end trust chain. It relies on a PostgreSQL connection authenticated elsewhere and is only safe to invoke with independently verified, restricted connections.
6. **No real Neon access**: connected Neon `list_projects` still fails with `Tool list_projects not found`. No Neon or production resources were accessed or changed.

## Remaining NO-GO gates
- Restore Neon read-only discovery, confirm test branch and cost policy without cloud mutation.
- Trusted authenticated gateway/session mapping to least-privilege Postgres roles, restricted connection factory and secrets lifecycle.
- Authorized private test documents with independently adjudicated labels, issuer verification and page-visual checks.
- Security/privacy review, explicit commercial sign-off, and separate live deployment acceptance.

No merge, deploy, live customer data, production auth, actual offer, or payment.
