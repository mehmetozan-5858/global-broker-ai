# AI B2B Proposal Agent — Ephemeral Reviewer Identity RLS Results

**15 November 2026 — DRAFT / NO-GO.**

## Verified GitHub CI
Workflow https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43691836161

- Offline regression: **156/156** successful.
- Ephemeral PostgreSQL 16: **22/22** successful, combining 8 default-deny and 14 reviewer-identity scenarios.
- Synthetic development diagnostic: 20/20, but this set previously informed the code, and is NOT an independent untouched holdout.

## New evidence
- Two separate PostgreSQL LOGIN principals `b2b_eval_ci_reviewer_a` and `b2b_eval_ci_reviewer_b` are created exclusively inside a throwaway GitHub Actions PostgreSQL container.
- A CI-only `FOR SELECT` policy uses PostgreSQL-authenticated `current_user`; it does **not** rely on caller-controlled `b2b_eval.actor_id` or `actor_role`.
- Reviewer A sees only A's assigned synthetic row; B sees only B's row. Cross-reviewer lookups return no data.
- Neither role gets write privileges or access to the review/audit tables; spoofing custom session settings does not bypass RLS.
- The default-deny reader from earlier tests remains unable to see rows. All test roles lack superuser and `BYPASSRLS` privileges.

## Remaining limitations
1. This CI-only policy is **not** applied to the repository's `private_eval_postgres.sql` migration. That draft continues to have no RLS policy or grants, so its default-deny posture remains intentionally nonfunctional.
2. CI database passwords are synthetic disposable fixture values; no actual authentication gateway, session management or secrets rotation was tested.
3. Role-name identity is only as trustworthy as PostgreSQL service authentication and role lifecycle administration. No real customer login, auditor identity, Neon access, or production tenant isolation was tested.
4. Neon `list_projects` still returns `Tool list_projects not found`; no Neon resources were read, created or changed.
5. Real document issuer verification and independently adjudicated private customer documents remain absent. No production approval.

**No merge, deploy, Neon migration, paid transaction, live customer data, or outbound offer.**
