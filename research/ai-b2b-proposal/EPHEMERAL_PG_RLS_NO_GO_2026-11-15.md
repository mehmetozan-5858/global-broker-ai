# AI B2B Proposal Agent — Ephemeral PostgreSQL RLS Verification

**15 November 2026 — DRAFT / NO-GO**

## Tested results
- GitHub Actions: https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43691575093
- `offline-tests`: 156 Python regression tests passed; separately, the 20 development-used synthetic examples passed.
- `ephemeral-postgres-rls`: 8 actual PostgreSQL 16 tests passed in a short-lived GitHub Actions service container against database `proposal_eval_ci`.
- Source code: `test_ephemeral_postgres_rls.py`; schema: `private_eval_postgres.sql`.

## Stronger authorization boundary
The earlier RLS policies depended on caller-settable `b2b_eval.actor_role` and `b2b_eval.actor_id`. That does not authenticate anyone; users with arbitrary SQL can spoof them. The research SQL was revised to declare **no policies** and no database grants or identities. PostgreSQL therefore defaults to denying table access under RLS for a restricted role.

The disposable integration test creates a disposable reader role **only in the CI container**, grants that role SELECT/INSERT/UPDATE/DELETE on the three tables, then confirms:
- RLS is enabled and forced on all three tables.
- There are no RLS policies to authorize visibility.
- The restricted role cannot see inserted test rows or add, modify, or delete data.
- Spoofed session settings do not unlock rows.
- The role is neither superuser nor BYPASSRLS.

**This confirms an intentionally nonfunctional default-deny baseline, not a safe working reviewer service.** Database owner/superuser capabilities bypass this model.

## External dependency blocker
Two current connector attempts for Neon `list_projects` and `search` returned `Tool ... not found`. No Neon project, branch, connection, cost allowance or production data was inspected. No Neon branch, paid resource or actual cloud database was created or changed.

## Next safe steps
1. Restore connector's ability to enumerate Neon projects/branches (or authorized alternative service) **before** any cloud test environment action.
2. Determine whether a dedicated isolated test branch is truly free and allowed. Do not create unknown-billing resources.
3. Implement trusted auth **outside SQL caller-controlled settings** with least-privilege database roles and a nonproduction, deny-arbitrary-SQL gateway.
4. Evaluate positive and negative authorization on **that actual isolated branch** with fake data.
5. Obtain independently labeled authorized private documents; never put customer data or secrets in public GitHub.

**PR #224 must remain draft; no merge, deploy, commercial approval, payment, or real customer data.**
