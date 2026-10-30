# Broker connection to the existing Paddle setup

AI Visibility's account, checkout page and existing products are preserved. A
shared merchant account does not make AI Visibility's products, customer IDs,
transactions or entitlement records Broker evidence. No second paid account is
required by this preparation; Broker needs its own sandbox catalogue mapping
and receiver credentials in the appropriate test environment.

## Read-only catalogue preflight

Run `node scripts/broker-paddle-preflight.mjs` in a private environment containing
the dedicated Broker sandbox configuration documented in
`BROKER_BILLING_SANDBOX.md`. It reads the authenticated sandbox API root and three
mapped prices. The URL is fixed to `sandbox-api.paddle.com`; production-shaped
keys stop before a network request, redirects are rejected and the root must
identify an authenticated sandbox account.

Output contains configuration names and boolean results only. It never prints
credentials, provider IDs or raw provider responses. Missing configuration
returns exit code 2. A passing preflight verifies the supplied catalogue inputs,
not a payment, webhook delivery, deployed receiver or membership activation.
The command makes no POST/PATCH/DELETE requests and never enables the receiver.

## Required Broker sandbox catalogue

| Broker plan | Monthly amount | Currency | Required price settings |
| --- | ---: | --- | --- |
| sector | 8900 minor units | USD | monthly × 1, tax internal, no trial, no country overrides |
| multi | 17900 minor units | USD | monthly × 1, tax internal, no trial, no country overrides |
| global | 34900 minor units | USD | monthly × 1, tax internal, no trial, no country overrides |

These are the already stored Broker membership amounts, not new live prices.
Use three distinct Broker product IDs and price IDs; do not reuse AI Visibility
plan mappings. Quantity bounds must permit one unit. The existing receipt
contract requires the full exact amount; external tax, a trial or a country
override can change the checkout total despite a matching base price. The
receiver now rejects those catalogue states before claiming transaction
creation or contacting the transaction endpoint. Existing prices are not edited.

The dedicated sandbox notification destination must point to
`https://yhzdqrqzjruduohypvqf.supabase.co/functions/v1/broker-billing-sandbox/webhook`
and subscribe to `transaction.completed`. Keep its signing secret private.
The live AI Visibility webhook and its event settings remain unchanged.

## Actual acceptance still required

Once sandbox access is connected, validate existing dedicated entries first.
Create missing sandbox configuration only in that test account; no live
transaction or paid operation is authorized by this document. Deploying or
enabling the receiver remains a separately reviewable environment change.
The receiver package must include both `core.mjs` and its new `catalog.mjs`.

Use a verified Broker test user and its own membership request for one provider
checkout, then reconcile the bound transaction and signed receipt. Browser
completion alone is insufficient. Real membership, invoices and entitlements
must remain unchanged in this sandbox test. Production billing/refund lifecycle
and operating approval remain separate work.
