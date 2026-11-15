# Consolidated Broker candidate

Prepared TED annex review utilities, fail-closed official XML gates, truthful customer-tab content and accessibility changes are merged locally with current main `cc853a78d23379821866df3e4ee623235f94cdb0`. The final candidate passed 779 Python and 99 JavaScript tests, including the new adapter tests.

`src/command_control_review.py` transforms trusted source-loaded `launch_gate.checks` into revision-dependent shared acceptance-review commands. Explicit booleans are reported as verified/blocked; missing or malformed values remain unknown. Technical annex, formula and source-revision gates are mandatory. A reported pass is not independent verification and never authorizes sourcing or release.

`submit_review` is disabled by default. Explicit submission requires a short-lived agent token and targets only `https://www.aivisibilityworks.com/api/command-control`. Redirects and automatic retries are not used. Tokens and response bodies are not logged. No outbound submission occurred in tests.

Still open: authoritative annex re-fetch, formula evaluation/reviewer attribution, PDF images, applicable revision/lot completeness, actual source probe, dedicated writer credentials and shared API deployment. `supplier_sourcing_ready` and commercial approval gates remain protected. Existing Vercel deployment BLOCKED status is separate from TED evidence acceptance; no pause, billing, sourcing or production settings were changed.
