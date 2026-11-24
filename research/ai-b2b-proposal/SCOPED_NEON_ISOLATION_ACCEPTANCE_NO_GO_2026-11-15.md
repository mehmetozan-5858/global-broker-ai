# AI B2B Proposal Agent — External acceptance gate / scoped Neon isolation

**2026-11-15 — DRAFT / NO-GO. Read-only checks. No resource creation.**

## Read-only facts
- GitHub PR #224 is OPEN, DRAFT, unmerged; isolated tests previously successful (249 Python, 75 disposable PostgreSQL, real CI pg_dump/pg_restore).
- Neon scoped project `ancient-water-34496424` (`neon-cyclamen-bell`) is accessible using `describe_project`, `list_branches`, `list_postgres_databases`, and `list_postgres_roles`. However `list_projects`, `list_organizations`, and `count_projects` still return tool-not-found; therefore **the full set of Neon projects remains unknown**.
- The default `main` branch has Vercel-production restrictions: do not operate or repurpose it.
- The following three READY non-default branches were inspected **only for database names and role names**, with no SQL row reads:
  - `mcp-migration-2026-11-14T05-03-02`: `neondb`; portal/tenant/report verification trial roles (e.g. `portal_reader_isolated_20261114`, `credential_verifier_trial_20261114`, `portal_report_fn_owner_trial_20261115`).
  - `zera-audit-v2-review-20261110`: `neondb`; ZERA audit roles.
  - `review-agent-control-20261109`: `neondb`; agent control and ZERA reader/test roles.
- An additional snapshot branch is archived; it is not an available B2B test environment.
- None of these branches is verified as a dedicated AI B2B Proposal Agent isolated branch. Role names indicate neighboring AI Visibility Works/ZERA testing; **names are not proof of data classification or complete privileges**.
- No distinct B2B Neon project, standalone evaluation branch, least-privilege identity for this proposal-agent module, or independent managed witness was verified. No billing plan or incremental-cost guarantee was established.

## Decision / authorization boundaries
- **NO-GO** for any use of the existing branches for this module, particularly Vercel production `main`. No schema changes, role creation, migrations, Neon reads of actual customer rows, deployments or paid operations.
- Do NOT treat the existing `neondb_owner` or test roles as appropriate B2B service identities.
- **NO-GO** on external witness custody: local/synthetic signed CI witness tests do not establish independently durable, immutable, authenticated storage or DB-witness atomicity.
- These are *environment* blockers, not additional Python/CI coverage tasks. More green synthetic tests cannot close them.

## Minimum verifiable exit criteria
1. Discover and identify an existing **distinct** B2B-only Neon project/branch using an authorized read-only inventory, or explicitly approve creation after pricing/isolation/retention and role plans are established. The current scope does not verify any.
2. Verify isolated ownership, real-data exclusion, free/capped compute/storage pricing, expiry and teardown procedure **before** any compute/branch creation.
3. Establish service identity restricted to only the intended schema, independent authentication and secret custody; reject default admin/owner rights, `BYPASSRLS`, cross-project access and reusable customer credentials.
4. Independently operated, authenticated append-only witness, durable monotonic pin/retention, rollback protection and fail-closed unavailable-health behavior with crash and backup validation.
5. Only then: controlled real test branch, permitted synthetic-only data, independent security review; real customer docs / outbound communications / production remain separate higher gates.

**Decision: DRAFT / NO-GO.** This update records read-only discovery only; no project/branch/role changes or costs.
