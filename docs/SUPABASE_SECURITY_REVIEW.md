# Supabase security review — 2026-10-10

## Closed findings

- Public RLS policies use `(select auth.uid())` / `(select auth.jwt())` where applicable to avoid per-row auth re-evaluation.
- Admin role visibility is one combined ownership + AAL2 policy; permissive-policy OR semantics cannot bypass MFA.
- `gb_new_user_defaults()` is a trigger helper and is not executable by `public`, `anon` or `authenticated`.
- `my_broker_access()` and `set_customer_preferences()` run as `SECURITY INVOKER` and rely on RLS.
- `private.contact_unlocks(opportunity_id)` has a covering index for its foreign key.

## Reviewed exception: `unlock_opportunity_contact(text)`

Supabase may continue to report this function as an authenticated `SECURITY DEFINER` RPC. This is intentional and must not be silenced by weakening the access model.

The function needs an atomic privileged boundary because it must read the private opportunity record, validate the server-managed entitlement, enforce selected sector/country scope, decrement a server-managed contact-credit balance, create the private unlock record and append an audit entry. Direct client access to those private tables remains revoked.

Controls:

- callable by `authenticated` only; `public` and `anon` execute are revoked;
- rejects a missing `auth.uid()`;
- requires an active server-side entitlement;
- enforces sector and selected-country scope;
- requires contact credit when the plan is credit-limited;
- makes repeated unlocks idempotent;
- writes an audit event;
- does not itself send external communications, offers, orders or payments.

If this RPC is redesigned later, prefer moving the privileged operation behind a server/Edge Function and revoke direct authenticated RPC execution rather than exposing private tables to the client.
