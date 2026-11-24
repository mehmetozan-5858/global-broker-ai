# Neon account quota and separate B2B project verification — 2026-11-15

**PR #224: DRAFT / NO-GO. Read-only investigation; no mutation, deployment or spending.**

## Evidence verified directly through scoped Neon connector
- Project id `ancient-water-34496424`, owned by Neon organization `org-late-mountain-31449241`, with organization label `Vercel: AI Visibility`. This is AI Visibility infrastructure, **not** a dedicated AI B2B Proposal Agent project.
- Project owner reports `subscription_type=free_v3` and `branches_limit=10`; branch logical size limit is 1,073,741,824 bytes (1 GiB). A per-branch storage cap is not an amount of unconsumed storage allowance.
- The project reports a `consumption_period_start` of `2026-11-01T00:00:00Z` and `consumption_period_end` of `2026-12-01T00:00:00Z`. Its `compute_time_seconds` and `active_time_seconds` values are cumulative project metadata and **must not** be converted directly into remaining CU-hour allowance, invoice amount, or a cost guarantee without interpreting billing definitions.
- Existing branch inventory (previous verification): Vercel production `main`, three READY auxiliary AI Visibility/ZERA/portal branches and one archived snapshot branch. None was verified to be distinct B2B research data or safe to reuse.

## Attempts to close account-wide unknowns
- `get_project_consumption` called with known organization id, known project id and 2026-11-01 to 2026-11-15 daily window: **connector error: Tool get_project_consumption not found**.
- `list_projects` called with explicit organization id: **Tool list_projects not found**.
- `count_projects` called with explicit organization id: **Tool count_projects not found**.
- `search` by `proposal`, `broker`, `global` and known project id: **Tool search not found**.
- The errors are tool routing/availability errors, not proof of absent projects or exhausted quota. No bill or spend information was obtained.

## Conservative decision and next gate
1. **Do not create or clone an evaluation branch under `Vercel: AI Visibility`**, especially production `main`, because copied source data or credentials could expose customers.
2. **Do not create a separate Neon project yet**: account-wide inventory, actual remaining no-cost entitlement, owner/account scope and spending controls remain unknown. `free_v3` in metadata alone cannot prove zero incremental charges.
3. The narrowest remaining external proof is a read-only authorized Neon account console billing/project overview or repaired Neon project/consumption connector. Inspect project list, true available free resources, payment/budget policy, and per-project compute/storage limits without exposing credentials.
4. If there is already an empty, dedicated AI B2B project, verify separately owner, zero customer data, scoped service role, compute auto-suspend and budget boundaries before doing anything else.
5. Durable independent monotonic witness/append-only custody, real auth and independent permissioned evaluation all remain separate **NO-GO** blockers.

**No Neon SQL, customer rows, secrets, project or role creation, merge, deployment or paid change occurred.**
