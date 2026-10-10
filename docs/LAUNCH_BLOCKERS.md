# Global Broker launch blockers

This document separates code completion from production/commercial launch readiness. A missing external attestation must never be replaced with a guessed `true` value.

## Verified technical state

- GitHub CI runs the Python regression suite and JavaScript syntax checks.
- Vercel staging can build the Python entrypoint defined in `pyproject.toml`.
- Supabase project is active and the private-room Edge Function is deployed.
- Private-room storage uses Vercel OIDC and a durable Supabase/Postgres store.
- Public Supabase tables use RLS; admin role reads require an AAL2 JWT.
- Admin shell additionally requires a valid Supabase session, AAL2 and the server-side `admin` role before loading the operations UI.
- Deal lifecycle, commission and payment state stay evidence-gated and Shadow Mode forbids autonomous external actions.
- Watchdog cannot infer a stalled agent when telemetry is missing.

## External gates that must remain blocked until evidenced

- **Admin dual recovery:** email + phone recovery enrollment has not been completed and the SMS provider is not verified. The database enrollment record must show both channels verified and enabled before this gate can pass.
- **Legal review:** Privacy, Terms and Refund pages are drafts until reviewed for the actual operating entity, customer geography, tax/invoicing and brokerage model.
- **Payment:** no provider or bank-payment production flow may be marked tested without a real test transaction, source reference and reconciled record.
- **Business contact:** a production support/legal contact must be verified before public commercial launch.
- **Custom domain:** a non-`vercel.app` production domain must be registered, attached and verified before the custom-domain gate passes.
- **Customer acceptance:** automated tests do not count as real-customer acceptance. A real acceptance session must be recorded explicitly.
- **Gulf launch attestation:** current-scan evidence and explicit launch attestation are both required; an environment flag alone cannot substitute for live scan evidence.

## Policy

The public informational experience may be tested in protected staging while the commercial launch remains closed. No code path may enable email sending, bids, orders, contract signing, payment initiation, contact disclosure or commission collection merely because a UI or deployment is reachable.
