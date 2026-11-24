# AI B2B Proposal Agent — Neon free-tier and isolated environment feasibility

**15 November 2026. DRAFT / NO-GO. Read-only account/project metadata audit.**

## Verified in connected Neon (scoped metadata, no SQL rows)
- Project: `ancient-water-34496424`, `neon-cyclamen-bell`, region `aws-eu-central-1`.
- The scoped project's owner metadata reports `subscription_type: free_v3` and `branches_limit: 10`.
- Five branches were listed: production-linked `main`, three READY branches with existing AI Visibility Works / ZERA / portal testing roles, and one archived branch. **No isolated AI B2B Proposal Agent branch is established** in this scoped project.
- The four READY branches each expose an existing read-write endpoint reporting `0.25 CU` min/max, `suspend_timeout_seconds: 0`, and `current_state: idle`. These settings were inspected, **not modified**. Do not infer zero compute consumption, billing allowance, or safe automatic suspension merely from `idle`.
- The default `main` branch has Vercel production restrictions. No branch or data copy from it was created.
- Full account/project inventory remains unknown: `list_projects`, `list_organizations`, and `count_projects` still return connector tool-not-found. The scoped project is not proof that a dedicated B2B project exists elsewhere.
- Neon project/branch *usage* via `get_project_consumption` could not be queried because it requires an organization ID unavailable through current connector discovery. **No actual remaining free quota / invoice / overage risk was established.**

## Official plan research (public pricing, NOT this account's entitlement)
- Neon published on **2 October 2026** that its general Free offering includes up to **100 projects**, **100 CU-hours/month per project**, **1 GB database storage per project**, and **10 branches/project**:
  https://neon.com/blog/neon-free-plan-1-gb-per-project
- This general offer does not prove that the user's Vercel-linked `free_v3` project has the same onboarding, free capacity, branch compute quota, or upgrade restrictions. Current billing/usage still needs account-side confirmation.
- Neon explains that a normal branch can clone the parent's schema **and data**; do not branch the AI Visibility production project just to obtain an unrelated B2B test environment:
  https://neon.com/blog/instant-branches-schema-only-or-with-data-the-choice-is-yours
- A truly **separate empty project**, created only after explicit cost, ownership, data-isolation and teardown checks, is preferable to cloning any AI Visibility Works or ZERA branch.

## Smallest safe external acceptance gates
1. Verify all Neon projects/accounts and current free-tier billing via read-only account/console data (or repaired project inventory tool); confirm an existing dedicated B2B project if one is present.
2. For a new dedicated B2B project, verify zero-charge eligibility and hard stop/limits *before* creation; choose fixed `0.25 CU`, aggressive scale-to-zero for idle test compute, no live customer data and temporary retention. No paid action without additional user approval.
3. Establish dedicated non-owner roles and separate test-only credentials; no production `neondb_owner`, default superuser or copied customer secrets, and no customer rows copied from the AI Visibility project.
4. Separately demonstrate external immutable witness custody and signed monotonic floor independent of the evaluation DB, including how it persists across backup restoration; do not equate synthetic CI witness fixtures with a deployed real service.
5. Require owner authorization before migrations, customer-facing changes, external spending or production release.

## Actions performed and decision
- Only read-only Neon metadata, branch/role/database names, endpoint settings and official public pricing were consulted.
- No Neon project/branch/compute/role was created or changed. No customer row queried, no credential requested or reset, no paid resource, merge or production deploy.
- **PR #224: DRAFT / NO-GO.** Current CI evidence is not live or independent-identity acceptance.
