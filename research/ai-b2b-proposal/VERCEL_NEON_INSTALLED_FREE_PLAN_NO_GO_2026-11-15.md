# AI B2B Proposal Agent — Vercel-linked Neon plan and read-only billing verification

**2026-11-15 — DRAFT / NO-GO; no resource changes.**

## Direct account records
- Read-only Vercel `list_integration_configurations(view=account)` returned one installed `neon` Marketplace integration under the Vercel team.
- The **current attached billing plan record**, for that integration (not an extrapolation from public website pricing), reports:
  - `billingPlan.id=free_v3`, `name=Free`, `scope=installation`, `paymentMethodRequired=false`, `cost=Free`.
  - `1 GB per project`; `Maximum projects: 100`; `Sizes up to 2 CU / 8 GB RAM`; `100 CU-hours per project`.
- Connected Neon's scoped `describe_project` reports an organization labelled `Vercel: AI Visibility`, project subscription `free_v3` and project-specific branch limit 10. The default `main` is tied to Vercel production.
- Read-only `list_projects` from Vercel returned 23 Vercel projects; this is **NOT a Neon project inventory**. A Vercel project is distinct from a Neon database project. No independent B2B-only Neon project was verified.
- Neon-specific account-wide project list and actual remaining compute/storage consumption continue to fail with missing connector tools, even when supplying the organization id. Thus remaining quota, other Neon projects and actual independent free headroom remain **unknown**.
- Read-only Vercel billing charges were successfully queried for a one-day slice. API returned a 24-hour period starting 2026-11-13 08:00Z and ending 2026-11-14 08:00Z, with billed service total approximately **$1.5245 USD**. Service breakdown contained Vercel Build CPU Minutes, Function Storage, Fluid functions, Sandbox Snapshot Storage and other Vercel services; there was **no separately identified Neon line**. This does **not** establish a Neon bill, Neon zero usage, or remaining free Neon quota.
- A longer Vercel billing period exceeded the connector response size limit, so do not infer month-to-date totals.

## Verified gate changes
- **Plan identification: ACCEPTED (limited)**. The installed Vercel-linked Neon integration's Free tier and listed headline capacities are verified.
- **Cost certainty for NEW B2B project: NOT ACCEPTED**. No actual quota remaining, second project availability, hard spending cap or guarantee of zero incremental Vercel-related expenses was proven.
- **B2B isolation: NOT ACCEPTED**. Existing scoped Neon branches contain AI Visibility/ZERA/portal-related infrastructure. Creating a branch from existing production risks copied schema/data and customer credentials.
- **Identity/witness: NOT ACCEPTED**. Dedicated least-privilege B2B service role, independently anchored durable witness and recovery consistency do not exist.
- Do not create, clone or modify a Neon project/role/branch or link a Vercel project without resource owner, cost and independent isolation acceptance.

## Operational decision
**PR #224 DRAFT / NO-GO**. No paid operation, Neon SQL, customer data read, secret use/reset, branch/provisioning, deploy, merge or outbound contact was performed. Next smallest safe step: read-only Neon project overview and billing/usage in the authenticated vendor console or repaired app API to establish a separate project and remaining actual free entitlement; stop if unavailable.
