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
- **Business contact:** the platform contact form and private owner email forwarding passed production verification on 20 October 2026 (run 39372843723); legal-contact acceptance for the actual individual operating model remains pending.
- **Custom domain:** broker.aivisibilityworks.com is attached, verified, and probed over HTTPS; retain the current-scan health and unauthorized-admin checks.
- **Customer acceptance:** automated tests do not count as real-customer acceptance. A real acceptance session must be recorded explicitly.
- **Gulf launch attestation:** current-scan evidence and explicit launch attestation are both required; an environment flag alone cannot substitute for live scan evidence.

## Policy

The public informational experience may be tested in protected staging while the commercial launch remains closed. No code path may enable email sending, bids, orders, contract signing, payment initiation, contact disclosure or commission collection merely because a UI or deployment is reachable.

## Consolidated acceptance review — 21 October 2026

This review covers all six remaining delivery acceptance headings together.
It closes no package: delivery remains web 77%, app 72%. These are fixed
package scores, not test-pass percentages. No new software change or repeated
regression run is needed merely to record missing external evidence.

### Evidence checked

- PR #178 merged as `fbb946ce89d2cbf42f49b8bcbe823bcb32a0e587`;
  Vercel production deployment `dpl_5LLY3zspxqrK5gKutPztpFbuHgtW` is READY.
- Python 571 / JavaScript 85 tests passed. Production browser acceptance run
  [39659188278](https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/39659188278)
  and full source scan
  [39659188471](https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/39659188471)
  succeeded. The scan persisted 67 active opportunities.
- Read-only database aggregates found 67 active records: 40 current calls by
  date/notice context only; 36 with extracted source/document text; zero fully
  evidenced commercial dossiers; zero verified supplier records; zero price-ready
  records. Source-sourcing readiness flags are not supplier technical approval.
- The commercial dossier projection flags missing buyer verification, scoped
  quantity, supplier and price on all 67 records; exact specification on 50,
  current deadline on 27, lot selection on 24, country on 3. A missing scoped
  quantity does not mean a notice has no published budget; these are distinct
  fields. Counts reflect this snapshot and must be refreshed after future scans.
- The quote inbox and quote review tables each contain zero rows; isolated Broker
  sandbox intents and receipts each contain zero rows. No real payment, invoice
  or accepted quotation can be inferred from a ready form.
- An empty production sandbox checkout probe returned HTTP 404
  `sandbox_unavailable`, confirming the disabled state; no transaction was created.
- One verified MFA factor exists, but zero phone-confirmed users and zero admin
  dual-recovery enrollment records. MFA alone does not prove dual recovery.
- Published launch state remains shadow, with admin dual recovery, legal review,
  payment provider testing, legal business-contact acceptance and real customer
  acceptance blocked. HTTPS, source ingestion and storage are separate completed
  technical conditions.

### One closure queue

| Heading | Current result | Evidence required to close | Next responsible action |
| --- | --- | --- | --- |
| P2 source dossier | Open: required fields/scope are missing | Current official buyer/product/scope, quantity or scoped budget/currency, deadline and readable required documents, with citations and reviewer/date; all package conditions still apply | Finish source/lot review from accessible official records; obtain unavailable documents from the source owner if needed |
| P3 technical match | Open: verified supplier count is zero | A supplier response naming one opportunity/lot and product/model, matching every mandatory specification, with exclusions and dated source reference | Await the already sent ficonTEC/FormFactor replies; assess the actual response against the exact lot, without repeat outreach |
| P4 quote, freight and risk | Open: quote inbox/reviews and price readiness are zero | Valid supplier quote plus documented origin/destination, freight, currency, delivery/Incoterm, commercial risk and review for the same selected scope | Register and review actual documents in the existing private quote flow when received; do not substitute catalogue or estimated prices |
| P6 account recovery | Open: phone and dual recovery are absent | Verified recovery channels and an explicitly recorded real recovery acceptance result | Respect the owner's decision to retain the current password; do not consume a reset link, send a new reset email or change auth settings for this review |
| P7 payment and operating conditions | Open: isolated sandbox is prepared but disabled; merchant/operating acceptance missing | Broker-specific sandbox catalogue/credentials, provider transaction and reconciled signed receipt; actual operating model, legal-contact/tax/invoice review and required provider acceptance | Await provider appeal outcome and account configuration; verify sandbox first, then assess production separately; no live charge or paid service is authorized by this review |
| P8 customer acceptance | Open: automated browser success only | A real customer's dated web/mobile session, observed outcome and explicit acceptance, with unresolved issues recorded | Arrange a real pilot session when a participant and valid dossier are available; do not invent a participant or treat fixture tests as acceptance |

### Single-session acceptance record

Use one private record for a real pilot, not a new public feature or repeated
fixture run. Record participant consent/role, time, device, deployed revision and
selected opportunity/lot; keep identities, documents, tokens and receipts out of
this public repository.

1. Read the buyer, requested goods, selected lot, quantity/budget, deadline and
   source documents. Record each fact's source and every unresolved omission.
2. Compare the supplier's exact product/model and written exceptions against
   mandatory specification clauses. Record accepted, rejected or pending.
3. Review the actual quote validity/currency/quantity and the same-scope freight,
   destination, delivery terms and risk. Record source references and decision.
4. Verify permitted login/MFA behavior. Record recovery as **not performed at
   owner request** unless a separate real recovery session is authorized; do not
   mark the recovery package complete as a result of login success.
5. Test provider sandbox only after Broker-specific configuration is available;
   reconcile server receipt and provider reference. Keep real entitlements and
   live charges unchanged. Record legal/operating approval independently.
6. Have the real participant state accept/reject/pending for the observed flow.
   Log issues and responsible actions; do not prefill acceptance or translate
   a test pass into commercial acceptance.

Only attach actual resulting evidence to the delivery ledger and award the
existing fixed package points when every acceptance condition is met. No
threshold, gate, password, subscription or supplier verification was changed by
this review. No external message was sent.
