# Broker Paddle sandbox catalogue evidence — 2026-10-30

Observed through the authenticated Paddle sandbox dashboard after owner-authorized browser fallback. The dashboard displayed **Test mode** and account **AI Visibility**. Existing AI Visibility integration onboarding was marked complete; this is not Broker checkout evidence.

## Created and verified sandbox catalogue

| Plan | Product ID | Price ID | Monthly USD |
| --- | --- | --- | ---: |
| sector | pro_01m66zsh97eczcgm38fp693mx5 | pri_01m66ztbsk11qktx2fs8xxt582 | 89 |
| multi | pro_01m66ztxgzfhy5cxqwnby8dgbx | pri_01m66zvfmy3x8a2s6wtqncejda | 179 |
| global | pro_01m66zwafptgdqx5zk8p8w8hj1 | pri_01m66zwtcmx4bb4qdfae8pgc3p | 349 |

All three products are active, tax category SaaS, custom data source=global-broker-sandbox. Each price was saved as recurring monthly USD, Includes tax, trials off, no country-specific prices, and minimum/maximum quantity 1. The saved price tables confirmed monthly amounts, no trial/country overrides, and active status. API preflight still needs to verify the provider representation.

## Remaining gates

- Authentication settings showed **Create your first API key**. A Broker-only sandbox key form was prepared with Prices Read and Transactions Read/Write. It was **not saved**: persistent credential creation requires action-time confirmation. No key was read, copied, created, or committed.
- Two pre-existing AI Visibility sandbox webhook destinations were active. Their full URLs contain access tokens and are deliberately omitted. They were not changed. No Broker destination was present in the displayed all-status/all-usage list.
- Broker receiver configuration, dedicated client token/signing secret, API preflight, provider checkout and verified Broker receipt remain unproven. No Broker webhook was created and no receiver was enabled or deployed.
- Local verification on code commit 30da015820214de3102030e71d2f36ad2bff29cc: 94 JavaScript tests passed (recorded in PR #211). GitHub run 41101188638 concluded **cancelled**, job test cancelled with no steps/logs returned. Do not count it as a pass or infer a code failure; no rerun was requested in this checkpoint.
- No live charge, live product/price/webhook change, entitlement activation, Vercel budget/pause/deployment change, or merge was performed.

Catalogue creation is configuration evidence only. It does not prove payment completion, Broker receipt acceptance, live readiness, or commercial acceptance.
