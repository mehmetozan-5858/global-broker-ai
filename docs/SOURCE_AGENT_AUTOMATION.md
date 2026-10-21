# Source worker: bounded parent-document discovery

The existing scan executes source, field, specification, supplier, feasibility
and risk stages automatically and records stage summaries/blocked work through
`agent_center`. This change extends the deterministic source worker. It uses no
new LLM calls or paid service and adds no new deployment/service dependency.
It is the first retrieval improvement in the broader agent automation work;
it does not implement an autonomous multi-LLM team.

## Behavior

When a public lot page explicitly links a parent tender index with a supported
navigation label, read at most one same-origin index and follow no further index
links. The worker never guesses parent IDs, signs in, sends forms, clicks show
interest or submits bids. GET download SSRF/redirect checks and existing byte,
page, text, worker and workflow limits continue to apply. Navigation currently
recognizes the Italian lot-list label and four explicit English parent/lot labels
on tender/notice routes; unsupported navigation stays pending for review.

The index is a discovery source only. Its listing text is never merged into the
opportunity's evidence because it can describe several lots. Actual attachments
retain the precise child or parent URL that discovered them. The shared three
attachment cap applies after ranking links from both origins, deduplicating
URLs. Italian technical specifications rank before evaluation criteria, which
rank before generic forms. All document text is ranked before applying the
existing 40,000-character merge cap. Index success alone does not increase the
parsed-source count or claim document reading.

The every-scan refresh applies to existing and future records. The existing
GitHub Shadow Scan is scheduled at minute 17 every six hours and also runs on
main source changes. A failed parent read remains a recorded failure and is
retried by the next scan; it does not restore old document evidence. The source
worker already processes opportunities concurrently. No endless retries or
recursive crawler was introduced.

## Verification

Nine regression tests cover explicit same-origin links, rejected credentials/
queries/login/cross-origin links, one-hop/one-page limits, failure preservation,
Italian attachment ranking, precise provenance, duplicate direct links, retained
lot review, and index-only counts. Local suite: 580 Python and 85 JavaScript tests.

A replay using captured real Livorno child and parent HTML plus actual downloaded
PDFs found zero PDFs before the change and two after it (technical specification
and evaluation criteria), with 33,677 final text characters and the technical
PDF first. Forms were omitted in that bounded replay. This demonstrates real
source structure handling, not a fresh live scan or supplier acceptance; the
post-merge production scan is the separate live verification.

The selected-lot review flag remains intact. No quantities/budgets across lots
are promoted, no supplier is verified, no price is created, and no external
message, payment, customer acceptance or fixed delivery point is generated.
Public projection remains an allowlist and does not expose index/attachment
URLs or private extracted text.
