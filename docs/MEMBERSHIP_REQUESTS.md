# Membership requests (pre-checkout)

Verified account holders can record interest in Sector Access, Multi-Sector or
Global Access at `/membership`, reached from pricing or the account page. These
are membership requests, not subscriptions, payment orders or invoices. The UI
states this before acknowledgement and after saving.

The server records the fixed USD monthly catalog amount, pricing-policy version,
acknowledgement version and timestamp. Clients send only request ID, plan ID and
acknowledgement; owner, amount, currency and status cannot be supplied. One request
per owner/plan prevents duplicate interest records even with a new retry ID. An ID
cannot be replayed for another plan or by another owner. The original request is
immutable to client roles.

Private rows are inaccessible to API roles. Public SECURITY INVOKER wrappers call
narrow internal helpers with explicit current-user and verified-email checks.
Workspaces expose only the current owner's requests; direct table access and
anonymous calls are denied. Browser-side profile metadata is never authoritative.

`awaiting_provider` and `not_issued` are the only allowed states. Neither this
schema nor its functions can update customer entitlements. Provider checkout,
verified payment events, invoice issuance/refunds and commercial approval remain
separate unfinished integration work. AI Visibility credentials are not copied to
Broker and no provider transaction or notification is initiated.

Verification: rolled-back SQL tests cover ownership, verified email, catalogue
prices, immutable retries, repeat plan deduplication, unchanged entitlements and
API role denial. Browser fixtures intercept all writes and cover pricing-to-plan
navigation, acknowledgement, ambiguous response retries, current Free access,
no-invoice messaging and mobile layout on Chromium/WebKit. Fixture users and
requests are never persisted.
