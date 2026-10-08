# GLOBAL BROKER AI — Professional Brokerage Operating Model
Updated 2026-10-08. **Design and implementation specification, not a claim of live functionality.**
## Market research
- Tridge Ark https://www.tridge.com/tridge-ark — product-centered two-sided matching, consent before revealing contact; Tridge does not charge deal commission.
- Europages Request Hub https://help.europages.com/en/supplier/europages-request-hub — validated RFQs, AI profile/product matching, buyer details gated until reply.
- Trademo https://www.trademo.com/ — trade activity, shipment signals, company research, tariffs, sanctions and evidence trails.
- go4WorldBusiness https://www.go4worldbusiness.com/pricing — paid access/contact quotas and vetted buying leads; subscriptions do not guarantee orders.
Use these as design inspiration only. No copying protected data, brand assets or unauthorized scraping.
## Product differentiation
Global Broker is an **active international intermediary**, not an Alibaba-style listing marketplace. Autonomous research identifies live buyers AND viable sellers; humans/agents qualify each; sector-specific invitations ask for consent; a separate signed brokerage agreement and applicable fee terms protect introductions; verified payments and consent control disclosure; success commission (target 3–5%, negotiated) is tracked only for contract-covered completed trades.
## Data states and access gates
1. DISCOVERED: source URL, time, original buyer request or seller offer, product/HS, location. Unverified company must not be labeled verified.
2. SOURCE_CHECKED: evidence that demand/supply signal exists and is current; do not imply corporate identity verified.
3. PARTY_VERIFIED: independently corroborated corporate identity and authorized contact, screening, recorded proof.
4. MATCH_REVIEWED: matching grade, quantity, origin, destination, Incoterms, timeline and constraints; evidence of actual availability and interest.
5. CONTACT_PERMISSIONED: each side independently authorizes introduction and allowed disclosures.
6. TERMS_SIGNED: signed agreement defines payer, commission %, commission basis, success trigger, covered counterparties, repeat order period, non-circumvention and dispute terms; legal review for relevant jurisdictions.
7. ACCESS_PAID: payment processor confirms payment of separately disclosed report/access fee, if applicable. **Payment never overrides consent.**
8. INTRODUCED: secure data room unlocks only permitted details; audit access.
9. DEAL_ACTIVE / WON / LOST: quotes, compliance docs, shipping, invoice, payments; success commission due only under agreed trigger.
10. COMMISSION_SETTLED: evidence of receipt, repeat-order coverage and expiration.
## Admin workflow
- Buyer Hunter: search genuine product buying requirements, distinguish tender/public procurement (usually excluded from private commission flow) from direct trade demand.
- Seller Hunter: discover manufacturers/exporters/wholesalers, distinguish manufacturer from trader; collect product specs, supply volume, country and certifications.
- Verification: company register, website/domain, authorized contact, product credentials, sanctions/PEP and jurisdiction-specific restrictions.
- Match: exact product and grade gate, volume, delivery, destination and Incoterms, deadline, margin viability where supported. Missing facts reduce readiness, not invented.
- Outreach: TR/EN localized sector templates, individualized recipient, provenance and unsubscribe/suppression; **draft only in Shadow Mode**.
- Document desk: purchase intent/RFQ, specifications, corporate registration, authority, supplier offer/COA, certificates, export/import permits where relevant; never assume all documents universally mandatory.
- Legal/commission: generate draft agreements only; require professional legal/tax review before execution.
- CEO: source freshness, evidence coverage, match quality, replies, signed terms, access fees, trade value, commission due/paid, disputes and agent cost.
## Product UI
Admin: Global Demand | Supply Discovery | Verified Matches | Sector Campaigns | Correspondence | Compliance Desk | Agreements | Payments | Commission Ledger | CEO Report.
Prospect: anonymized opportunity teaser and source freshness (no identifying buyer data).
Paid client: verified report scope as advertised; no contact details unless both consent and agreement gates permit.
## Anti-misrepresentation
No guaranteed buyer, seller, price, availability, successful deal or income. No email sent until approved and technical mail provider connected. No fee charged until processor, refunds, invoices and tax treatment established. Public GitHub Pages is not an authenticated private data room.
## Delivery order and gates
P0 evidence schema, truthful labels, matching, sector campaign drafts, tests.
P1 authenticated server-side private data room, explicit consent records, document workflow, email provider with approval queue.
P2 payment webhook, signed agreements, commission ledger, repeat orders and audit.
P3 scalable source connectors (license/API compliant), monitoring, multilingual optimization.
Mark each stage done only after code + tests + verified deployment.