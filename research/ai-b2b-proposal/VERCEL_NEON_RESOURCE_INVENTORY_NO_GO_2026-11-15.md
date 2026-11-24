# Neon integration resource inventory acceptance gate — 2026-11-15

**PR #224 remains DRAFT / NO-GO. Read-only external investigation.**

## Checked with the connected Vercel account
- `list_integration_configurations(view=account)` and `get_configuration` identified the installed Neon Marketplace configuration under the current Vercel team.
- The configuration's **attached** `free_v3 / Free` plan has `paymentMethodRequired=false`; its published installation terms list **100 projects maximum, 1 GB per project and 100 CU-hours per project**.
- `get_configuration` also reports `projectSelection=selected`, `projects=[]`, Marketplace installation, and storage product capability. **This is NOT an account-wide Neon database project list; an empty Vercel configuration project-selection array does not mean Neon has zero projects.**
- `list_integration_configuration_products` returned the Neon product's metadata schema (region, auth and realtime fields), **not** provisioned Neon database instances, usage remaining or a bill.
- `list_connectors(search=neon)` and `list_project_connector_connections` for AI Visibility returned empty generic connector collections. These are not proof that the Neon Marketplace integration is absent: Marketplace integrations and generic Vercel connectors are distinct interfaces.
- The previously scoped Neon project `ancient-water-34496424` (Vercel: AI Visibility) and its live/customer-associated branches were intentionally **not** reused, cloned or queried for customer data.
- The Neon-side full `list_projects`, `count_projects`, `get_project_consumption` and `get_branch_consumption` connectors remain unavailable. A separate B2B database and the actual unused monthly quota remain unknown.

## What is genuinely verified versus still blocked
- **Verified:** a Neon Marketplace Free plan is installed for the Vercel team; its registered plan limits and no-credit-card requirement.
- **Not verified:** number of Neon database projects, actual remaining compute/storage free quota, an isolated B2B-only Neon project, service-role privileges, separately durable witness custody, zero-cost guarantee of new provisioning, disaster recovery acceptance.
- Vercel project counts and generic connector lists must never be substituted for the Neon database project count or quota.

## Next smallest independent evidence
- Read-only, authorized Neon console **Projects** overview to prove whether there is already a dedicated B2B empty project; read-only **Usage/Billing** view for actual remaining free quota and potential enforced stop/caps. No keys/passwords or customer rows needed.
- Once externally verified, use strictly separate test-only credentials and a non-customer, empty project. Before provisioning, verify the amount of compute, snapshot retention and hard-free limit, plus a safe teardown and no-charge policy.
- Do not claim that synthetic CI HMAC proof is a deployed immutable witness; this remains a distinct NO-GO.
- Any work requiring creating a Neon project/role/compute, making a billable change, or touching production must stay blocked until these conditions are met.

**No resources created, no deployment or merge, no billable operations or customer-data inspection.**
