# PR #224 — Neon alternate read-only account verification

**15 November 2026 — DRAFT / NO-GO; external gates only.**

## Verification performed
- Existing scoped Neon project: `ancient-water-34496424`, organization `org-late-mountain-31449241` labelled `Vercel: AI Visibility`, owner reports `free_v3`. No dedicated B2B project was established.
- `list_projects`, `count_projects`, `get_project_consumption`, `get_branch_consumption`, `search`, `fetch` and `list_organizations` remain unavailable through the connector (tool-not-found errors). Known organization id was supplied where supported. These errors **do not** prove that no other projects exist.
- `list_project_permissions` for the scoped project returned HTTP 404 `project not found`. This is not proof that the project is missing: other scoped metadata tools work.
- `list_project_members` returned HTTP 404 `Project permissions are not enabled for this organization`. Consequently there is **no validated project-scoped member-role control in this organization**. This is distinct from restricted PostgreSQL database roles and does not establish their effective privileges.
- `list_operations` succeeded read-only and showed successful `start_compute` and `suspend_compute` events for existing production/agent branches on November 15, 2026. These events confirm operational starts/suspensions, but do NOT prove that compute usage is free or calculate remaining CU-hours.
- The scoped project's subscription metadata, previous branch inventory and 2026-11-01 through 2026-12-01 consumption period remain the only direct account-wide cost clues, not a billing statement.
- No actual customer data, password, token, query results or credential strings were requested.

## Minimum safe conditions not yet satisfied
1. Independent read-only account project list and actual remaining Free-plan compute/storage quota plus binding no-charge policies.
2. Dedicated empty B2B research environment that cannot inherit live AI Visibility / ZERA customer records.
3. Non-owner, narrowly scoped *database* service identity, with direct verification of grants, `BYPASSRLS` behavior and secret custody in a separate environment.
4. Independently durable, managed-key, append-only external witness and a recovery/rollback acceptance protocol.
5. Legal permission for independent real-world documents and genuine evaluation holdout.
6. Separate explicit approval for any resource provisioning or spending after the above checks. This step does not authorize it.

## Decision
**NO-GO / DRAFT** for production and for new Neon resources. Existing customer/production environments remain untouched. No new CI tests, merges, branches, databases, roles, compute changes, spend or outbound messages occurred during this read-only verification.
