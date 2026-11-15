# External acceptance gate — Neon discovery and independent witness

**2026-11-15 — DRAFT / NO-GO. Read-only external verification.**

## What was verified
- GitHub [PR #224](https://github.com/mehmetozan-5858/global-broker-ai/pull/224) remains open, draft and unmerged. Last verified isolated CI: [43699482158](https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43699482158), 249 offline Python + 75 disposable PostgreSQL integration tests, plus a successful actual ephemeral pg_dump/pg_restore.
- Neon `list_projects`, `list_organizations` and `count_projects` still return a connector tool-not-found error. **However `describe_project`, `list_branches`, `list_postgres_roles`, `list_postgres_databases` and `get_database_tables` work read-only** for the current scoped project.
- Current scoped project: `ancient-water-34496424` (`neon-cyclamen-bell`, Frankfurt `aws-eu-central-1`).
- Its `main` branch is the default primary branch and identifies Vercel production restrictions. DO NOT change or repurpose this branch.
- Four additional branches were observed (three ready, one archived), but none is established as an isolated AI B2B Proposal Agent evaluation database.
- Read-only inspection of branch `review-agent-control-20261109` showed project tables such as `clients`, `client_credentials`, `client_pilot_access`, `ai_provider_comparisons`, `visibility_scans`, `payments`, `sales_pipeline`, `session` and ZERA audit roles. This strongly suggests it is tied to AI Visibility Works/ZERA. No table rows were read, and no secret or customer record was requested.
- No isolated B2B research Neon branch, independently authenticated custodian/issuer, separate safe test role, billing allowance, or cost approval was established.

## Implications
1. **Connector access is partial, not wholly unavailable.** Earlier "Neon inaccessible" statements should now be read as "project-wide discovery tools fail; scoped read-only inspection works".
2. The discovered project and existing branches **must not** be repurposed for PR #224 without explicit proof of ownership, isolation from customer data, authorized branch creation, cost-free operating conditions, role restrictions and rollback procedures.
3. A production-grade independent witness does NOT exist. The CI HMAC and external-floor examples are synthetic, without durable append-only third-party custody, managed keys, tamper resistance, independent state retention, or DB-witness crash consistency.
4. The next acceptance gate is **not another synthetic test**. It is a confirmed separate test environment plus read-only evidence of service identity/least privilege and independently durable witness feasibility. No spending, resource creation, production data change or customer login modification is authorized.
5. PR #224 remains **DRAFT / NO-GO**. Successful CI does not authorize commercial launch.

## Smallest safe next action
- Obtain reliable read-only project inventory (connector repair or independently supplied exact isolated project ID), then confirm an *existing* distinct AI B2B research environment, project ownership, no production/customer data coupling, service role privilege boundaries and billing conditions.
- Do not create branches, roles, passwords, databases or paid storage while the above remain unknown.
- Keep ZERA and AI Visibility production/test operations separate from Global Broker and this proposal-agent research effort.

**Actions performed in this review: only read-only Neon metadata/schema enumeration and GitHub evidence review.**
