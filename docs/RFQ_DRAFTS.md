# Private source-scoped RFQ drafts

Admin dossiers can prepare a copyable English quotation-request draft from explicitly selected World Bank source-table rows. No e-mail is sent, no quotation is recorded and no commercial approval is granted.

The builder requires exact notice/API provenance, a valid current deadline and a successful source read no older than 48 hours. Selected indexes must be unique and within the current source table. Quantities and units must retain the source parser's numeric/unit contract. Mixed procurement groups, inconsistent group labels, missing units and contact/URL-bearing cells are rejected. Selections start empty and any change clears the previous draft.

The output lists selected products, quantities and destinations individually, with no summed quantity. It asks the supplier to state technical configuration, standards/deviations, currency, unit/item pricing, validity, lead time, payment and delivery/freight terms. It explicitly leaves full specification confirmation open and does not create an order. Buyer identity, source URL/notice ID and personal contact fields are omitted. A browser-generated UUID identifies only the draft, never a purchase or paid entitlement.

Controls appear only in the existing private admin dossier context. Existing admin session/MFA/data boundaries remain authoritative; no new endpoint or service credential is introduced. Scope/financial gates remain closed. Copy is a user-triggered local clipboard operation; concurrent copies are suppressed and changed selections require regeneration.

Validation is performed remotely through GitHub CI and the exact-deployed-script Chromium 320/390/1280 and WebKit 390 browser tests because the interactive execution environment is unavailable. Browser requests are intercepted; tests verify empty/mixed selection rejection, per-row amounts, privacy, copying, clearing and zero outbound mutations. This is draft-preparation verification, not a real supplier quotation, customer acceptance, provider approval or package completion.
