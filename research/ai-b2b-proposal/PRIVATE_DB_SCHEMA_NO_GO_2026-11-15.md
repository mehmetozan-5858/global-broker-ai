# AI B2B Proposal Agent — Isolated test database design review

**15 November 2026 — DRAFT / NO-GO.**

## What was actually accomplished
- Created research-only `private_eval_postgres.sql` describing three metadata tables in `b2b_research_eval`, no customer files, default-deny writes and explicit RLS declarations.
- Added `check_private_eval_schema.py` and ten offline static structural/negative checks.
- CI: https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43691203615 — 154/154 offline regression tests and the separate 20-case synthetic diagnostic succeeded.
- PR #224 stays draft and unmerged.

## What was NOT accomplished
- The connected Neon project list failed (`Tool list_projects not found`); no Neon project, branch, account role, actual RLS policy or running database was verified or changed.
- No database was provisioned, no migrations executed, no authenticated gateway established, no credentials generated, no production deployment.
- Static SQL scans do not prove PostgreSQL execution, effective privileges, privilege inheritance, policy isolation or data confidentiality.

## Important threat-model limitations
- RLS policies use `current_setting('b2b_eval.actor_id',true)` and `current_setting('b2b_eval.actor_role',true)`, which arbitrary direct SQL clients can forge. **These MUST NOT be trusted as authentication or exposed with direct database access.**
- No data-writing policy was installed deliberately; the draft is not a functional ingestion app. A trusted authentication gateway and separately assigned restricted DB identities would be needed.
- Schema-only `REVOKE` cannot substitute for reviewing role membership, database privileges or existing defaults.
- The local SQLite prototype's role fields are also caller claims, not trusted authentication.

## Next real acceptance steps
1. Restore/verify the Neon connection's project read access before picking a dedicated test project.
2. Record cost cap and test-only branch isolation before creating anything (no production copy of customer data).
3. Use trusted server identities, parametrized and scoped access, deny arbitrary SQL, then execute negative access tests on an isolated database.
4. Confirm encryption, audit policy, retention, backups, secrets management and actual independent reviewer before introducing any real data.

This report is an honest **unexecuted design and CI-only result**, not a database deployment acceptance certificate.
