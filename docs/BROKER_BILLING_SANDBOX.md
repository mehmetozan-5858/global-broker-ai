# Broker billing integration — isolated sandbox

This extends Broker membership requests with a separate test billing flow. It
never imports AI Visibility plans, clients, subscriptions or payment records.
No real checkout, invoice or entitlement is enabled by this work.

## Implemented boundaries

- A verified Broker account can prepare an intent only for its own stored
  membership request. Plan, amount and currency come from the database.
- Before creating a transaction, the server reads the dedicated sandbox price
  and checks active status, product, monthly cycle and exact USD amount.
- A database claim serializes transaction creation. Created transactions are
  reused. An ambiguous provider/claim/binding response remains `creating` or
  `uncertain` and requires read-only provider reconciliation before any retry
  of creation. The UI cannot reset that state or create a second transaction.
- Only `https://sandbox-api.paddle.com` is used. The browser receives only a
  `test_` client token and transaction ID and initializes Paddle in sandbox.
- Webhooks verify HMAC-SHA256 against raw bytes with five-second timestamp
  tolerance, then require an exact Broker intent, bound transaction, product,
  price, quantity, monthly cycle, USD currency and full non-discounted amount.
- Only initial `transaction.completed` receipts are recorded. Renewals,
  cancellations, refunds, discounts, credits and other lifecycle events are not
  accepted as initial membership payment evidence. This is not a production
  subscription state machine.
- Receipts are idempotent and owner-filtered. Browser completion callbacks
  merely refresh server state. No handler changes `customer_entitlements`,
  issues an invoice, marks a real payment received or opens live commerce.
- New private tables have RLS and no browser table grants. Public wrappers are
  SECURITY INVOKER; privileged helpers are private and service-role-only.

## Deployment/configuration status

The receiver defaults to disabled. Configuration does not establish provider
approval. No existing AI Visibility price mapping or credential is copied.
Dedicated Broker sandbox products/prices, key, client token and notification
secret must be configured and verified before an actual provider test.

Required Edge Function variables (values must be entered privately):

- `GB_BROKER_SANDBOX_ENABLED=true`
- `GB_BROKER_SANDBOX_API_KEY` — sandbox API key only
- `GB_BROKER_SANDBOX_CLIENT_TOKEN` — `test_` token only
- `GB_BROKER_SANDBOX_WEBHOOK_SECRET` — this sandbox notification destination
- `GB_BROKER_SANDBOX_PRICES` — JSON mapping of `sector`, `multi`, `global` to
  distinct dedicated `price_id` and `product_id` pairs. Monthly USD prices must
  match the stored membership catalog (8900, 17900, 34900 minor units).

Supabase supplies `SUPABASE_URL`, `SUPABASE_ANON_KEY` and the server-only
`SUPABASE_SERVICE_ROLE_KEY`. None is returned as a server secret to the browser.

Function routes under `/functions/v1/broker-billing-sandbox`:

- `POST /checkout`: verified Bearer session and exact Broker web origin.
- `POST /workspace`: same owner session; isolated sandbox state only.
- `POST /webhook`: dedicated notification signature, no user JWT. Platform JWT
  validation is disabled only because the function authenticates these routes
  itself. This does not disable the checks inside the function.

The membership page hides the test controls when the receiver is disabled.
Any enabled controls are explicitly labelled Sandbox, prohibit real cards and
never describe the test receipt as a real invoice or paid membership.

## Verification and remaining acceptance

Local validation: 559 Python and 85 JavaScript tests. The SQL authorization
fixture runs in a transaction with ROLLBACK, including owner isolation,
service/browser separation, single claims, retries, exact matching and unchanged
real entitlements. No synthetic account, intent or receipt is retained.

The browser fixture intercepts all membership and sandbox POSTs and stubs
Paddle. It covers live-token rejection, sandbox initialization, callback without
receipt, later receipt refresh, unchanged real plan and mobile containment.

Actual fresh Broker provider delivery, refund/lifecycle handling, real invoice,
merchant/domain/product approval and real customer acceptance remain open.
This preparation does not close P7 or alter the fixed web/app percentages.
