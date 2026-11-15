# AI B2B Proposal Agent — v9 source-bound offline acceptance

Status: **DRAFT / NO-GO**. Research-only code, not production acceptance.

## Gate design
- v9 rule-based content checks: `proposal_v9.py` — 30 synthetic regression cases.
- New trusted snapshot integrity gate: `proposal_source_gate.py` — 18 synthetic regression cases.
- Offline CI: `.github/workflows/ai-b2b-proposal-v9-offline.yml`, Python standard library only.
- No direct deployment, network fetch, credential use, payment, email dispatch, or automatic proposal submission.

## Essential trust boundary
`trusted_sources` **must be supplied independently** by a controlled document ingestion process. A model-generated or applicant-supplied `trusted_sources` dictionary is untrusted input and can make a forged statement appear internally consistent. SHA-256 only checks exact equality between a supplied snapshot and record; it does **not** independently validate the document issuer, certification authority, jurisdiction, timestamps, signatory, or commercial entitlement.

`source_integrity_verified=True` is an internal snapshot consistency flag **only**. The result always sets `real_world_authenticity_verified=False` and `commercial_approval=False` / `automatic_offer=False`.

## Fail-closed behavior
Invalid/missing source id, line id, company binding, trusted region binding, source digest, or exact line text => `REVIEW_SCOPE`; mixed trusted and untrusted records do not yield auto-positive. Relevance matching remains limited to three topics (English support, ISO 27001, uptime) and is not a general natural language understanding system.

## Open blockers before any production decision
1. Independent document ingestion, immutable versioning, approved source registry and custodianship.
2. Verified legal company identity / issuer chain and certificate validation with competent sources.
3. OCR/PDF paragraph or line citation reconciliation and adversarial evaluation against genuine authorized examples.
4. Holdout tests measuring **false accept** and **false reject** rates with human annotations.
5. Security review and explicit customer-facing acceptance. No deploy/merge while blocked.

Last recorded offline CI evidence: https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43617568543
